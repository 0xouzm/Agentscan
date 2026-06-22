"""Task scheduler service - Multi-network support"""

import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.services.blockchain_sync import get_sync_service
from src.core.networks_config import get_enabled_networks, get_network
import structlog

logger = structlog.get_logger()

# Global scheduler instance
scheduler = AsyncIOScheduler()

# Endpoint scan configuration
ENDPOINT_SCAN_HOUR = 3  # UTC 03:00 daily
STARTUP_SCAN_THRESHOLD = 10  # Trigger startup scan if unchecked agents >= this

# Network sync intervals (minutes) - all networks at 5 minutes
# Rationale: catch-up is complete; event volume is low; 2-3min intervals wasted RPC budget
NETWORK_SYNC_INTERVALS = {
    "ethereum": 5, "polygon": 5, "base": 5, "monad": 5,
    "arbitrum": 5, "optimism": 5, "linea": 5, "scroll": 5,
    "avalanche": 5, "celo": 5, "gnosis": 5, "taiko": 5, "megaeth": 5,
    "bsc-1": 5, "sepolia": 5,
}
DEFAULT_NETWORK_SYNC_INTERVAL_MINUTES = 5
NETWORK_SYNC_STAGGER_SECONDS = 1


def _create_multi_network_sync_task(network_keys: list[str]):
    """Factory function to create one sequential sync task for all networks."""
    async def sync_task():
        started_at = datetime.now(timezone.utc)
        failed_networks = []

        logger.info("scheduler_task_started", task="multi_network_sync", networks=network_keys)

        for index, network_key in enumerate(network_keys):
            network = get_network(network_key) or {}
            try:
                logger.info(
                    "network_sync_dispatch_started",
                    network=network_key,
                    name=network.get("name", network_key)
                )
                await asyncio.to_thread(_sync_network_blocking, network_key)
                logger.info("network_sync_dispatch_completed", network=network_key)
            except Exception as e:
                failed_networks.append(network_key)
                logger.error(
                    "network_sync_dispatch_failed",
                    network=network_key,
                    error=str(e)
                )

            if index < len(network_keys) - 1:
                await asyncio.sleep(NETWORK_SYNC_STAGGER_SECONDS)

        logger.info(
            "scheduler_task_completed",
            task="multi_network_sync",
            failed_networks=failed_networks,
            duration_seconds=round((datetime.now(timezone.utc) - started_at).total_seconds(), 2)
        )
    return sync_task


def start_scheduler():
    """Start the background task scheduler with multi-network support"""

    async def endpoint_scan_task():
        try:
            logger.info("scheduler_task_started", task="endpoint_scan")
            await asyncio.to_thread(_run_endpoint_scan_blocking)
            logger.info("scheduler_task_completed", task="endpoint_scan")
        except Exception as e:
            logger.error("scheduler_task_failed", task="endpoint_scan", error=str(e))

    _reset_interrupted_syncs()

    enabled_networks = get_enabled_networks()
    scheduled_networks = []

    for network_key, config in enabled_networks.items():
        rpc_url = config.get("rpc_url", "")
        if not rpc_url:
            logger.warning(
                "network_sync_skipped",
                network=network_key,
                reason="no_rpc_url_configured"
            )
            continue

        scheduled_networks.append(network_key)
        logger.info(
            "network_sync_enabled",
            network=network_key,
            name=config["name"],
            interval_minutes=NETWORK_SYNC_INTERVALS.get(network_key, DEFAULT_NETWORK_SYNC_INTERVAL_MINUTES)
        )

    if scheduled_networks:
        interval = min(
            NETWORK_SYNC_INTERVALS.get(network_key, DEFAULT_NETWORK_SYNC_INTERVAL_MINUTES)
            for network_key in scheduled_networks
        )
        scheduler.add_job(
            _create_multi_network_sync_task(scheduled_networks),
            trigger=CronTrigger(minute=f'*/{interval}', second=0),
            id='multi_network_sync',
            name='Sync enabled blockchain networks sequentially',
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=interval * 60,
        )
        logger.info("multi_network_sync_scheduled", networks=scheduled_networks, interval_minutes=interval)

    scheduler.add_job(
        endpoint_scan_task,
        trigger=CronTrigger(hour=ENDPOINT_SCAN_HOUR, minute=0),
        id='endpoint_scan',
        name='Daily endpoint health scan',
        replace_existing=True,
        max_instances=1
    )

    scheduler.start()

    endpoint_scan_job = scheduler.get_job('endpoint_scan')
    logger.info(
        "scheduler_started",
        networks=scheduled_networks,
        total_networks=len(scheduled_networks),
        endpoint_scan_schedule=f"Daily at {ENDPOINT_SCAN_HOUR:02d}:00 UTC",
        endpoint_scan_next_run=endpoint_scan_job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if endpoint_scan_job and endpoint_scan_job.next_run_time else 'N/A',
        reputation_mode="EVENT-DRIVEN (via NewFeedback/FeedbackRevoked events)"
    )

    _check_and_trigger_startup_scan()


def _check_and_trigger_startup_scan():
    """Check if there are unchecked agents and trigger a scan if threshold is met"""
    from src.db.database import SessionLocal
    from src.models import Agent
    import threading

    try:
        db = SessionLocal()
        unchecked_count = db.query(Agent).filter(
            Agent.endpoint_checked_at.is_(None)
        ).count()
        db.close()

        if unchecked_count >= STARTUP_SCAN_THRESHOLD:
            logger.info(
                "startup_scan_triggered",
                unchecked_agents=unchecked_count,
                threshold=STARTUP_SCAN_THRESHOLD
            )
            thread = threading.Thread(target=_run_endpoint_scan_blocking, daemon=True)
            thread.start()
        else:
            logger.info(
                "startup_scan_skipped",
                unchecked_agents=unchecked_count,
                threshold=STARTUP_SCAN_THRESHOLD,
                reason="below_threshold"
            )
    except Exception as e:
        logger.error("startup_scan_check_failed", error=str(e))


def _reset_interrupted_syncs():
    """Clear RUNNING sync flags left behind by a previous interrupted process."""
    from src.db.database import SessionLocal
    from src.models import BlockchainSync, SyncStatusEnum

    db = None
    try:
        db = SessionLocal()
        stale_syncs = db.query(BlockchainSync).filter(
            BlockchainSync.status == SyncStatusEnum.RUNNING
        ).all()
        if not stale_syncs:
            return

        networks = [sync.network_name for sync in stale_syncs]
        for sync in stale_syncs:
            sync.status = SyncStatusEnum.ERROR
            sync.error_message = "Reset on scheduler startup: previous sync did not finish"
        db.commit()
        logger.warning("interrupted_syncs_reset", count=len(stale_syncs), networks=networks)
    except Exception as e:
        logger.error("interrupted_syncs_reset_failed", error=str(e))
    finally:
        if db is not None:
            db.close()


def _sync_network_blocking(network_key: str):
    """Blocking wrapper for network sync - runs in thread pool"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        service = get_sync_service(network_key)
        loop.run_until_complete(service.sync())
    finally:
        loop.close()


def _run_endpoint_scan_blocking():
    """Run endpoint health scan for all unchecked agents - runs in thread pool"""
    from src.db.database import SessionLocal
    from src.models import Agent
    from src.services.endpoint_health_service import get_endpoint_health_service
    from datetime import datetime

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        db = SessionLocal()
        try:
            agents = db.query(Agent).filter(
                Agent.endpoint_checked_at.is_(None)
            ).all()

            if not agents:
                logger.info("endpoint_scan_skipped", reason="no_unchecked_agents")
                return

            logger.info("endpoint_scan_starting", total_agents=len(agents))

            service = get_endpoint_health_service()

            async def log_progress(checked, total, working, agent_name, result):
                if checked % 100 == 0:  # Log every 100 agents
                    logger.info(
                        "endpoint_scan_progress",
                        checked=checked,
                        total=total,
                        working=working,
                    )

            async def run_scan():
                return await service.scan_agents_concurrent(agents, log_progress)

            result = loop.run_until_complete(run_scan())

            for scan_result in result.get("results", []):
                agent_id = scan_result.get("agent_id")
                if agent_id:
                    try:
                        agent = db.query(Agent).filter(Agent.id == agent_id).first()
                        if agent:
                            # Always mark as checked, even if skipped (no metadata)
                            agent.endpoint_checked_at = datetime.utcnow()
                            # Only save endpoint_status if not skipped
                            if not scan_result.get("skipped"):
                                agent.endpoint_status = {
                                    "endpoints": scan_result.get("endpoints", []),
                                    "has_working_endpoints": scan_result.get("has_working_endpoints", False),
                                    "total_endpoints": scan_result.get("total_endpoints", 0),
                                    "healthy_endpoints": scan_result.get("healthy_endpoints", 0),
                                    "checked_at": datetime.utcnow().isoformat(),
                                }
                    except Exception as e:
                        logger.debug("db_save_failed", agent_id=agent_id, error=str(e))

            db.commit()

            logger.info(
                "endpoint_scan_completed",
                checked=result.get("checked", 0),
                working=result.get("working", 0),
            )

        finally:
            db.close()

    finally:
        loop.close()


def shutdown_scheduler():
    """Shutdown the scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("scheduler_shutdown")
