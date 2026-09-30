import pytest

from model.jobs.j1 import Activity, Bullet, Course, Deliverable
from model.jobs.j2 import (
    Item, Tag, TagError, format_gold_j2, format_tags, items_from_records,
    parse_gold_j2, parse_tag, tag_violations,
)
from model.jobs.skills import load_taxonomy


def test_tag_round_trip():
    for line in ["quantitative", "leadership | President", "tool | SQL"]:
        assert format_tags([parse_tag(line)]) == line + "\n"


@pytest.mark.parametrize("line", ["tool", "a | b | c", " | x"])
def test_bad_tags_raise(line):
    with pytest.raises(TagError):
        parse_tag(line)


def test_keys_ignore_quotes_and_tool_case():
    assert Tag("leadership", "Led").key == "leadership"
    assert Tag("tool", "sql").key == Tag("tool", "SQL").key


def test_items_group_bullets_under_activities():
    course = Course("STAT 250", "Statistics")
    club = Activity("club", "Chess Club")
    records = [course, club, Bullet("Ran weekly games"), Deliverable("Quiz", "5%"), Bullet("orphan")]
    assert items_from_records(records) == [Item((course,)), Item((club, Bullet("Ran weekly games")))]


GOLD = (
    "C | STAT 250 | Statistics |  | A |\n"
    "  quantitative\n"
    "  data_analysis\n"
    "\n"
    "A | club | Chess Club |  |  | President\n"
    "B | Ran weekly games\n"
    "  leadership | President\n"
)


def test_gold_j2_round_trip():
    pairs, errors = parse_gold_j2(GOLD)
    assert errors == []
    assert [tag.key for tag in pairs[0][1]] == ["quantitative", "data_analysis"]
    assert pairs[1][0].records[1] == Bullet("Ran weekly games")
    assert pairs[1][1] == [Tag("leadership", "President")]
    assert format_gold_j2(pairs) == GOLD


def test_gold_j2_errors():
    _, errors = parse_gold_j2("  quantitative\nD | Quiz | 5% |\n  writing\n")
    assert errors == [
        "line 1: a tag before any record",
        "tags under a record that isn't a course or activity: D | Quiz | 5% |",
    ]


def test_tag_violations():
    taxonomy = load_taxonomy()
    source = "A | club | Chess Club |  |  | President\nB | Used Excel to track members\n"
    assert tag_violations(Tag("leadership", "President"), source, taxonomy) == []
    assert tag_violations(Tag("tool", "Excel"), source, taxonomy) == []
    assert tag_violations(Tag("juggling"), source, taxonomy) == ["unknown skill 'juggling'"]
    assert tag_violations(Tag("tool", "SQL"), source, taxonomy) == ["'SQL' is not in the input"]
    assert tag_violations(Tag("tool", "Notepad"), source + "Notepad", taxonomy) == ["unknown tool 'Notepad'"]
