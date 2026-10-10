"""MSVE-WO-1.4: complete recomputation binding at the award() boundary.

Every contract-required binding field is checked directly: claim ID,
query ID, checker identity, checker version, enumeration bound.
"""
import pytest

from msve import assurance as asr
from msve.checker import CHECKER_ID, CHECKER_VERSION
from msve.errors import MSVEError

BOUND = 5


def _record(**over):
    r = {"checker": CHECKER_ID, "checker_version": CHECKER_VERSION,
         "agrees": True, "claim_id": "cid", "query_id": "qid",
         "bound": BOUND, "record_ref": "core-b:qid"}
    r.update(over)
    return r


def _ev(rec):
    return {"solver_observation": {"outcome": "SAT", "query_id": "qid"}, "recompute": rec}


def test_binding_ok_current_run_record():
    r = asr.award("holds", "SAT", "VIOLATED", _ev(_record()), "cid",
                  "INDEPENDENT_RECOMPUTE", expected_bound=BOUND)
    assert r["basis"] == "INDEPENDENT_RECOMPUTE"


def test_binding_rejects_fabricated_checker_identity():
    with pytest.raises(MSVEError) as e:
        asr.award("holds", "SAT", "VIOLATED", _ev(_record(checker="core-c")),
                  "cid", "INDEPENDENT_RECOMPUTE", expected_bound=BOUND)
    assert "checker identity" in str(e.value)


def test_binding_rejects_wrong_checker_version():
    with pytest.raises(MSVEError) as e:
        asr.award("holds", "SAT", "VIOLATED", _ev(_record(checker_version="9.9")),
                  "cid", "INDEPENDENT_RECOMPUTE", expected_bound=BOUND)
    assert "checker version" in str(e.value)


def test_binding_rejects_mismatched_bound():
    with pytest.raises(MSVEError) as e:
        asr.award("holds", "SAT", "VIOLATED", _ev(_record(bound=99)),
                  "cid", "INDEPENDENT_RECOMPUTE", expected_bound=BOUND)
    assert "enumeration bound" in str(e.value)


def test_binding_rejects_stale_query():
    with pytest.raises(MSVEError) as e:
        asr.award("holds", "SAT", "VIOLATED", _ev(_record(query_id="old-q")),
                  "cid", "INDEPENDENT_RECOMPUTE", expected_bound=BOUND)
    assert "query_id" in str(e.value)


def test_binding_rejects_wrong_claim():
    with pytest.raises(MSVEError) as e:
        asr.award("holds", "SAT", "VIOLATED", _ev(_record(claim_id="other")),
                  "cid", "INDEPENDENT_RECOMPUTE", expected_bound=BOUND)
    assert "claim_id" in str(e.value)
