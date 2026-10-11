"""FAULT-INJECTION tests (label: INJECTED) — MSVE-WO-1.2 §4.

These tests DELIBERATELY corrupt a component to verify the pipeline
detects disagreement, withholds unjustified assurance, and manufactures
no positive conclusion. They are labelled INJECTED and kept separate from
the observed-behavior tests.
"""
import pytest

from conftest import CFG, doc, holds_query, run_doc


def _inject_solver_outcome(monkeypatch, outcome):
    import msve.pipeline as P
    real = P.solv.run
    def fake(query, timeout_ms, invocation_id):
        o = real(query, timeout_ms, invocation_id)
        o["outcome"] = outcome
        return o
    monkeypatch.setattr(P.solv, "run", fake)


def test_injected_core_a_lie_detected(monkeypatch):
    # INJECTED: Core A claims SAT for a genuinely UNSAT query.
    # Core B honestly finds nothing -> disagreement recorded, no basis.
    d = doc()
    d["claim"]["query"] = holds_query(negated=True)  # genuinely UNSAT
    d["assurance_ask"] = "INDEPENDENT_RECOMPUTE"
    _inject_solver_outcome(monkeypatch, "SAT")
    r = run_doc(d)
    assert r["assurance_achieved"] is None
    assert any(x["checker"] == "core-b" for x in r["discrepancies"])
    # the injected SAT must not manufacture a VIOLATED positive either... 
    # (semantic follows the recorded observation; the lie is Core A's,
    #  which the pipeline cannot see through — documented limitation)
    assert r["solver_observation"]["outcome"] == "SAT"


def test_injected_core_b_false_sat_detected(monkeypatch):
    # INJECTED: Core B falsely reports SAT for an UNSAT query while Core A
    # honestly reports UNSAT -> no agreement (SAT vs UNSAT mismatch).
    import msve.pipeline as P
    monkeypatch.setattr(P.checker, "check",
                        lambda q, b: {"verdict": "SAT", "witness": {"x": 0}, "bound": b})
    d = doc()
    d["claim"]["query"] = holds_query(negated=True)  # genuinely UNSAT
    d["assurance_ask"] = "INDEPENDENT_RECOMPUTE"
    r = run_doc(d)
    assert r["assurance_achieved"] is None
    assert len(r["discrepancies"]) == 1


def test_injected_core_b_false_agreement_trust_boundary(monkeypatch):
    # INJECTED: documents the trust boundary. If Core B LIES about
    # agreement (returns True), the pipeline awards the basis — the engine
    # cannot detect a lying checker. This is a disclosed limitation, not
    # a passing security claim.
    import msve.pipeline as P
    monkeypatch.setattr(P.checker, "agrees_with_solver",
                        lambda q, o, b: (True, "INJECTED false agreement", None))
    d = doc()
    d["claim"]["query"] = holds_query(negated=True)
    d["assurance_ask"] = "INDEPENDENT_RECOMPUTE"
    r = run_doc(d)
    # documents the boundary: award follows the (false) agreement signal
    assert r["assurance_achieved"] == "INDEPENDENT_RECOMPUTE"
