"""MSVE-WO-1.2: Core B cross-validation experiment driver.

Runs each case in experiments/checker_xval/input_*.json through the
UNMODIFIED pipeline, recording Core A's Z3 result and Core B's independent
verdict separately. Disagreements are caught and recorded, not hidden.
"""
import glob
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, "src")

from msve import checker, queries
from msve.capacity import load_config
from msve.errors import MSVEError
from msve.pipeline import run
from msve.solver import VERSION as Z3_VERSION

HERE = os.path.dirname(os.path.abspath(__file__))


def run_case(path, cfg, ask_override=None):
    text = open(path).read()
    doc = json.loads(text)
    if ask_override is not None:
        doc["assurance_ask"] = ask_override
    query = doc["claim"]["query"]
    rec = {
        "input": os.path.basename(path),
        "input_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "query_id": queries.query_id(query),
        "assurance_ask": doc.get("assurance_ask"),
    }
    # Core B independent verdict (separate path, always recorded)
    t0 = time.monotonic()
    rec["core_b"] = checker.check(query, cfg["checker_enumeration_bound"])
    rec["core_b_ms"] = int((time.monotonic() - t0) * 1000)
    # Core A via the real pipeline
    t0 = time.monotonic()
    try:
        result = run(doc, cfg)
        rec["pipeline_ok"] = True
        rec["claim_id"] = result["claim_id"]
        obs = result["solver_observation"] or {}
        rec["core_a_outcome"] = obs.get("outcome")
        rec["core_a_reason"] = obs.get("reason")
        rec["core_a_ms"] = obs.get("elapsed_ms")
        rec["semantic"] = result["semantic_result"]["variant"]
        rec["assurance_achieved"] = result["assurance_achieved"]
        rec["assurance_weak"] = result["assurance_weak"]
        rec["discrepancies"] = result["discrepancies"]
        rec["experimental"] = result["experimental"]
        json.dump(result, open(path.replace("input_", "output_").replace(".json", "_typed.json"), "w"), indent=2)
    except MSVEError as e:
        rec["pipeline_ok"] = False
        rec["pipeline_error"] = {"code": e.code, "message": str(e)}
    rec["wall_ms"] = int((time.monotonic() - t0) * 1000)
    return rec


def main():
    cfg = load_config()
    print(f"z3: {Z3_VERSION} | timeout_ms={cfg['solver_timeout_ms']} | core_b_bound={cfg['checker_enumeration_bound']}")
    records = []
    for path in sorted(glob.glob(os.path.join(HERE, "input_*.json"))):
        rec = run_case(path, cfg)
        records.append(rec)
        # extra probe: INDEPENDENT_RECOMPUTE on the holds_unsat case documents withholding
        if "holds_unsat" in path:
            rec2 = run_case(path, cfg, ask_override="INDEPENDENT_RECOMPUTE")
            rec2["input"] += " [ask=INDEPENDENT_RECOMPUTE probe]"
            records.append(rec2)
    for r in records:
        print(f"\n=== {r['input']} ===")
        print(f"  ask={r['assurance_ask']} | core_a={r.get('core_a_outcome')} "
              f"| core_b={r['core_b']['verdict']} | semantic={r.get('semantic')}")
        print(f"  assurance={r.get('assurance_achieved')} weak={r.get('assurance_weak')}")
        if not r["pipeline_ok"]:
            print(f"  PIPELINE RAISED: {r['pipeline_error']}")
        if r.get("discrepancies"):
            print(f"  discrepancies: {r['discrepancies']}")
    json.dump(records, open(os.path.join(HERE, "xval_records.json"), "w"), indent=2)
    print("\nwrote xval_records.json + per-case typed outputs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
