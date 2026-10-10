# Correction Report — MSVE-WO-1.5

Date: 2026-10-10. HEAD inspected before changes: `710fe07` (clean, remote
matched).

## Finding: fail-open bound validation — FIXED

- **Source:** `src/msve/assurance.py` `award()` — the enumeration-bound
  check was guarded by `if expected_bound is not None`, so omitting
  `expected_bound` skipped bound validation entirely and the basis could
  be granted without it.
- **Fix:** `expected_bound` is now required for `INDEPENDENT_RECOMPUTE`.
  Omitting it raises `EVIDENCE_MISSING` explicitly ("requires an expected
  enumeration bound; refusing without one"). The record's `bound` is
  always compared; missing and mismatched values are both rejected with
  the field named.
- **Existing checks preserved:** claim ID, query ID, checker identity,
  checker version — unchanged. Caller-supplied recompute records remain
  quarantined in the normal pipeline.

## Provenance limitation (documented, not claimed away)

Field matching establishes *consistency*, not provenance. The trusted
source of recomputation records is the pipeline's controlled checker
execution (which quarantines caller input and regenerates the record).
At the direct `award()` boundary, a perfectly consistent fabricated
record is indistinguishable from a genuine one — the binding checks
narrow the forgery surface but do not prove origin. Documented in
`PROTOTYPE_CONTRACT.md` §8 and in the `award()` code comment.

## Regression tests

- `tests/test_binding.py` (+2): `test_expected_bound_omitted_fails_closed`,
  `test_record_bound_omitted_rejected`. Existing: incorrect bound,
  fabricated identity/version, stale query, wrong claim, valid record.
- Pipeline-level: valid current-run recomputation still awarded
  (`test_independent_recompute_agreement`); failed corroboration still
  recorded + withheld (`test_independent_recompute_disagreement_recorded`).

## Test results

- Full suite: **96 passed, 0 failed** (94 prior + 2 new).
  Log: `logs/test_run_2026-10-10_wo15.log`.
- Environment: Python 3.12.3, z3-solver==5.1.0.0, Z3 5.1.0.

## Scope compliance

- Implementation repository only. Archival spec/model/tests/history
  untouched. D1–D9 intact. No freeze, release, or baseline. All outputs
  experimental (D8).
