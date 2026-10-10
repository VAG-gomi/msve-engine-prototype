"""Core B independent checker tests (D4)."""
from conftest import holds_query
from msve import checker


def test_core_b_sat_with_witness():
    q = {"language": "msve-arith-v1",
         "declarations": [{"name": "x", "sort": "Int"}],
         "assertions": [[">", "x", 0]]}
    r = checker.check(q, bound=5)
    assert r["verdict"] == "SAT"
    assert r["witness"]["x"] > 0


def test_core_b_unknown_when_out_of_bound():
    q = {"language": "msve-arith-v1",
         "declarations": [{"name": "x", "sort": "Int"}],
         "assertions": [[">", "x", 100]]}
    r = checker.check(q, bound=5)
    assert r["verdict"] == "UNKNOWN"


def test_core_b_never_claims_unsat():
    q = holds_query(negated=True)  # genuinely UNSAT
    r = checker.check(q, bound=5)
    assert r["verdict"] in ("SAT", "UNKNOWN")
    assert r["verdict"] != "UNSAT"


def test_agreement_sat_sat():
    q = {"language": "msve-arith-v1",
         "declarations": [{"name": "x", "sort": "Int"}],
         "assertions": [[">", "x", 0]]}
    ok, why = checker.agrees_with_solver(q, "SAT", bound=5)
    assert ok is True


def test_no_agreement_for_unsat():
    q = holds_query(negated=True)
    ok, why = checker.agrees_with_solver(q, "UNSAT", bound=5)
    assert ok is False
    assert "never" in why or "UNSAT" in why


def test_checker_uses_independent_algorithm():
    # core B source must not import z3 (algorithmic independence)
    import inspect
    src = inspect.getsource(checker)
    assert "import z3" not in src
