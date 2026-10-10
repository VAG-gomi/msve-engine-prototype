# Correction Report — MSVE-WO-1.3

Date: 2026-10-10. Basis: owner source-review of the public prototype
(commit `832978a` page viewed; current HEAD at review time `f0087cd`).

## 0. Publication discrepancy (resolved)

- The owner viewed the commit-specific page for `832978a` (first commit:
  40 files, README "58 tests") and found it inconsistent with the test
  report's WO-1.2 addendum (65 tests).
- Reconciliation: `832978a` was correct *for that commit*. Current HEAD
  was and is `f0087cd2003f52c2fec3b0512b82cde1035e916b` (WO-1.2, 52 files).
  The genuine staleness was the README still saying "58 tests" after the
  WO-1.2 push — fixed (now 89 after this work order).
- Lesson recorded: README test counts must be updated with every suite
  change; the test report's addenda are the authoritative count.

## Finding 1 (P1): independent-recompute evidence bypass — FIXED

- **Source:** `src/msve/pipeline.py` (evidence dict carried caller-supplied
  `recompute` through a failed Core B check), `src/msve/assurance.py`
  (`award()` accepted any `agrees:true` record without provenance check).
- **Fix:**
  - `pipeline.py`: caller-supplied `evidence.recompute` is quarantined on
    all paths — moved to `result["quarantined_input_evidence"]` with reason,
    never silently dropped, never trusted.
  - Trusted records are generated only from the current Core B execution,
    bound to `claim_id`, `query_id`, checker id/version (`core-b`,
    `0.1.0-proto`) and configured bound.
  - `assurance.py` `award()`: defense-in-depth binding check — rejects
    records whose `claim_id`/`query_id` don't match the current execution.
  - `PROTOTYPE_CONTRACT.md` §1 documents the input policy.
- **Regression tests** (`tests/test_evidence_integrity.py`, 4):
  fabricated `agrees:true` + Core B UNKNOWN → discrepancy recorded, basis
  withheld, record quarantined; stale other-query record denied at
  `award()`; valid current-run corroboration still awarded.

## Finding 2: D2 second enforcement point — FIXED

- **Source:** `src/msve/assurance.py` — `outcome_compatible()` checked
  `outcome == "UNKNOWN"` before the seven-kinds exclusion, and `award()`'s
  D1 exception had no kinds guard.
- **Fix:** seven-kinds exclusion moved first in `outcome_compatible()`;
  explicit D2 guard in `award()` before the D1 weak chain (admission
  remains the first layer).
- **Regression tests** (`tests/test_wo13_hardening.py`): all seven kinds ×
  UNKNOWN+INCONCLUSIVE refused at `award()`; `outcome_compatible()` false
  for all seven; D1 preserved for `holds`/`derive`/`prove`.

## Finding 3: Boolean top-level assertions — FIXED

- **Source:** `src/msve/queries.py` `validate()` discarded `_check_expr`
  return types.
- **Fix:** every top-level assertion must type as `Bool`, else
  `MALFORMED_INPUT`. `src/msve/solver.py`: defensive boundary around
  denotation + solver construction → `SOLVER_EXECUTION_FAILED`, never
  disguised as UNKNOWN.
- **Regression tests:** integer-valued, Int-typed-name, and structurally
  invalid assertions rejected via `MALFORMED_INPUT`, including through the
  full pipeline.

## Finding 4: claim/query link (D3) — DOCUMENTED AND LABELLED

- **Status:** a verified prose↔query correspondence is outside this work
  order's safe scope; no semantics invented.
- **Fix:** `PROTOTYPE_CONTRACT.md` §10 defines the exact boundary (what is
  solved, what relationship is *not* established, how assumptions are
  treated). Every typed result now carries `"claim_query_link":
  "UNVERIFIED"` with an explanatory note — the semantic result describes
  the query outcome only.
- **Regression test:** the field is present on accepted and non-accepted
  results.

## Test results

- Full suite: **89 passed, 0 failed** (65 prior + 24 new).
  Log: `logs/test_run_2026-10-10_wo13.log`.
- Environment: Python 3.12.3, z3-solver==5.1.0.0, Z3 5.1.0.
- Observed vs injected: fault-injection tests remain labelled INJECTED in
  `tests/test_fault_injection.py`; all WO-1.3 tests are OBSERVED.

## Scope compliance

- Implementation-repository changes only. Archival spec, model, original
  tests, historical records untouched. D1–D9 preserved (D1 narrowed
  correctly by the D2 guard; D4 strengthened by the binding rule).
- No freeze, release, or baseline approval. All outputs experimental (D8).
