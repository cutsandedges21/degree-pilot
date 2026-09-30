from model.jobs.normalize import contains, norm


def test_collapses_whitespace_and_case():
    assert norm("  Intermediate \n  Microeconomics ") == "intermediate microeconomics"


def test_keeps_grade_signs_and_code_hyphens():
    assert norm("A-") == "a-"
    assert norm("B+") == "b+"
    assert norm("603-101-MQ") == "603-101-mq"


def test_trims_edge_punctuation():
    assert norm("(Fall 2025)") == "fall 2025"
    assert norm("• Built dashboards.") == "built dashboards"


def test_nfkc():
    assert norm("Ｆｉｎａｎｃｅ") == "finance"


def test_contains_across_line_breaks():
    assert contains("ECON 201\nIntermediate\nMicroeconomics", "intermediate microeconomics")
    assert not contains("ECON 201", "ECON 202")
