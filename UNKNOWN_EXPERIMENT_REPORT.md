# UNKNOWN Experiment Report — MSVE-WO-1.1

Date: 2026-10-10. Prototype: v0.1.0-proto. Work order: MSVE-WO-1.1.

## Hypothesis

The D1 weak-assurance path (`UNKNOWN` + `INCONCLUSIVE` → weak
`SOLVER_BACKED`) was previously covered only by injected-outcome tests.
Hypothesis: a genuine Z3 `UNKNOWN` returned through the real
engine-to-solver boundary produces the same typed result — `INCONCLUSIVE`,
weak `SOLVER_BACKED`, no positive mathematical conclusion — without
mocking any component.

## Experimental setup

- **Input:** `experiments/unknown_d1/input.json`
  (`sha256: 2bc53b135ad2696b4756a2223071925232da042454fbd851c009555f43447422`)
- **Claim:** kind `prove`, proposition "1000003 is composite (has a
  nontrivial factorization)", `assurance_ask: SOLVER_BACKED`.
- **Query** (`msve-arith-v1`, within the existing contract — no DSL change):
  `x*y = 1000003 ∧ x > 1 ∧ y > 1 ∧ x ≤ y`
  (`query_id: bb97e576…70fa5b`).
- **Why this query:** 1000003 is prime (verified by trial division —
  no factor ≤ √1000003), so the ground truth is UNSAT, but Z3 5.1.0's
  non-linear integer reasoning cannot decide it within any tested timeout
  (2s, 5s, 15s all → UNKNOWN). Small NIA controls (`x²+y²=3`,
  `x³=2`, `x·y=12 ∧ x>3 ∧ y>3`) are all decided UNSAT in <20ms, so the
  UNKNOWN is specific to this hard instance, not a DSL or harness fault.
- **Driver:** `experiments/unknown_d1/run_experiment.py` — calls the real
  `msve.pipeline.run_text` (same entry as the CLI); no mocks, no patching.
- **Environment:** Python 3.12.3, z3-solver==5.1.0.0, Z3 runtime 5.1.0,
  Linux build VM. `solver_timeout_ms: 5000` (default config),
  `checker_enumeration_bound: 5`.

## Raw solver outcome

- `check()` returned **`UNKNOWN`** (actual Z3 result, not injected).
- `reason_unknown()`: **`timeout`** — this UNKNOWN is resource-limit-induced,
  not solver incompleteness. Disclosed as such; see limits.
- Solver elapsed: 5004ms of 5000ms budget; wall time 5009ms.
- No model, no statistics beyond the timeout reason (Z3 yields none on
  timeout for this problem).

## Core A / Core B interaction

- **Core A (Z3):** UNKNOWN as above; observation recorded with tool,
  version, query_id, invocation_id, outcome, elapsed_ms, reason.
- **Core B (independent bounded enumeration):** run separately on the same
  query — verdict **UNKNOWN** ("no satisfying assignment within
  enumeration bound; search incomplete"). It did not manufacture a SAT
  witness and did not claim UNSAT beyond its bound. No discrepancy to
  conceal; both cores report uncertainty through their own documented
  limits.

## Resulting typed output

(`experiments/unknown_d1/typed_output.json`)

- `admission`: ACCEPTED; `claim_id`: `9478cbdd…5ccc60c95a`
- `semantic_result`: `INCONCLUSIVE` ("solver outcome UNKNOWN for kind 'prove'")
- `assurance_achieved`: `SOLVER_BACKED`, **`assurance_weak`: true**,
  note: "D1 weak chain: UNKNOWN+INCONCLUSIVE qualifies for weak
  SOLVER_BACKED; not a proof, not a positive conclusion"
- `experimental`: true; provenance links to archival spec `dbc610c3…`
  and decision-ledger DEC-008 (D1).

## Acceptance verification (WO-1.1 §D)

1. Solver observation + provenance preserved — PASS
2. Weak SOLVER_BACKED taken under D1 — PASS
3. Weakness explicit (`assurance_weak: true` + note) — PASS
4. No proof/HOLDS/positive conclusion — PASS (`INCONCLUSIVE`)
5. Core B did not convert uncertainty into a positive — PASS (UNKNOWN, disclosed)
6. `experimental: true` — PASS
7. No silent success conversion — PASS (all paths return typed verdicts or raise)

## Test results

- Full regression suite: **58 passed, 0 failed** (54 pre-existing +
  4 new in `tests/test_unknown_experiment.py`).
  Log: `logs/test_run_2026-10-10_wo11.log`.
- Experiment driver: 3/3 runs → UNKNOWN/timeout → weak SOLVER_BACKED.

## Reproducibility limits and unresolved issues

- The UNKNOWN depends on Z3 5.1.0 failing to factor 1000003 within the
  timeout. It reproduced 4/4 in this environment (2s/5s/15s timeouts),
  but a faster machine, a different Z3 version, or improved NIA heuristics
  could decide it (correctly: UNSAT). **Portability is not claimed.**
- `reason_unknown() == "timeout"` classifies the cause as resource-limit,
  not logical incompleteness. A solver-incompleteness UNKNOWN (no timeout
  pressure) was not found among the probed QF_NIA instances — small cases
  all decide quickly.
- Core B's bound (5) is far below the factor search space; its UNKNOWN is
  uninformative here beyond "no false positive".
- Ground truth (UNSAT, 1000003 prime) was established by trial division
  *outside* the engine; the engine itself correctly reports INCONCLUSIVE.

## Conclusion

**Demonstrated:** an actual Z3 UNKNOWN, obtained through the unmodified
engine pipeline, reaches the D1 weak-assurance INCONCLUSIVE result with
the weakness explicitly flagged, no positive conclusion drawn, and the
independent checker concurring in uncertainty rather than manufacturing
certainty. The injected-outcome tests and the real-boundary experiment
agree.

**Not demonstrated:** that UNKNOWN outcomes in general are handled
(timeout-induced only); that the D1 path is portable across Z3 versions
or hardware; that any MSVE claim is verified (all outputs remain
experimental evidence per D8).
