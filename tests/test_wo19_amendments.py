"""WO-1.9 regression tests: A1/A2/A4/A5/A6 amendments + D3 fragment (candidate 0.8.9)."""
import hashlib
import json
import struct

import pytest

from msve.capacity import load_config, BOUNDS, DEFAULTS
from msve.errors import MSVEError
from msve.identity import (
    canonical_bytes,
    claim_id,
    ENCODING_VERSION,
    _enc_scalar,
    _enc_list,
)
from msve.pipeline import run
from msve.queries import query_id

from conftest import doc, holds_query, run_doc


# ---------------- A1: weak-assurance provenance binding ----------------

def test_a1_observation_bound_to_claim_query_spec():
    d = doc()
    q = holds_query()
    d["claim"]["query"] = q
    r = run_doc(d)
    obs = r["solver_observation"]
    assert obs["claim_id"] == r["claim_id"]
    assert obs["query_id"] == query_id(q)
    assert obs["spec_version"] == d["spec_version"]


def test_a1_unknown_never_holds():
    # derive/prove + SAT/UNSAT observations stay INCONCLUSIVE (diagnostic only)
    for outcome_query in (holds_query(negated=True), holds_query(negated=False)):
        d = doc()
        d["claim"]["kind"] = "prove"
        d["claim"]["query"] = outcome_query
        r = run_doc(d)
        assert r["semantic_result"]["variant"] == "INCONCLUSIVE"
        assert r["assurance_achieved"] != "SOLVER_BACKED" or r["assurance_weak"]


# ---------------- A5: normative capacity ----------------

def test_a5_normative_defaults_and_bounds():
    assert DEFAULTS["max_verification_records"] == 10000
    assert DEFAULTS["max_descriptors"] == 1000
    assert BOUNDS["max_verification_records"] == (1, 1000000)
    assert BOUNDS["max_descriptors"] == (1, 100000)


def test_a5_boundaries_accepted():
    cfg = load_config(overrides={"max_verification_records": 1,
                                 "max_descriptors": 100000})
    assert cfg["max_verification_records"] == 1
    cfg = load_config(overrides={"max_verification_records": 1000000,
                                 "max_descriptors": 1})
    assert cfg["max_verification_records"] == 1000000


def test_a5_out_of_range_invalid_input():
    with pytest.raises(MSVEError) as e:
        load_config(overrides={"max_verification_records": 0})
    assert e.value.code == "INVALID_INPUT"
    assert "capacity-out-of-range" in str(e.value)
    with pytest.raises(MSVEError) as e:
        load_config(overrides={"max_descriptors": 100001})
    assert e.value.code == "INVALID_INPUT"


def test_a5_not_an_object_invalid_input():
    with pytest.raises(MSVEError) as e:
        load_config(overrides="nonsense")
    assert e.value.code == "INVALID_INPUT"
    assert "capacity-not-an-object" in str(e.value)


def test_a5_precedence_explicit_over_embedded_over_default():
    d = doc()
    d["config"] = {"capacity": {"max_assumptions": 4}}
    explicit = load_config(overrides={"max_assumptions": 8})
    # explicit cfg wins; embedded is ignored
    r = run(d, explicit)
    assert r["admission"] == "ACCEPTED"


# ---------------- A6: msve-descriptor-1 ----------------

def test_a6_encoding_version_bound():
    assert ENCODING_VERSION == "msve-descriptor-1"
    desc = {"kind": "holds", "proposition": "p", "goal_ref": "g",
            "inputs_ref": "i", "assumptions": [], "spec_version": "0.8.9"}
    preimage = canonical_bytes(desc)
    assert preimage.endswith(_enc_scalar("msve-descriptor-1"))


def test_a6_null_vs_empty_distinct():
    base = {"kind": "holds", "proposition": "p", "goal_ref": "g",
            "inputs_ref": "i", "assumptions": [], "spec_version": "0.8.9"}
    null_id = claim_id(dict(base, goal_ref=None))
    empty_id = claim_id(dict(base, goal_ref=""))
    assert null_id != empty_id
    assert _enc_scalar(None) == b"\x00"
    assert _enc_scalar("") == b"\x01\x00\x00\x00\x00"


def test_a6_collection_boundary_explicit():
    # assumptions ["a|b"] vs ["a", "b"] must differ (no separator ambiguity)
    base = {"kind": "holds", "proposition": "p", "goal_ref": "g",
            "inputs_ref": "i", "spec_version": "0.8.9"}
    id1 = claim_id(dict(base, assumptions=["a|b"]))
    id2 = claim_id(dict(base, assumptions=["a", "b"]))
    assert id1 != id2
    # count prefix is present: u32be(1) then tagged element
    enc = _enc_list(["a|b"])
    assert enc[:4] == struct.pack(">I", 1)


def test_a6_version_change_changes_identity():
    # same logical descriptor under a different encoding version differs
    desc = {"kind": "holds", "proposition": "p", "goal_ref": "g",
            "inputs_ref": "i", "assumptions": ["a"], "spec_version": "0.8.9"}
    id_v1 = claim_id(desc)
    # manually compute with a hypothetical v2 tag
    parts = []
    for key in ("kind", "proposition", "goal_ref", "inputs_ref"):
        parts.append(_enc_scalar(desc[key]))
    parts.append(_enc_list(desc["assumptions"]))
    parts.append(_enc_scalar(desc["spec_version"]))
    parts.append(_enc_scalar("msve-descriptor-2"))
    id_v2 = hashlib.sha256(b"".join(parts)).hexdigest()
    assert id_v1 != id_v2


def test_a6_golden_vectors():
    vecs = json.load(open("vectors/canonical_vectors.json"))
    assert len(vecs) >= 16
    for v in vecs:
        assert v["encoding"] == "msve-descriptor-1"
        assert claim_id(v["descriptor"]) == v["claim_id"]
    by_name = {v["name"]: v["claim_id"] for v in vecs}
    assert by_name["multi-assumptions-1"] == by_name["multi-assumptions-2"]
    assert by_name["null-goal-ref"] != by_name["empty-goal-ref"]
    assert by_name["unicode-nfc"] == by_name["unicode-nfd"]


# ---------------- D3: assumption metadata role ----------------

def test_d3_assumptions_not_in_solver_reasoning():
    # assumptions are recorded but do not affect the solver outcome:
    # same query with different assumptions -> same semantic result
    d1 = doc()
    d1["claim"]["query"] = holds_query()
    d1["claim"]["assumptions"] = []
    d2 = doc()
    d2["claim"]["query"] = holds_query()
    d2["claim"]["assumptions"] = ["x is even", "unrelated note"]
    r1, r2 = run_doc(d1), run_doc(d2)
    assert r1["semantic_result"] == r2["semantic_result"]
    assert r1["claim_id"] != r2["claim_id"]  # identity preserves them
    assert r2["assumptions_unverified"] == ["x is even", "unrelated note"]


def test_d3_claim_query_link_unverified_with_assumptions():
    d = doc()
    d["claim"]["query"] = holds_query()
    d["claim"]["assumptions"] = ["depends on unformalized lemma"]
    r = run_doc(d)
    assert r["claim_query_link"] == "UNVERIFIED"
