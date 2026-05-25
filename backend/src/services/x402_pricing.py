"""Pricing aggregation helpers for x402 discovery resources."""

from __future__ import annotations

from typing import Any

PRICE_BUCKETS = [
    ("<$0.001", 0, 0.001),
    ("$0.001-$0.01", 0.001, 0.01),
    ("$0.01-$0.05", 0.01, 0.05),
    ("$0.05-$0.10", 0.05, 0.10),
    ("$0.10-$0.50", 0.10, 0.50),
    ("$0.50-$1", 0.50, 1),
    ("$1-$5", 1, 5),
    (">$5", 5, None),
]


def amount_usd(accept: dict[str, Any]) -> float | None:
    try:
        return int(accept.get("amount")) / 1_000_000
    except (TypeError, ValueError):
        return None


def price_distribution(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = {label: 0 for label, _, _ in PRICE_BUCKETS}
    for item in items:
        prices = [
            price
            for price in (amount_usd(accept) for accept in (item.get("accepts") or []))
            if price is not None
        ]
        if not prices:
            continue
        bucket = _bucket_label(min(prices))
        counts[bucket] += 1
    return [
        {"bucket": label, "count": counts[label], "min_usd": low, "max_usd": high}
        for label, low, high in PRICE_BUCKETS
    ]


def _bucket_label(price: float) -> str:
    for label, low, high in PRICE_BUCKETS:
        if price >= low and (high is None or price < high):
            return label
    return PRICE_BUCKETS[-1][0]
