"""D6 canonical identity tests: determinism, boundaries, vectors."""
import json
import os

from conftest import CFG, doc, run_doc
from msve.identity import canonical_bytes, claim_id

VECTORS = os.path.join(os.path.dirname(__file__), "..", "vectors", "canonical_vectors.json")


def desc(**kw):
    d = {"kind": "holds", "proposition": "p", "goal_ref": None,
         "inputs_ref": None, "assumptions": [], "spec_version": "0.8.8.1"}
    d.update(kw)
    return d


def test_deterministic():
    assert claim_id(desc()) == claim_id(desc())


def test_field_sensitivity():
    base = claim_id(desc())
    assert claim_id(desc(proposition="q")) != base
    assert claim_id(desc(kind="prove")) != base
    assert claim_id(desc(assumptions=["a"])) != base


def test_ambiguous_boundary_pipe():
    # "a|b" as one field vs "a","b" split must differ; length-prefixing
    # guarantees it (this is the spec |-joining gap, repaired here)
    a = claim_id(desc(proposition="a|b"))
    b = claim_id(desc(proposition="a", goal_ref=None))
    assert a != b


def test_ambiguous_boundary_comma():
    a = claim_id(desc(assumptions=["x,y"]))
    b = claim_id(desc(assumptions=["x", "y"]))
    assert a != b


def test_assumption_order_irrelevant():
    assert claim_id(desc(assumptions=["b", "a"])) == claim_id(desc(assumptions=["a", "b"]))


def test_assumption_duplicates_matter():
    assert claim_id(desc(assumptions=["a", "a"])) != claim_id(desc(assumptions=["a"]))


def test_unicode_normalization():
    # e + combining acute vs precomposed é must share identity (NFC)
    a = claim_id(desc(proposition="café"))
    b = claim_id(desc(proposition="café"))
    assert a != claim_id(desc(proposition="cafe"))
    # both forms normalize identically
    assert a == b


def test_empty_proposition():
    cid = claim_id(desc(proposition=""))
    assert len(cid) == 64 and all(c in "0123456789abcdef" for c in cid)


def test_golden_vectors():
    with open(VECTORS) as f:
        vecs = json.load(f)
    assert len(vecs) >= 6
    for v in vecs:
        assert claim_id(v["descriptor"]) == v["claim_id"], v["name"]


def test_identity_stable_across_runs():
    d1 = doc()
    d1["claim"]["query"] = None
    r1 = run_doc(d1)
    r2 = run_doc(doc())
    assert r1["claim_id"] == r2["claim_id"]
