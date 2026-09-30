"""Percentile bootstrap: how much a score could move with a different sample of documents."""
import math
import random
from collections.abc import Callable, Sequence


def bootstrap_ci(units: Sequence, statistic: Callable[[list], float], n: int = 1000,
                 seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    if not units:
        return math.nan, math.nan
    rng = random.Random(seed)
    values = []
    for _ in range(n):
        value = statistic([units[rng.randrange(len(units))] for _ in units])
        if not math.isnan(value):
            values.append(value)
    if not values:
        return math.nan, math.nan
    values.sort()
    return values[int(alpha / 2 * (len(values) - 1))], values[round((1 - alpha / 2) * (len(values) - 1))]
