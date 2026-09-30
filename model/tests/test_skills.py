import pytest

from model.jobs.skills import load_taxonomy, parse_taxonomy


def test_taxonomy_loads_with_unique_ids():
    taxonomy = load_taxonomy()
    assert len(taxonomy.skills) == 20
    assert {"writing", "quantitative", "leadership", "programming"} <= taxonomy.skill_ids
    assert {"SQL", "Excel", "Python"} <= set(taxonomy.tools)


def test_every_skill_has_keywords():
    for skill in load_taxonomy().skills:
        assert len(skill.keywords) >= 5, skill.id


def test_skill_lookup():
    assert load_taxonomy().skill("writing").name == "Written communication"


def _raw(*ids, keyword="x"):
    return {"skills": [{"id": i, "name": i, "description": "", "keywords": [keyword]} for i in ids], "tools": []}


def test_rejects_duplicate_ids():
    with pytest.raises(ValueError):
        parse_taxonomy(_raw("a", "a"))


def test_rejects_reserved_tool_id():
    with pytest.raises(ValueError):
        parse_taxonomy(_raw("tool"))


def test_rejects_uppercase_keywords():
    with pytest.raises(ValueError):
        parse_taxonomy(_raw("a", keyword="Excel"))
