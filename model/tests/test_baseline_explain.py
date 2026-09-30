import pytest

from model.baselines.explain import explain
from model.jobs.j3 import check_explanation, parse_facts
from model.jobs.skills import load_taxonomy

FACTS = {
    "why_fit": ("style: why_fit\ncareer: Data Analyst\nskill: Quantitative reasoning (High)\n"
                "evidence: STAT 250 Introduction to Statistics, A\nevidence: ECON 301 Econometrics, A-\n"),
    "gap": "style: gap\ncareer: Data Analyst\nhave: Quantitative reasoning\nneed: Programming\ntool: SQL\n",
    "action": ("style: action\naction: Build a small SQL project with public housing data\n"
               "because: Data Analyst roles ask for SQL\neffort: 3 hours a week\n"),
}


@pytest.mark.parametrize("style", FACTS)
def test_templates_pass_the_fact_check(style):
    facts = parse_facts(FACTS[style])
    text = explain(facts)
    check = check_explanation(text, facts, load_taxonomy())
    assert check.ok, (text, check)


def test_wording():
    assert explain(parse_facts(FACTS["why_fit"])) == (
        "Data Analyst could fit you. Quantitative reasoning (High) shows in "
        "STAT 250 Introduction to Statistics (A) and ECON 301 Econometrics (A-).")
    assert explain(parse_facts(FACTS["gap"])) == (
        "For Data Analyst, you already show Quantitative reasoning. To get there, build Programming and SQL.")
    assert explain(parse_facts(FACTS["action"])) == (
        "Build a small SQL project with public housing data (3 hours a week). Data Analyst roles ask for SQL.")
