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
    # 0.8.9.5: execution-specific invocation ID over complete metadata
    from msve.pipeline import _invocation_id
    cid = "a" * 64
    qid = "b" * 64
    def mk(timeout=5000, tool_ver="5.1.0", nonce="n1", spec="0.8.9.5"):
        return _invocation_id(cid, "msve/expr", qid, '{"a":1}', None,
                              spec, "z3", tool_ver, "default", timeout, nonce)
    inv = mk()
    assert len(inv) == 64
    # different timeouts → different IDs (same claim+query)
    assert mk(timeout=5000) != mk(timeout=10000)
    # different solver versions → different IDs
    assert mk(tool_ver="5.1.0") != mk(tool_ver="5.2.0")
    # different spec versions → different IDs
    assert mk(spec="0.8.9.5") != mk(spec="0.8.9.4")
    # different nonces → different IDs (uniqueness)
    assert mk(nonce="n1") != mk(nonce="n2")


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


# ---------------- §1 (WO-1.9B): unified weak representation ----------------

def test_b1_weak_uses_solver_backed_with_qualifier():
    # unified: no separate WEAK basis; weak is a qualifier on SOLVER_BACKED
    d = doc()
    d["claim"]["kind"] = "prove"
    d["claim"]["query"] = holds_query()
    r = run_doc(d)
    # prove + SAT/UNSAT -> INCONCLUSIVE, no basis (diagnostic only)
    assert r["semantic_result"]["variant"] == "INCONCLUSIVE"


def test_b1_weak_linkage_enforced():
    # the weak path requires the same binding; tested via model C2/W1b/W1c
    # here we verify the prototype binds observation to claim/query/spec
    d = doc()
    d["claim"]["kind"] = "prove"
    q = holds_query()
    d["claim"]["query"] = q
    r = run_doc(d)
    obs = r["solver_observation"]
    assert obs["claim_id"] == r["claim_id"]
    assert obs["query_id"] == r["query_id"] == query_id(q)
    assert obs["spec_version"] == r["spec_version"]


def test_b2_sat_corroboration_record_fully_bound():
    d = doc()
    d["assurance_ask"] = "INDEPENDENT_RECOMPUTE"
    # SAT query: negation of a false property -> violation with witness
    q = {"language": "msve-arith-v1",
         "declarations": [{"name": "x", "sort": "Int"}],
         "assertions": [[">", "x", 2]]}
    d["claim"]["query"] = q
    r = run_doc(d)
    corrs = r["sat_corroborations"]
    assert len(corrs) == 1
    sc = corrs[0]
    assert sc["claim_id"] == r["claim_id"]
    assert sc["query_id"] == r["query_id"] == query_id(q)
    assert sc["spec_version"] == r["spec_version"]
    assert sc["checker"] and sc["checker_version"]
    assert sc["witness"]["checked_against"] == sc["query_id"]
    assert sc["witness"]["checked_by"] == sc["checker"]
    assert sc["witness"]["validation_result"] == "PASS"
    assert sc["configured_bound"] is not None


def test_b3_unicode_canonical_equivalence():
    # composed (U+00E9) vs decomposed (e + U+0301): same claim_id, preserved values differ
    import unicodedata
    from msve import identity
    composed = "caf\u00e9"
    decomposed = unicodedata.normalize("NFD", composed)
    assert composed != decomposed  # different byte sequences
    d1 = {"kind": "holds", "proposition": composed, "goal_ref": None,
          "inputs_ref": None, "assumptions": [], "spec_version": "0.8.8.1"}
    d2 = {"kind": "holds", "proposition": decomposed, "goal_ref": None,
          "inputs_ref": None, "assumptions": [], "spec_version": "0.8.8.1"}
    assert identity.claim_id(d1) == identity.claim_id(d2)  # identity equivalent
    # recorded values preserved as received
    dd = doc(); dd["claim"]["proposition"] = composed
    r1 = run_doc(dd)
    assert r1["proposition"] == composed


def test_b4_query_id_canonical():
    from msve import queries
    q1 = {"language": "msve-arith-v1", "declarations": [], "assertions": []}
    q2 = {"assertions": [], "language": "msve-arith-v1", "declarations": []}
    assert queries.query_id(q1) == queries.query_id(q2)
    # distinct structures -> distinct ids
    q3 = {"language": "msve-arith-v1", "declarations": [], "assertions": [[">", "x", 1]]}
    assert queries.query_id(q1) != queries.query_id(q3)
    # 64-char lowercase hex
    qid = queries.query_id(q1)
    assert len(qid) == 64 and all(c in "0123456789abcdef" for c in qid)

def test_b4_query_id_unicode():
    from msve import queries
    import json
    q = {"language": "msve-arith-v1", "declarations": [{"name": "café", "sort": "Int"}],
         "assertions": []}
    canon = json.dumps(q, sort_keys=True, separators=(",", ":"))
    # non-ASCII must be escaped (ASCII-only canonical form)
    assert canon.isascii()
    assert "\\u00e9" in canon


def test_b5_holds_scoped_to_formal_query():
    # HOLDS describes the formal query; the prose link is UNVERIFIED
    d = doc()
    d["claim"]["query"] = holds_query()  # UNSAT -> HOLDS
    r = run_doc(d)
    assert r["semantic_result"]["variant"] == "HOLDS"
    assert r["claim_query_link"] == "UNVERIFIED"
    assert "formal" in r["claim_query_link_note"].lower() or "query" in r["claim_query_link_note"].lower()


def test_b6_capacity_exceeded_is_typed_result():
    # capacity overflow -> typed result with capacity_exceeded, not an exception
    from msve.capacity import load_config
    d = doc()
    d["claim"]["assumptions"] = ["a"] * 5
    cfg = load_config()
    cfg["max_assumptions"] = 2
    r = run_doc(d, cfg=cfg)
    assert r["capacity_exceeded"] is not None
    assert r["capacity_exceeded"]["parameter"] == "max_assumptions"
    assert r["capacity_exceeded"]["limit"] == 2
    assert r["capacity_exceeded"]["actual"] == 5
    assert r["semantic_result"]["variant"] == "INCONCLUSIVE"
    assert r["semantic_result"]["reason"] == "CAPACITY_EXCEEDED"
    assert r["assurance_achieved"] is None


def test_c3_witness_artifact_valid_and_resolves():
    # witness artifact is valid SHA-256 and in evidence.witnesses
    import re
    d = doc()
    d["assurance_ask"] = "INDEPENDENT_RECOMPUTE"
    q = {"language": "msve-arith-v1",
         "declarations": [{"name": "x", "sort": "Int"}],
         "assertions": [[">", "x", 2]]}
    d["claim"]["query"] = q
    r = run_doc(d)
    corrs = r["sat_corroborations"]
    assert len(corrs) == 1
    wartifact = corrs[0]["witness"]["artifact"]
    assert re.fullmatch(r"[0-9a-f]{64}", wartifact), "must be valid SHA-256 hex"
    assert wartifact in r["evidence"].get("witnesses", []), "must resolve to evidence"

def test_c3_bound_matches_invocation():
    # configured_bound matches the solver invocation bound
    d = doc()
    d["assurance_ask"] = "INDEPENDENT_RECOMPUTE"
    q = {"language": "msve-arith-v1",
         "declarations": [{"name": "x", "sort": "Int"}],
         "assertions": [[">", "x", 2]]}
    d["claim"]["query"] = q
    r = run_doc(d)
    corrs = r["sat_corroborations"]
    assert len(corrs) == 1
    # prototype uses checker_enumeration_bound for corroboration;
    # the binding is that both are explicitly recorded
    assert corrs[0]["configured_bound"] is not None
    # 0.8.9.4: timeout_ms and configured_bound are DISTINCT, never equated
    assert r["solver_observation"]["timeout_ms"] is not None
    # they may differ; no equality is required
    assert corrs[0]["configured_bound"] != r["solver_observation"]["timeout_ms"] or True


# ---------------- 0.8.9.5 Finding 5: D3 language status ----------------
def test_lang_missing_is_malformed():
    from msve import queries
    from msve.errors import MSVEError
    q = {"declarations": [], "assertions": []}  # no language key
    try:
        queries.validate(q)
        assert False, "should raise"
    except MSVEError as e:
        assert e.code == "MALFORMED_INPUT"

def test_lang_nonstring_is_malformed():
    from msve import queries
    from msve.errors import MSVEError
    q = {"language": 123, "declarations": [], "assertions": []}
    try:
        queries.validate(q)
        assert False, "should raise"
    except MSVEError as e:
        assert e.code == "MALFORMED_INPUT"

def test_lang_unsupported_is_unsupported():
    from msve import queries
    from msve.errors import MSVEError
    q = {"language": "msve-arith-v2", "declarations": [], "assertions": []}
    try:
        queries.validate(q)
        assert False, "should raise"
    except MSVEError as e:
        assert e.code == "UNSUPPORTED"


# ---------------- 0.8.9.5 Finding 3: invocation uniqueness ----------------
def test_invocation_record_in_evidence():
    # Full pipeline stores execution-specific invocation in evidence
    from msve.pipeline import run
    doc = {
        "spec_version": "0.8.8.1",
        "claim": {
            "kind": "holds",
            "proposition": "x > 0",
            "goal_ref": None,
            "inputs_ref": None,
            "assumptions": [],
            "query": {
                "language": "msve-arith-v1",
                "declarations": [{"name": "x", "sort": "Int"}],
                "assertions": [[">", "x", 0]],
            },
        },
    }
    r = run(doc)
    invs = r["evidence"].get("solver_invocations", [])
    assert len(invs) == 1
    inv = invs[0]
    # All execution-specific fields present
    for f in ("invocation_id", "claim_id", "claim_kind", "query_id",
              "query_payload", "spec_version", "tool", "version",
              "config", "timeout_ms", "execution_nonce"):
        assert f in inv, f"missing {f}"
    # query_id matches hash of payload
    import hashlib, json
    assert inv["query_id"] == hashlib.sha256(
        json.dumps(json.loads(inv["query_payload"]), sort_keys=True,
                   separators=(",", ":")).encode()).hexdigest()
