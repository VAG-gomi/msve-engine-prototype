"""MSVE-WO-1.3 regression tests.

Finding 2: D2 enforced at the assurance boundary (D1 exception must not
grant SOLVER_BACKED for the seven undefined kinds).
Finding 3: top-level assertions must be Boolean; malformed queries fail
cleanly via MSVE errors, not uncaught Z3 exceptions.
Finding 4: every typed result carries the claim/query-link limitation.
"""
import pytest

from conftest import CFG, doc, holds_query, run_doc
from msve import assurance as asr
from msve.admission import SEVEN_KINDS
from msve.errors import MSVEError
from msve.queries import validate

SEVEN = list(SEVEN_KINDS)
assert len(SEVEN) == 7


def _obs(outcome="UNKNOWN"):
    return {"outcome": outcome, "query_id": "qid", "tool": "z3", "version": "5.1.0"}


@pytest.mark.parametrize("kind", SEVEN)
def test_d2_bars_d1_weak_chain_for_seven_kinds(kind):
    # UNKNOWN + INCONCLUSIVE with valid solver evidence must be refused
    # for every undefined kind — at the award() layer, not just admission.
    with pytest.raises(MSVEError) as e:
        asr.award(kind, "UNKNOWN", "INCONCLUSIVE",
                  {"solver_observation": _obs()}, "cid", "SOLVER_BACKED")
    assert e.value.code == "EVIDENCE_MISSING"


@pytest.mark.parametrize("kind", SEVEN)
def test_outcome_compatible_false_for_seven_kinds_unknown(kind):
    assert asr.outcome_compatible(kind, "UNKNOWN", "INCONCLUSIVE") is False


def test_d1_preserved_for_eligible_kinds():
    for kind in ("holds", "derive", "prove"):
        r = asr.award(kind, "UNKNOWN", "INCONCLUSIVE",
                      {"solver_observation": _obs()}, "cid", "SOLVER_BACKED")
        assert r["basis"] == "SOLVER_BACKED" and r["weak"] is True


def test_integer_top_level_assertion_rejected():
    q = {"language": "msve-arith-v1",
         "declarations": [{"name": "x", "sort": "Int"}],
         "assertions": [["+", "x", 1]]}
    with pytest.raises(MSVEError) as e:
        validate(q)
    assert e.value.code == "MALFORMED_INPUT"


def test_int_typed_name_top_level_rejected():
    q = {"language": "msve-arith-v1",
         "declarations": [{"name": "x", "sort": "Int"}],
         "assertions": ["x"]}
    with pytest.raises(MSVEError) as e:
        validate(q)
    assert e.value.code == "MALFORMED_INPUT"


def test_structurally_invalid_assertion_rejected():
    q = {"language": "msve-arith-v1", "declarations": [],
         "assertions": [["=", 1]]}
    with pytest.raises(MSVEError) as e:
        validate(q)
    assert e.value.code == "MALFORMED_INPUT"


def test_malformed_query_fails_through_pipeline_cleanly():
    d = doc()
    d["claim"]["query"] = {"language": "msve-arith-v1",
                           "declarations": [{"name": "x", "sort": "Int"}],
                           "assertions": [["+", "x", 1]]}
    d["assurance_ask"] = "SOLVER_BACKED"
    with pytest.raises(MSVEError) as e:
        run_doc(d)
    assert e.value.code == "MALFORMED_INPUT"


def test_claim_query_link_unverified_on_every_result():
    d = doc()
    d["claim"]["query"] = holds_query()
    d["assurance_ask"] = "SOLVER_BACKED"
    r = run_doc(d)
    assert r["claim_query_link"] == "UNVERIFIED"
    assert "natural-language" in r["claim_query_link_note"]
    # also on non-accepted verdicts
    d2 = doc()
    d2["assurance_ask"] = "KERNEL_PROOF"
    r2 = run_doc(d2)
    assert r2["claim_query_link"] == "UNVERIFIED"
