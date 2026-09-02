import { EndpointBlock } from '@/components/docs/EndpointBlock';

export const metadata = {
  title: 'Endpoint Health API - Agentscan Docs',
  description: 'API endpoints for agent endpoint monitoring and health reports',
};

export default function EndpointHealthApiPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold text-[#0a0a0a] dark:text-[#fafafa] mb-4">Endpoint Health API</h1>
      <p className="text-[#525252] dark:text-[#a1a1a6] mb-8">
        Monitor the health and availability of AI agent endpoints. Single-agent checks run live; aggregate
        endpoints return the latest stored scan so requests stay fast and bounded.
      </p>

      <EndpointBlock
        method="GET"
        path="/api/agents/{agent_id}/endpoint-health"
        description="Get endpoint health report for a specific agent, including live checks and response times."
        params={[
          { name: 'agent_id', type: 'string', required: true, description: 'Agent ID' },
          { name: 'include_feedbacks', type: 'boolean', default: 'true', description: 'Include feedback data in report' },
        ]}
        response={`{
  "agent_id": "ethereum-1",
  "agent_name": "MyAgent",
  "endpoints": [
    {
      "url": "https://agent.example.com/api",
      "status": "healthy",
      "http_status": 200,
      "response_time_ms": 245,
      "last_checked": "2026-04-07T10:00:00Z"
    }
  ],
  "overall_status": "healthy"
}`}
      />

      <EndpointBlock
        method="GET"
        path="/api/endpoint-health/quick-stats"
        description="Quick platform-wide health statistics with top agents."
        params={[
          { name: 'network', type: 'string', description: 'Filter by network' },
        ]}
        response={`{
  "summary": {
    "total_agents": 1200,
    "agents_with_endpoints": 850,
    "working_endpoints": 720,
    "health_rate": 84.7
  },
  "working_agents": [ ... ],
  "top_reputation_agents": [ ... ],
  "generated_at": "2026-04-07T10:00:00Z"
}`}
      />

      <EndpointBlock
        method="GET"
        path="/api/endpoint-health/summary"
        description="Cached endpoint health summary with a bounded working-agent list."
        params={[
          { name: 'network', type: 'string', description: 'Filter by network' },
          { name: 'limit', type: 'integer', default: '20', description: 'Max working agents to return (max 100)' },
        ]}
        response={`{
  "summary": {
    "total_scanned": 850,
    "working": 720,
    "failed": 130,
    "health_rate": 84.7
  },
  "working_agents": [
    {
      "agent_id": "ethereum-1",
      "agent_name": "MyAgent",
      "endpoints": ["https://agent.example.com/api"],
      "response_time_ms": 245
    }
  ],
  "generated_at": "2026-04-07T10:00:00Z"
}`}
      />

      <EndpointBlock
        method="GET"
        path="/api/endpoint-health/working-agents"
        description="List agents with working endpoints from the latest stored scan, optionally filtered by minimum reputation."
        params={[
          { name: 'network', type: 'string', description: 'Filter by network' },
          { name: 'min_reputation', type: 'integer', default: '0', description: 'Minimum reputation score' },
          { name: 'limit', type: 'integer', default: '20', description: 'Max results (max 100)' },
        ]}
        response={`{
  "total_working": 720,
  "agents": [
    {
      "agent_id": "ethereum-42",
      "agent_name": "HighRepAgent",
      "reputation_score": 95.2,
      "endpoints": ["https://agent.example.com"],
      "response_time_ms": 120
    }
  ]
}`}
      />

      <EndpointBlock
        method="GET"
        path="/api/endpoint-health/full-report"
        description="Bounded endpoint health report from the latest stored scan."
        params={[
          { name: 'network', type: 'string', description: 'Filter by network' },
          { name: 'limit', type: 'integer', default: '100', description: 'Max agents (max 500)' },
        ]}
        response={`{
  "summary": { ... },
  "working_agents": [ ... ],
  "all_reports": [
    {
      "agent_id": "ethereum-1",
      "endpoints": [
        { "url": "...", "status": "healthy", "response_time_ms": 245 }
      ]
    }
  ],
  "generated_at": "2026-04-07T10:00:00Z"
}`}
      />
    </div>
  );
}
