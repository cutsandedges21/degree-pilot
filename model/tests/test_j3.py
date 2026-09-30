import pytest

from model.jobs.j3 import FactsError, check_explanation, format_facts, parse_facts
from model.jobs.skills import load_taxonomy

FACTS = """style: why_fit
career: Data Analyst
skill: Quantitative reasoning (High)
evidence: STAT 250 Introduction to Statistics, A
evidence: ECON 301 Econometrics, A-
"""


def test_parse_and_format_round_trip():
    facts = parse_facts(FACTS)
    assert facts.style == "why_fit"
    assert facts.values("evidence") == ["STAT 250 Introduction to Statistics, A", "ECON 301 Econometrics, A-"]
    assert format_facts(facts) == FACTS


@pytest.mark.parametrize("text", ["career: X\n", "style: poem\n", "style: gap\nhobby: x\n", "style: gap\ncareer\n"])
def test_bad_facts_raise(text):
    with pytest.raises(FactsError):
        parse_facts(text)


def test_supported_text_passes():
    text = "Data Analyst could fit you: your A in STAT 250 and A- in ECON 301 show quantitative reasoning."
    check = check_explanation(text, parse_facts(FACTS), load_taxonomy())
    assert check.unsupported == ()
    assert check.used == 4
    assert check.ok


def test_invented_course_grade_number_and_skill_are_caught():
    text = "Data Analyst fits: you got a B in MATH 101, beat 90% of peers, and show programming."
    check = check_explanation(text, parse_facts(FACTS), load_taxonomy())
    assert set(check.unsupported) == {"MATH 101", "101", "90", "B", "Programming"}
    assert not check.ok
