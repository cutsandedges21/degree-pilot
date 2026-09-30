from model.eval.__main__ import main


def test_scorecard_on_a_tiny_testset(tmp_path, capsys):
    doc = tmp_path / "transcript" / "t1"
    doc.mkdir(parents=True)
    (doc / "text.txt").write_text("Fall 2024\nSTAT 250 Statistics 3.00 A\n", encoding="utf-8")
    (doc / "gold.j1").write_text("C | STAT 250 | Statistics | Fall 2024 | A | 3.00\n", encoding="utf-8")
    (doc / "gold.j2").write_text("C | STAT 250 | Statistics | Fall 2024 | A | 3.00\n  quantitative\n", encoding="utf-8")
    assert main(["--testsets", str(tmp_path), "--samples", "20"]) == 0
    out = capsys.readouterr().out
    assert "1 docs (transcript 1)" in out
    assert "C.code" in out and "ok (bar 0.95)" in out
    assert "J2 tag (1 docs, 1 items)" in out
    assert "J3 explain (9 cases)" in out


def test_empty_testset_says_so(tmp_path, capsys):
    assert main(["--testsets", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "no labelled documents yet" in out
