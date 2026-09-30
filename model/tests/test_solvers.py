import pytest

from model.solvers import get_solver


def test_baseline_solver_speaks_the_wire_formats():
    solver = get_solver("baseline")
    assert solver.name == "baseline"
    assert solver.extract("ECON 101 Principles 3.00 A\n", "transcript") == "C | ECON 101 | Principles |  | A | 3.00\n"
    assert solver.tag("C | STAT 250 | Statistics |  | A |\n") == "quantitative\ndata_analysis\n"
    text = solver.explain("style: gap\ncareer: Data Analyst\nhave: Teamwork\nneed: Programming\n")
    assert text.startswith("For Data Analyst")


def test_unknown_solver():
    with pytest.raises(KeyError):
        get_solver("gpt")
