"""Interface hardening tests (owner finding, 2026-10-10).

Malformed queries must fail as structured MSVE input errors, never as
raw Python exceptions (AttributeError/TypeError) escaping the validation
path.
"""
import pytest

from conftest import doc
from msve.errors import MSVEError
from msve.pipeline import run
from msve.queries import validate


def _run_no_cfg(d):
    return run(d)


@pytest.mark.parametrize("bad_query", ["not-a-dict", ["a", "list"], 42, True])
def test_non_dict_query_rejected_cleanly(bad_query):
    d = doc()
    d["claim"]["query"] = bad_query
    with pytest.raises(MSVEError) as e:
        _run_no_cfg(d)
    assert e.value.code == "MALFORMED_INPUT"
    assert "query must be an object" in str(e.value)


@pytest.mark.parametrize("bad_op", [["+", 1], {"op": "+"}, 42, None])
def test_non_string_operator_rejected_cleanly(bad_op):
    q = {"language": "msve-arith-v1", "declarations": [],
         "assertions": [[bad_op, 1, 2]]}
    with pytest.raises(MSVEError) as e:
        validate(q)
    assert e.value.code == "MALFORMED_INPUT"
    assert "operator must be a string" in str(e.value)


def test_non_string_operator_rejected_through_pipeline():
    d = doc()
    d["claim"]["query"] = {"language": "msve-arith-v1",
                           "declarations": [{"name": "x", "sort": "Int"}],
                           "assertions": [[["+", "x"], 1]]}
    d["assurance_ask"] = "SOLVER_BACKED"
    with pytest.raises(MSVEError) as e:
        _run_no_cfg(d)
    assert e.value.code == "MALFORMED_INPUT"


def test_no_raw_exceptions_escape():
    # belt-and-braces: none of these may raise AttributeError/TypeError
    d = doc()
    for bad in ("s", [1], {"language": "msve-arith-v1", "declarations": "x",
                           "assertions": []}):
        d["claim"]["query"] = bad
        with pytest.raises(MSVEError):
            _run_no_cfg(d)
