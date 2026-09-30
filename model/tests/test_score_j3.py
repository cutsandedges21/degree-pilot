from model.eval.score_j3 import J3Result, score_j3
from model.jobs.j3 import parse_facts
from model.jobs.skills import load_taxonomy


def test_pass_and_fail():
    facts = parse_facts("style: action\naction: Build a SQL project\nbecause: Analysts use SQL\neffort: 3 hours\n")
    total = J3Result()
    total += score_j3("Build a SQL project (3 hours). Analysts use SQL.", facts, load_taxonomy())
    total += score_j3("Build a SQL project in 9 hours.", facts, load_taxonomy())
    assert (total.cases, total.passed) == (2, 1)
    assert total.failures == [("Build a SQL project in 9 hours.", ("9",))]
