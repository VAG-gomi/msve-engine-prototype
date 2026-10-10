"""Bounded-checker limitation tests (label: OBSERVED) — MSVE-WO-1.2 §5.

Core B must never treat an incomplete search or an insufficient bound as
universal proof. These tests pin that property on observed behavior.
"""
from conftest import CFG
from msve import checker


def _q(assertions, decls=None):
    return {"language": "msve-arith-v1",
            "declarations": [{"name": n, "sort": s} for n, s in (decls or [("x", "Int")])],
            "assertions": assertions}


def test_core_b_never_returns_bare_unsat():
    # across a battery of queries, Core B's verdict is never unqualified UNSAT
    queries = [
        _q([[">", "x", 0]]),
        _q([["=", ["*", "x", "x"], 2]]),
        _q([[">", "x", 100]]),
        _q([["and", [">", "x", 0], ["<", "x", 0]]]),
        _q([[">", "x", 0]], decls=[("x", "Int"), ("b", "Bool")]),
    ]
    for qq in queries:
        r = checker.check(qq, bound=5)
        assert r["verdict"] in ("SAT", "UNKNOWN"), qq
        assert r["verdict"] != "UNSAT"


def test_insufficient_bound_yields_unknown_not_proof():
    # SAT only at x=100; bound 5 cannot see it -> UNKNOWN, never "no solution"
    r = checker.check(_q([["=", "x", 100]]), bound=5)
    assert r["verdict"] == "UNKNOWN"
    assert "incomplete" in r["note"]


def test_larger_bound_finds_witness():
    r = checker.check(_q([["=", "x", 100]]), bound=100)
    assert r["verdict"] == "SAT"
    assert r["witness"]["x"] == 100


def test_witness_is_checkable():
    # a SAT verdict always carries a witness that satisfies the assertions
    r = checker.check(_q([[">", "x", 0]]), bound=5)
    assert r["verdict"] == "SAT"
    assert r["witness"]["x"] > 0
