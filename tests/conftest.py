"""Shared fixtures for the MSVE prototype test suite."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from msve.capacity import load_config  # noqa: E402
from msve.pipeline import run  # noqa: E402

CFG = load_config()


def doc(**kw):
    base = {
        "spec_version": "0.8.8.1",
        "claim": {
            "kind": "holds",
            "proposition": "x+1 > x for x in [0,10]",
            "goal_ref": None,
            "inputs_ref": None,
            "assumptions": [],
        },
    }
    base.update(kw)
    return base


def holds_query(negated=True):
    # negation of "x+1 > x" over [0,10] is "x+1 <= x"
    if negated:
        assertions = [["and", [">=", "x", 0], ["<=", "x", 10],
                       ["<=", ["+", "x", 1], "x"]]]
    else:
        assertions = [[">", ["+", "x", 1], "x"]]
    return {
        "language": "msve-arith-v1",
        "declarations": [{"name": "x", "sort": "Int"}],
        "assertions": assertions,
    }


def run_doc(d, cfg=None):
    return run(d, cfg or CFG)
