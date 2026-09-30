from model.eval.score_j2 import J2Result, score_j2
from model.jobs.j1 import Course
from model.jobs.j2 import Item, Tag
from model.jobs.skills import load_taxonomy

ITEM = Item((Course("STAT 250", "Statistics"),))


def test_counts_keys():
    gold = [Tag("quantitative"), Tag("data_analysis")]
    result = score_j2("quantitative\nwriting\n", gold, ITEM, load_taxonomy())
    assert (result.counts.tp, result.counts.fp, result.counts.fn) == (1, 1, 1)
    assert result.bad_tags == 0


def test_counts_bad_tags():
    result = score_j2("juggling\ntool | SQL\na | b | c\n", [], ITEM, load_taxonomy())
    assert result.bad_tags == 3


def test_results_add_up():
    total = J2Result()
    total += score_j2("quantitative\n", [Tag("quantitative")], ITEM, load_taxonomy())
    total += score_j2("", [Tag("writing")], ITEM, load_taxonomy())
    assert (total.items, total.counts.tp, total.counts.fn) == (2, 1, 1)
