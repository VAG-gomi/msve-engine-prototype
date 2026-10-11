"""WO-1.9A regression tests: findings C1–C6 corrections."""
import pytest

from msve import checker
from msve.errors import MSVEError
from msve.queries import query_id

from conftest import doc, holds_query, run_doc


# ---------------- Finding 2: query-identity binding ----------------

def test_c2_query_id_in_result():
    d = doc()
    q = holds_query()
    d["claim"]["query"] = q
    r = run_doc(d)
    assert r["query_id"] == query_id(q)
    assert r["query_id"] == r["solver_observation"]["query_id"]


def test_c2_query_id_none_without_query():
    d = doc()
    # no query -> no solver observation, query_id is None
    r = run_doc(d)
    assert r["query_id"] is None


def test_c2_invocation_id_fixed_width():
    # both operands are 64-char hex; delimiter at deterministic position
    from msve.pipeline import _invocation_id
    cid = "a" * 64
    qid = "b" * 64
    inv = _invocation_id(cid, qid)
    assert len(inv) == 64
    # different orderings / similar values don't collide
    assert _invocation_id(cid, qid) != _invocation_id(qid, cid)


# ---------------- Finding 3: witness paths ----------------

def test_c3_witness_validated_against_query():
    q = {"language": "msve-arith-v1",
         "declarations": [{"name": "x", "sort": "Int"}],
         "assertions": [[">", "x", 0]]}
    ok, why, witness = checker.agrees_with_solver(q, "SAT", bound=5)
    assert ok is True
    assert witness is not None
    assert checker.validate_witness(q, witness) is True


def test_c3_bad_witness_rejected():
    q = {"language": "msve-arith-v1",
         "declarations": [{"name": "x", "sort": "Int"}],
         "assertions": [[">", "x", 0]]}
    assert checker.validate_witness(q, {"x": -5}) is False
    assert checker.validate_witness(q, {"x": "not-an-int"}) is False
    assert checker.validate_witness(q, {}) is False
    assert checker.validate_witness(q, {"x": 5}) is True


def test_c3_recompute_record_carries_witness():
    d = doc()
    d["claim"]["query"] = {"language": "msve-arith-v1",
                           "declarations": [{"name": "x", "sort": "Int"}],
                           "assertions": [[">", "x", 0]]}
    d["assurance_ask"] = "INDEPENDENT_RECOMPUTE"
    r = run_doc(d)
    # SAT query: Core B should corroborate with a witness
    rec = r["evidence"]["recompute"]
    assert rec["witness_validated"] is True
    assert rec["witness"] is not None
    assert checker.validate_witness(d["claim"]["query"], rec["witness"])


def test_c3_bounded_no_witness_inconclusive():
    # query SAT only outside Core B's bound -> no corroboration, no basis
    d = doc()
    d["claim"]["query"] = {"language": "msve-arith-v1",
                           "declarations": [{"name": "x", "sort": "Int"}],
                           "assertions": [[">", "x", 100]]}
    d["assurance_ask"] = "INDEPENDENT_RECOMPUTE"
    r = run_doc(d)
    assert r["assurance_achieved"] is None or r["assurance_achieved"] != "INDEPENDENT_RECOMPUTE"


# ---------------- Finding 4: null/empty distinctions ----------------

def test_c4_null_goal_ref_accepted():
    d = doc()
    d["claim"]["goal_ref"] = None
    d["claim"]["inputs_ref"] = None
    r = run_doc(d)
    assert r["admission"] == "ACCEPTED"


def test_c4_empty_goal_ref_rejected():
    d = doc()
    d["claim"]["goal_ref"] = ""
    with pytest.raises(MSVEError) as e:
        run_doc(d)
    assert e.value.code == "MALFORMED_INPUT"


def test_c4_nonstring_goal_ref_rejected():
    d = doc()
    d["claim"]["goal_ref"] = 123
    with pytest.raises(MSVEError) as e:
        run_doc(d)
    assert e.value.code == "MALFORMED_INPUT"


def test_c4_null_assumption_element_rejected():
    from msve.identity import canonical_bytes
    desc = {"kind": "holds", "proposition": "p", "goal_ref": "g",
            "inputs_ref": "i", "assumptions": ["a", None],
            "spec_version": "0.8.9.1"}
    with pytest.raises(TypeError):
        canonical_bytes(desc)
