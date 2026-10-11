"""Schema/implementation alignment tests (owner finding, 2026-10-10).

The contract's input schema must describe what the engine consumes:
- config.capacity overrides are honored (range-validated), not ignored.
- assurance_ask is a validated top-level field driving basis selection;
  claim.assurance_required is recorded-only.
"""
import pytest

from conftest import doc, holds_query
from msve.capacity import load_config
from msve.errors import MSVEError
from msve.pipeline import run


def _run_no_cfg(d):
    return run(d)  # no explicit cfg -> input-embedded config applies


def test_input_config_capacity_honored():
    d = doc()
    d["claim"]["query"] = holds_query()
    d["config"] = {"capacity": {"max_assumptions": 1}}
    d["claim"]["assumptions"] = ["a", "b"]  # exceeds the input-set limit
    with pytest.raises(MSVEError) as e:
        _run_no_cfg(d)
    assert e.value.code == "CAPACITY_EXCEEDED"


def test_input_config_invalid_rejected():
    d = doc()
    d["config"] = {"capacity": {"max_assumptions": 999999}}
    with pytest.raises(MSVEError) as e:
        _run_no_cfg(d)
    assert e.value.code == "INVALID_INPUT"


def test_input_config_not_object_rejected():
    d = doc()
    d["config"] = "nonsense"
    with pytest.raises(MSVEError) as e:
        _run_no_cfg(d)
    assert e.value.code == "MALFORMED_INPUT"


def test_input_config_absent_uses_defaults():
    d = doc()
    d["claim"]["query"] = holds_query()
    r = _run_no_cfg(d)
    assert r["admission"] == "ACCEPTED"


def test_bad_assurance_ask_rejected_at_schema():
    d = doc()
    d["assurance_ask"] = "FROBNICATE"
    with pytest.raises(MSVEError) as e:
        _run_no_cfg(d)
    assert e.value.code == "MALFORMED_INPUT"


def test_assurance_ask_drives_selection():
    d = doc()
    d["claim"]["query"] = holds_query()
    d["assurance_ask"] = "SOLVER_BACKED"
    r = _run_no_cfg(d)
    assert r["assurance_achieved"] == "SOLVER_BACKED"


def test_assurance_required_recorded_not_acted_on():
    # LEVEL_A is recorded and reported; basis selection still uses assurance_ask
    d = doc()
    d["claim"]["assurance_required"] = "LEVEL_A"
    d["claim"]["query"] = holds_query()
    r = _run_no_cfg(d)
    assert r["assurance_required"] == "LEVEL_A"
    assert r["assurance_achieved"] is None  # no ask -> no basis


def test_explicit_cfg_ignores_input_config():
    # Python API: explicit cfg wins; input-embedded config ignored (documented)
    d = doc()
    d["config"] = {"capacity": {"max_assumptions": 1}}
    d["claim"]["assumptions"] = ["a", "b"]
    cfg = load_config()  # defaults: max_assumptions=16
    r = run(d, cfg)
    assert r["admission"] == "ACCEPTED"
