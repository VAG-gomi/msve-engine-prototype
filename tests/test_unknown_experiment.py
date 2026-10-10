"""MSVE-WO-1.1: genuine Z3 UNKNOWN end-to-end (no mocks, no injection).

The query x*y=1000003, x>1, y>1, x<=y is genuinely UNSAT (1000003 is
prime) but Z3 5.1.0 cannot decide it within the timeout -> UNKNOWN with
reason 'timeout'. This exercises the real engine-to-Z3 boundary for D1.

The injected-outcome tests in test_solver.py cover the internal branch;
this test covers the real solver boundary. Both are preserved.
"""
import json
import os

from conftest import CFG
from msve import checker
from msve.capacity import load_config
from msve.pipeline import run

INPUT = os.path.join(os.path.dirname(__file__), "..", "experiments",
                     "unknown_d1", "input.json")

# shorter timeout for suite speed; the problem is undecidable by Z3 well
# beyond this (verified unknown at 15000ms), so 2000ms is safe
FAST_CFG = load_config(overrides={"solver_timeout_ms": 2000})


def _run():
    with open(INPUT) as f:
        doc = json.load(f)
    return run(doc, FAST_CFG), doc


def test_genuine_unknown_through_pipeline():
    r, doc = _run()
    obs = r["solver_observation"]
    assert obs["outcome"] == "UNKNOWN", "experiment requires an actual UNKNOWN"
    assert obs["tool"] == "z3"
    assert r["semantic_result"]["variant"] == "INCONCLUSIVE"


def test_d1_weak_assurance_on_genuine_unknown():
    r, doc = _run()
    assert r["assurance_achieved"] == "SOLVER_BACKED"
    assert r["assurance_weak"] is True
    assert any("not a proof" in n for n in r["assurance_notes"])


def test_no_positive_conclusion_from_unknown():
    r, doc = _run()
    assert r["semantic_result"]["variant"] not in ("HOLDS", "PROVED", "VIOLATED")
    assert r["experimental"] is True


def test_core_b_reports_unknown_separately():
    r, doc = _run()
    cb = checker.check(doc["claim"]["query"], FAST_CFG["checker_enumeration_bound"])
    # core B must not manufacture a positive result from solver uncertainty
    assert cb["verdict"] == "UNKNOWN"
    assert "incomplete" in cb["note"]
