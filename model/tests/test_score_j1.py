from model.eval.score_j1 import J1Result, score_j1


def test_perfect_prediction():
    gold = "C | ECON 101 | Principles | Fall 2024 | A | 3.00\n"
    result = score_j1(gold, gold, "ECON 101 Principles Fall 2024 A 3.00")
    assert result.fields["C.code"].f1 == 1.0
    assert result.exact_rows == result.gold_rows == 1
    assert result.copy_violations == 0


def test_wrong_grade_counts_once_each_way():
    gold = "C | ECON 101 | Principles | Fall 2024 | A | 3.00\n"
    predicted = "C | ECON 101 | Principles | Fall 2024 | B | 3.00\n"
    result = score_j1(predicted, gold, "ECON 101 Principles Fall 2024 A B 3.00")
    grade = result.fields["C.grade"]
    assert (grade.tp, grade.fp, grade.fn) == (0, 1, 1)
    assert result.fields["C.title"].f1 == 1.0
    assert result.exact_rows == 0


def test_missing_and_extra_rows():
    gold = "C | ECON 101 | Principles |  | A |\nC | MATH 151 | Calculus I |  | B+ |\n"
    predicted = "C | ECON 101 | Principles |  | A |\nC | PHYS 101 | Physics |  | C |\n"
    code = score_j1(predicted, gold, "").fields["C.code"]
    assert (code.tp, code.fp, code.fn) == (1, 1, 1)


def test_unparseable_lines_are_counted():
    assert score_j1("garbage\n", "", "").unparseable == 1


def test_results_add_up():
    total = J1Result()
    total += score_j1("C | A 1 |  |  |  |\n", "C | A 1 |  |  |  |\n", "A 1")
    total += score_j1("", "C | B 2 |  |  |  |\n", "B 2")
    assert total.gold_rows == 2
    assert total.fields["C.code"].recall == 0.5
