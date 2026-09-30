from model.eval.j3cases import build_cases
from model.eval.testset import EvalDoc, load_testset
from model.jobs.j3 import Facts, format_facts, parse_facts
from model.jobs.skills import load_taxonomy


def test_loads_docs_in_family_order(tmp_path):
    for family, doc_id in [("syllabus", "s1"), ("transcript", "t2"), ("transcript", "t1")]:
        folder = tmp_path / family / doc_id
        folder.mkdir(parents=True)
        (folder / "text.txt").write_text(f"{doc_id} text", encoding="utf-8")
    (tmp_path / "transcript" / "t1" / "gold.j1").write_text("C | X 100 |  |  |  |\n", encoding="utf-8")
    (tmp_path / "resume" / "no-text-yet").mkdir(parents=True)
    docs = load_testset(tmp_path)
    assert [(d.family, d.doc_id) for d in docs] == [("transcript", "t1"), ("transcript", "t2"), ("syllabus", "s1")]
    assert docs[0].gold_j1 == "C | X 100 |  |  |  |\n"
    assert docs[0].gold_j2 is None


def test_missing_root_gives_no_docs(tmp_path):
    assert load_testset(tmp_path / "nope") == []


def test_cases_from_one_labelled_course():
    gold_j2 = "C | STAT 250 | Statistics |  | A |\n  quantitative\n  data_analysis\n"
    cases = build_cases([EvalDoc("transcript", "t1", "", None, gold_j2)], load_taxonomy())
    assert len(cases) == 12   # 4 careers use these skills, 3 cases each
    assert cases[0] == Facts("why_fit", (
        ("career", "Data Analyst"),
        ("skill", "Quantitative reasoning (Developing)"), ("evidence", "STAT 250 Statistics, A"),
        ("skill", "Data analysis (Developing)"), ("evidence", "STAT 250 Statistics, A"),
    ))
    assert cases[1] == Facts("gap", (
        ("career", "Data Analyst"), ("have", "Quantitative reasoning"), ("have", "Data analysis"),
        ("need", "Programming"),
    ))
    assert cases[2].style == "action"
    assert all(parse_facts(format_facts(case)) == case for case in cases)
