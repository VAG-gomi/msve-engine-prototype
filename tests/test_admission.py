"""Admission, decode, and capacity tests."""
import pytest

from conftest import CFG, doc, holds_query, run_doc
from msve.capacity import load_config
from msve.errors import MSVEError
from msve.pipeline import run_text


def test_valid_input_accepted():
    d = doc()
    d["claim"]["query"] = holds_query()
    r = run_doc(d)
    assert r["admission"] == "ACCEPTED"
    assert r["experimental"] is True


def test_malformed_json():
    with pytest.raises(MSVEError) as e:
        run_text("{not json", CFG)
    assert e.value.code == "MALFORMED_INPUT"


def test_missing_claim():
    with pytest.raises(MSVEError):
        run_doc({"spec_version": "0.8.8.1"})


def test_missing_required_field():
    d = doc()
    del d["claim"]["proposition"]
    with pytest.raises(MSVEError) as e:
        run_doc(d)
    assert e.value.code == "MALFORMED_INPUT"


def test_unknown_spec_version():
    d = doc()
    d["spec_version"] = "9.9.9"
    with pytest.raises(MSVEError) as e:
        run_doc(d)
    assert e.value.code == "UNKNOWN_SPEC_VERSION"


def test_unknown_claim_kind():
    d = doc()
    d["claim"]["kind"] = "conjecture"
    with pytest.raises(MSVEError):
        run_doc(d)


def test_seven_kinds_recording_only():
    for kind in ("no_solution", "contradiction", "unique_under_projection",
                 "violated", "underdetermined", "disproved", "artifact_constructed"):
        d = doc()
        d["claim"]["kind"] = kind
        r = run_doc(d)
        assert r["admission"] == "ACCEPTED"
        assert r["semantic_result"]["variant"] == "RECORDED_UNINTERPRETED"


def test_kernel_proof_unsupported():
    d = doc()
    d["assurance_ask"] = "KERNEL_PROOF"
    r = run_doc(d)
    assert r["admission"] == "UNSUPPORTED"


def test_solver_backed_underspecified_without_query():
    d = doc()
    d["assurance_ask"] = "SOLVER_BACKED"
    r = run_doc(d)
    assert r["admission"] == "UNDERSPECIFIED"


def test_capacity_exceeded_assumptions():
    d = doc()
    d["claim"]["assumptions"] = [f"a{i}" for i in range(17)]
    with pytest.raises(MSVEError) as e:
        run_doc(d)
    assert e.value.code == "CAPACITY_EXCEEDED"


def test_capacity_exceeded_assertions():
    d = doc()
    q = holds_query()
    q["assertions"] = [["=", 1, 1]] * 65
    d["claim"]["query"] = q
    with pytest.raises(MSVEError) as e:
        run_doc(d)
    assert e.value.code == "CAPACITY_EXCEEDED"


def test_capacity_boundary_exact():
    d = doc()
    d["claim"]["assumptions"] = [f"a{i}" for i in range(16)]
    r = run_doc(d)
    assert r["admission"] == "ACCEPTED"


def test_invalid_config_rejected():
    with pytest.raises(MSVEError) as e:
        load_config(overrides={"max_assumptions": -1})
    assert e.value.code == "INVALID_INPUT"
    with pytest.raises(MSVEError):
        load_config(overrides={"max_assumptions": 999999})


def test_config_override_applied():
    cfg = load_config(overrides={"max_assumptions": 2})
    d = doc()
    d["claim"]["assumptions"] = ["a", "b", "c"]
    with pytest.raises(MSVEError) as e:
        run_doc(d, cfg)
    assert e.value.code == "CAPACITY_EXCEEDED"
