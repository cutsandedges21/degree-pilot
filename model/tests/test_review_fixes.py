"""Regression tests for the Phase 1 review findings (2026-09-30)."""
import pytest

from model.eval.__main__ import main
from model.eval.j3cases import build_cases
from model.eval.testset import EvalDoc
from model.jobs.j1 import Course, copy_violations, format_records, parse_records
from model.jobs.j2 import Tag, tag_violations
from model.jobs.j3 import FactsError, check_explanation, parse_facts
from model.jobs.normalize import contains_words
from model.jobs.skills import load_taxonomy

FACTS = """style: why_fit
career: Data Analyst
skill: Quantitative reasoning (High)
evidence: STAT 250 Introduction to Statistics, A
evidence: ECON 301 Econometrics, A-
"""


def test_contains_words_needs_whole_words():
    assert contains_words("Digital Media Club", "Digital Media")
    assert not contains_words("Digital Media Club", "Git")
    assert not contains_words("Won an Excellence award", "Excel")
    assert contains_words("Used C++ and Excel daily", "C++")
    assert contains_words("raising ~$15,000 for", "raising ~$15,000")
    assert contains_words("ECON 201\nIntermediate\nMicroeconomics", "intermediate microeconomics")


def test_copy_rule_needs_whole_tokens_and_case_for_short_values():
    course = Course("ECON 101", "Principles", "", "A", "3.0")
    assert copy_violations(course, "ECON 101 Principles B+ and a note, 13.05") == ["grade='A'", "credits='3.0'"]
    assert copy_violations(course, "ECON 101  Principles  3.0  A") == []


def test_tool_and_quote_checks_need_whole_words():
    taxonomy = load_taxonomy()
    source = "A | club | Digital Media Club |  |  |\nB | Won an Excellence award\n"
    assert tag_violations(Tag("tool", "Git"), source, taxonomy) == ["'Git' is not in the input"]
    assert tag_violations(Tag("tool", "Excel"), source, taxonomy) == ["'Excel' is not in the input"]
    assert tag_violations(Tag("creativity", "Digital Media"), source, taxonomy, activity=True) == []


def test_activity_skill_tags_need_a_real_quote():
    taxonomy = load_taxonomy()
    source = "A | club | Chess Club |  |  | President\nB | Ran a weekly tournament\n"
    assert tag_violations(Tag("leadership"), source, taxonomy, activity=True) == [
        "activity tags need a quote from the item"]
    assert tag_violations(Tag("leadership", "a"), source, taxonomy, activity=True) == ["quote 'a' is too short"]
    assert tag_violations(Tag("quantitative"), "C | MATH 101 | Calculus |  |  |\n", taxonomy) == []


def test_numbers_must_match_whole_fact_numbers():
    text = "Quantitative reasoning shows in STAT 250 with 2 courses and 5 projects."
    check = check_explanation(text, parse_facts(FACTS), load_taxonomy())
    assert set(check.unsupported) == {"2", "5"}


@pytest.mark.parametrize("text", [
    "career: X\nstyle: gap\n",
    "style: why_fit\nevidence: STAT 250, A\nskill: Quantitative reasoning\n",
])
def test_style_comes_first_and_evidence_follows_a_skill(text):
    with pytest.raises(FactsError):
        parse_facts(text)


def test_values_may_hold_form_feeds_and_unicode_line_separators():
    course = Course("A 1", "a\x0cb\u2028c")
    assert parse_records(format_records([course])) == ([course], [])


def test_items_without_evidence_text_are_skipped():
    gold_j2 = "A | club |  |  | 2020 |\n  leadership | x\n"
    assert build_cases([EvalDoc("resume", "r1", "", None, gold_j2)], load_taxonomy()) == []


def test_a_bad_gold_file_is_named(tmp_path):
    doc = tmp_path / "transcript" / "t1"
    doc.mkdir(parents=True)
    (doc / "text.txt").write_text("x", encoding="utf-8")
    (doc / "gold.j1").write_text("X | bad\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="transcript/t1/gold.j1"):
        main(["--testsets", str(tmp_path)])
