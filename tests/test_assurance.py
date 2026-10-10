"""Assurance discipline tests: bases awarded only on evidence."""
import pytest

from conftest import CFG, doc, holds_query, run_doc
from msve.errors import MSVEError


def test_no_basis_by_default():
    d = doc()
    r = run_doc(d)
    assert r["assurance_achieved"] is None


def test_test_backed_refused_no_mechanism():
    # WO-1.4: even a well-formed passing record cannot earn TEST_BACKED —
    # no trusted test-execution mechanism exists in this prototype.
    d = doc()
    d["claim"]["query"] = holds_query()
    r0 = run_doc(d)
    cid = r0["claim_id"]
    d["evidence"] = {"test_records": [
        {"test_id": "t1", "claim_id": cid, "passed": True,
         "spec_version": "0.8.8.1", "test_run_ref": "run-1",
         "runner": "external"}]}
    d["assurance_ask"] = "TEST_BACKED"
    r = run_doc(d)
    assert r["admission"] == "UNSUPPORTED"
    assert r["assurance_achieved"] is None
    # the supplied records are quarantined visibly, not silently dropped
    assert len(r["quarantined_input_evidence"]) == 1
    assert r["quarantined_input_evidence"][0]["field"] == "evidence.test_records"


def test_test_backed_fabricated_record_refused():
    d = doc()
    d["evidence"] = {"test_records": [{"test_id": "t1", "claim_id": "x", "passed": True}]}
    d["assurance_ask"] = "TEST_BACKED"
    r = run_doc(d)
    assert r["admission"] == "UNSUPPORTED"
    assert r["assurance_achieved"] is None


def test_test_backed_unsupported_at_award_boundary():
    # defense in depth: direct award() also refuses
    from msve import assurance as asr
    with pytest.raises(MSVEError) as e:
        asr.award("holds", "UNSAT", "HOLDS",
                  {"test_records": [{"test_id": "t1", "claim_id": "c",
                                     "passed": True, "spec_version": "0.8.8.1",
                                     "test_run_ref": "r", "runner": "ext"}]},
                  "c", "TEST_BACKED")
    assert e.value.code == "UNSUPPORTED_BASIS"


def test_seven_kinds_no_solver_backed():
    from msve import assurance as asr
    for kind in ("contradiction", "unique_under_projection", "no_solution"):
        with pytest.raises(MSVEError) as e:
            asr.award(kind, "UNSAT", "RECORDED_UNINTERPRETED", {}, "cid", "SOLVER_BACKED")
        assert e.value.code == "EVIDENCE_MISSING"


def test_independent_recompute_agreement():
    d = doc()
    # SAT query small enough for core B to confirm: x=1 satisfies x>0
    d["claim"]["query"] = {
        "language": "msve-arith-v1",
        "declarations": [{"name": "x", "sort": "Int"}],
        "assertions": [[">", "x", 0]],
    }
    d["assurance_ask"] = "INDEPENDENT_RECOMPUTE"
    r = run_doc(d)
    assert r["assurance_achieved"] == "INDEPENDENT_RECOMPUTE"
    assert r["discrepancies"] == []


def test_independent_recompute_disagreement_recorded():
    # solver UNSAT can never be confirmed by core B -> disagreement is
    # RECORDED in the typed result and the basis is withheld (not raised away)
    d = doc()
    d["claim"]["query"] = holds_query(negated=True)  # UNSAT
    d["assurance_ask"] = "INDEPENDENT_RECOMPUTE"
    r = run_doc(d)
    assert r["assurance_achieved"] is None
    assert len(r["discrepancies"]) == 1
    assert r["discrepancies"][0]["checker"] == "core-b"
    assert any("withheld" in n for n in r["assurance_notes"])


def test_kernel_proof_never_awarded():
    from msve import assurance as asr
    with pytest.raises(MSVEError) as e:
        asr.award("holds", "UNSAT", "HOLDS", {}, "cid", "KERNEL_PROOF")
    assert e.value.code == "UNSUPPORTED_BASIS"


def test_experimental_flag_always():
    d = doc()
    d["claim"]["query"] = holds_query()
    d["assurance_ask"] = "SOLVER_BACKED"
    r = run_doc(d)
    assert r["experimental"] is True
    assert r["provenance"]["spec_sha256"].startswith("dbc610c3")
