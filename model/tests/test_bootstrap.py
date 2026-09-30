import math

from model.eval.bootstrap import bootstrap_ci


def test_constant_statistic_has_zero_width():
    assert bootstrap_ci([1, 2, 3], lambda sample: 5.0, n=50) == (5.0, 5.0)


def test_interval_brackets_the_mean_and_is_repeatable():
    units = list(range(20))

    def mean(sample):
        return sum(sample) / len(sample)

    low, high = bootstrap_ci(units, mean, n=500)
    assert low < mean(units) < high
    assert bootstrap_ci(units, mean, n=500) == (low, high)


def test_empty_units_give_nan():
    low, high = bootstrap_ci([], lambda sample: 1.0)
    assert math.isnan(low) and math.isnan(high)
