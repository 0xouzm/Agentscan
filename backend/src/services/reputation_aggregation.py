"""Small, pure helpers for maintaining reputation aggregates."""


def normalize_feedback_value(value: int, value_decimals: int) -> float:
    """Convert an ERC-8004 fixed-point value to its displayed numeric value."""
    if value_decimals < 0:
        raise ValueError("value_decimals must be non-negative")
    return float(value) / (10 ** value_decimals) if value_decimals else float(value)


def add_feedback_to_aggregate(
    value_sum: float,
    feedback_count: int,
    value: int,
    value_decimals: int,
) -> tuple[float, int, float]:
    """Add one feedback value without rereading the agent's feedback history."""
    if feedback_count < 0:
        raise ValueError("feedback_count must be non-negative")

    new_sum = float(value_sum) + normalize_feedback_value(value, value_decimals)
    new_count = feedback_count + 1
    return new_sum, new_count, new_sum / new_count
