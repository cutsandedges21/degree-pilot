from model.eval.label import check, main, prefill_j1, prefill_j2


def _doc(tmp_path, text, family="transcript"):
    doc = tmp_path / family / "doc1"
    doc.mkdir(parents=True)
    (doc / "text.txt").write_text(text, encoding="utf-8")
    return doc


def test_prefill_j1_writes_baseline_rows_once(tmp_path):
    doc = _doc(tmp_path, "Fall 2024\nECON 101 Principles 3.00 A\n")
    path = prefill_j1(doc)
    assert "C | ECON 101 | Principles | Fall 2024 | A | 3.00\n" in path.read_text(encoding="utf-8")
    path.write_text("# edited\n", encoding="utf-8")
    prefill_j1(doc)
    assert path.read_text(encoding="utf-8") == "# edited\n"


def test_prefill_j2_tags_the_gold_rows(tmp_path):
    doc = _doc(tmp_path, "STAT 250 Statistics 3.00 A\n")
    prefill_j1(doc)
    text = prefill_j2(doc).read_text(encoding="utf-8")
    assert "C | STAT 250 | Statistics |  | A | 3.00\n  quantitative\n  data_analysis\n" in text


def test_check_finds_copy_and_tag_problems(tmp_path):
    doc = _doc(tmp_path, "STAT 250 Statistics 3.00 A\n")
    (doc / "gold.j1").write_text("C | STAT 250 | Statistics | Fall 2031 | A | 3.00\n", encoding="utf-8")
    (doc / "gold.j2").write_text("C | STAT 250 | Statistics |  | A | 3.00\n  juggling\n", encoding="utf-8")
    assert check(doc) == [
        "gold.j1 not in text.txt: term='Fall 2031'",
        "gold.j2 Statistics: unknown skill 'juggling'",
    ]


def test_check_passes_prefilled_files(tmp_path, capsys):
    doc = _doc(tmp_path, "STAT 250 Statistics 3.00 A\n")
    prefill_j1(doc)
    prefill_j2(doc)
    assert main(["check", str(doc)]) == 0
    assert capsys.readouterr().out.strip() == "ok"
