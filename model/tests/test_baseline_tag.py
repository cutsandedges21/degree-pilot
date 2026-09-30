from model.baselines.tag import tag
from model.jobs.j2 import Tag, tag_violations
from model.jobs.skills import load_taxonomy


def test_course_tags_come_from_the_title_without_quotes():
    item = "C | STAT 250 | Introduction to Statistics | Fall 2024 | A | 3.00\n"
    assert tag(item, load_taxonomy()) == [Tag("quantitative"), Tag("data_analysis")]


def test_activity_tags_quote_the_input():
    item = ("A | club | President | Economics Society | Sep 2024 – Present |\n"
            "B | Organized 6 events and a budget in Excel\n")
    assert tag(item, load_taxonomy()) == [
        Tag("data_analysis", "Excel"),
        Tag("leadership", "President"),
        Tag("organization", "Organized"),
        Tag("financial", "budget"),
        Tag("tool", "Excel"),
    ]


def test_tags_obey_the_quote_rule():
    taxonomy = load_taxonomy()
    item = "A | job | Cashier | Metro |  |\nB | Served 200 customers a day\n"
    tags = tag(item, taxonomy)
    assert Tag("client_service", "customers") in tags
    for t in tags:
        assert tag_violations(t, item, taxonomy) == []


def test_no_tags_for_non_items():
    assert tag("D | Quiz | 5% |\n", load_taxonomy()) == []
