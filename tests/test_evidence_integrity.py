"""MSVE-WO-1.3 regression tests: assurance-evidence integrity hardening.

Finding 1 (P1): caller-supplied evidence.recompute must not bypass a
failed Core B corroboration.
"""
import pytest

from conftest import CFG, doc, holds_query, run_doc
from msve import assurance as asr
from msve.errors import MSVEError


def _fabricated_recompute(claim_id="forged", query_id="forged"):
    return {"checker": "core-b", "agrees": True, "claim_id": claim_id,
            "query_id": query_id, "record_ref": "forged-record"}


def test_fabricated_recompute_cannot_override_failed_checker():
    # UNSAT query -> Core B UNKNOWN (cannot confirm) + fabricated agrees:true
    # Expected: discrepancy recorded, basis withheld, record quarantined.
    d = doc()
    d["claim"]["query"] = holds_query(negated=True)  # UNSAT
    d["assurance_ask"] = "INDEPENDENT_RECOMPUTE"
    d["evidence"] = {"recompute": _fabricated_recompute()}
    r = run_doc(d)
    assert r["assurance_achieved"] is None
    assert any(x["checker"] == "core-b" for x in r["discrepancies"])
    q = r["quarantined_input_evidence"]
    assert len(q) == 1 and q[0]["field"] == "evidence.recompute"
    assert q[0]["record"]["record_ref"] == "forged-record"


def test_fabricated_recompute_quarantined_even_without_ask():
    d = doc()
    d["evidence"] = {"recompute": _fabricated_recompute()}
    r = run_doc(d)
    assert len(r["quarantined_input_evidence"]) == 1
    assert r["assurance_achieved"] is None


def test_stale_recompute_for_other_query_denied():
    # defense in depth: award() itself rejects records not bound to the
    # current claim/query execution, even if one reached it directly.
    obs = {"outcome": "SAT", "query_id": "real-qid"}
    with pytest.raises(MSVEError) as e:
        asr.award("holds", "SAT", "VIOLATED",
                  {"solver_observation": obs,
                   "recompute": _fabricated_recompute("other-claim", "other-q")},
                  "real-claim", "INDEPENDENT_RECOMPUTE")
    assert e.value.code == "EVIDENCE_MISSING"


def test_valid_current_run_corroboration_still_works():
    d = doc()
    d["claim"]["query"] = {
        "language": "msve-arith-v1",
        "declarations": [{"name": "x", "sort": "Int"}],
        "assertions": [[">", "x", 0]],
    }
    d["assurance_ask"] = "INDEPENDENT_RECOMPUTE"
    r = run_doc(d)
    assert r["assurance_achieved"] == "INDEPENDENT_RECOMPUTE"
    assert r["quarantined_input_evidence"] == []
