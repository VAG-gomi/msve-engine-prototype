"""Query DSL (D3) and solver outcome tests: SAT, UNSAT, UNKNOWN."""
import pytest

from conftest import CFG, doc, holds_query, run_doc
from msve import checker, solver
from msve.errors import MSVEError
from msve.queries import denote, query_id, validate


def test_query_schema_valid():
    sig = validate(holds_query())
    assert sig == {"x": "Int"}


def test_query_unbound_name():
    q = holds_query()
    q["assertions"] = [["=", "y", 1]]
    with pytest.raises(MSVEError) as e:
        validate(q)
    assert e.value.code == "MALFORMED_INPUT"


def test_query_sort_mismatch():
    q = {"language": "msve-arith-v1", "declarations": [{"name": "x", "sort": "Int"}],
         "assertions": [["and", "x", True]]}
    with pytest.raises(MSVEError):
        validate(q)


def test_query_unknown_operator():
    q = {"language": "msve-arith-v1", "declarations": [],
         "assertions": [["frobnicate", 1, 2]]}
    with pytest.raises(MSVEError):
        validate(q)


def test_query_id_stable():
    assert query_id(holds_query()) == query_id(holds_query())


def test_query_type_handling_bool():
    q = {"language": "msve-arith-v1",
         "declarations": [{"name": "b", "sort": "Bool"}],
         "assertions": [["or", "b", ["not", "b"]]]}
    validate(q)
    _, asserts = denote(q)
    assert len(asserts) == 1


def test_holds_unsat_gives_holds():
    d = doc()
    d["claim"]["query"] = holds_query(negated=True)  # negation unsat => holds
    d["assurance_ask"] = "SOLVER_BACKED"
    r = run_doc(d)
    assert r["solver_observation"]["outcome"] == "UNSAT"
    assert r["semantic_result"]["variant"] == "HOLDS"
    assert r["assurance_achieved"] == "SOLVER_BACKED"
    assert r["assurance_weak"] is False


def test_holds_sat_gives_violated_with_witness():
    d = doc()
    d["claim"]["query"] = holds_query(negated=False)  # property itself is sat
    # query must be the NEGATION for holds; here we give the positive form,
    # so the solver finds it sat -> VIOLATED with witness
    d["assurance_ask"] = "SOLVER_BACKED"
    r = run_doc(d)
    assert r["solver_observation"]["outcome"] == "SAT"
    assert r["semantic_result"]["variant"] == "VIOLATED"
    assert "witness" in r["semantic_result"]
    assert r["assurance_achieved"] == "SOLVER_BACKED"


def test_derive_is_diagnostic_only():
    d = doc()
    d["claim"]["kind"] = "derive"
    d["claim"]["query"] = holds_query()
    # no basis asked: solver runs, result is INCONCLUSIVE, nothing awarded
    r = run_doc(d)
    assert r["admission"] == "ACCEPTED"
    assert r["semantic_result"]["variant"] == "INCONCLUSIVE"
    assert r["assurance_achieved"] is None


def test_derive_solver_backed_denied():
    from msve.errors import MSVEError
    import pytest
    d = doc()
    d["claim"]["kind"] = "prove"
    d["claim"]["query"] = holds_query()
    d["assurance_ask"] = "SOLVER_BACKED"
    with pytest.raises(MSVEError) as e:
        run_doc(d)
    assert e.value.code == "EVIDENCE_MISSING"


def test_unknown_outcome_recorded():
    # UNKNOWN recording path: patch the Z3 check to return unknown
    # deterministically (timeout-based unknown is not deterministic)
    import z3
    import msve.solver as S
    real_check = z3.Solver.check
    z3.Solver.check = lambda self: z3.unknown
    try:
        obs = S.run(holds_query(), timeout_ms=5000, invocation_id="inv-test")
    finally:
        z3.Solver.check = real_check
    assert obs["outcome"] == "UNKNOWN"
    assert obs["tool"] == "z3"
    assert "version" in obs
    assert "reason" in obs


def test_unknown_inconclusive_weak_backed_d1():
    # D1: UNKNOWN + INCONCLUSIVE may qualify for weak SOLVER_BACKED
    d = doc()
    d["claim"]["kind"] = "prove"
    d["claim"]["query"] = holds_query()
    d["assurance_ask"] = "SOLVER_BACKED"
    # simulate: run pipeline but force the observation to UNKNOWN
    import msve.pipeline as P
    real_run = P.solv.run
    def fake_run(query, timeout_ms, invocation_id, config="default"):
        o = real_run(query, timeout_ms, invocation_id)
        o["outcome"] = "UNKNOWN"
        o["reason"] = "injected for D1 test"
        return o
    P.solv.run = fake_run
    try:
        r = run_doc(d)
    finally:
        P.solv.run = real_run
    assert r["semantic_result"]["variant"] == "INCONCLUSIVE"
    assert r["assurance_achieved"] == "SOLVER_BACKED"
    assert r["assurance_weak"] is True
    assert any("not a proof" in n for n in r["assurance_notes"])


def test_unknown_never_positive_conclusion():
    d = doc()
    d["claim"]["kind"] = "holds"
    d["claim"]["query"] = holds_query()
    import msve.pipeline as P
    real_run = P.solv.run
    def fake_run(query, timeout_ms, invocation_id, config="default"):
        o = real_run(query, timeout_ms, invocation_id)
        o["outcome"] = "UNKNOWN"
        return o
    P.solv.run = fake_run
    try:
        r = run_doc(d)
    finally:
        P.solv.run = real_run
    assert r["semantic_result"]["variant"] == "INCONCLUSIVE"
    assert r["semantic_result"]["variant"] != "HOLDS"


def test_assumptions_preserved_unverified():
    d = doc()
    d["claim"]["assumptions"] = ["every natural is finite", "x in [0,10]"]
    r = run_doc(d)
    assert r["assumptions_unverified"] == ["every natural is finite", "x in [0,10]"]
