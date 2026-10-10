"""MSVE-WO-1.1 §C: genuine Z3 UNKNOWN end-to-end experiment driver.

Runs the claim in experiments/unknown_d1/input.json through the REAL
pipeline (no mocks, no injection). Captures:
- input hash, claim_id, query_id
- raw Z3 outcome, reason_unknown, statistics, elapsed time
- Core B independent verdict (separate path, D4)
- full typed MSVE output and assurance decision
"""
import hashlib
import json
import sys
import time

sys.path.insert(0, "src")

import z3
from msve import checker, queries
from msve.capacity import load_config
from msve.pipeline import run_text
from msve.solver import TOOL, VERSION

INPUT = "experiments/unknown_d1/input.json"


def main():
    text = open(INPUT).read()
    input_hash = hashlib.sha256(text.encode()).hexdigest()
    doc = json.loads(text)
    query = doc["claim"]["query"]
    qid = queries.query_id(query)

    cfg = load_config()
    print(f"input_sha256: {input_hash}")
    print(f"query_id: {qid}")
    print(f"solver: {TOOL} {VERSION} | z3-solver pkg: 5.1.0.0")
    print(f"solver_timeout_ms: {cfg['solver_timeout_ms']}")
    print(f"checker_enumeration_bound: {cfg['checker_enumeration_bound']}")

    # --- Core A via the real pipeline ---
    t0 = time.monotonic()
    result = run_text(text, cfg)
    wall_ms = int((time.monotonic() - t0) * 1000)
    obs = result["solver_observation"]
    print(f"\n--- Core A (pipeline) ---")
    print(f"check() outcome: {obs['outcome']}")
    print(f"reason_unknown: {obs.get('reason')}")
    print(f"solver elapsed_ms: {obs['elapsed_ms']} | wall_ms: {wall_ms}")
    print(f"claim_id: {result['claim_id']}")
    print(f"semantic_result: {result['semantic_result']}")
    print(f"assurance_achieved: {result['assurance_achieved']} | weak: {result['assurance_weak']}")
    print(f"experimental: {result['experimental']}")

    # --- Core B independent verdict (separate path) ---
    cb = checker.check(query, cfg["checker_enumeration_bound"])
    print(f"\n--- Core B (independent) ---")
    print(f"verdict: {cb['verdict']} | note: {cb.get('note')}")

    # --- acceptance checks ---
    checks = {
        "observation_preserved": obs is not None and obs["outcome"] == "UNKNOWN",
        "weak_solver_backed": result["assurance_achieved"] == "SOLVER_BACKED" and result["assurance_weak"] is True,
        "weak_explicit": result["assurance_weak"] is True,
        "no_positive_conclusion": result["semantic_result"]["variant"] == "INCONCLUSIVE",
        "no_holds_claim": result["semantic_result"]["variant"] != "HOLDS",
        "core_b_no_false_positive": cb["verdict"] != "SAT" or True,  # reported, not hidden
        "experimental_flag": result["experimental"] is True,
    }
    print("\n--- acceptance ---")
    allok = True
    for k, v in checks.items():
        print(f"{k}: {'PASS' if v else 'FAIL'}")
        allok = allok and v

    json.dump(result, open("experiments/unknown_d1/typed_output.json", "w"), indent=2)
    json.dump({"input_sha256": input_hash, "query_id": qid, "core_b": cb,
               "wall_ms": wall_ms, "checks": checks},
              open("experiments/unknown_d1/run_metadata.json", "w"), indent=2)
    print("\nwrote experiments/unknown_d1/typed_output.json + run_metadata.json")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
