# Correction Report — MSVE-WO-1.4

Date: 2026-10-10. Basis: owner source-review of WO-1.3.

## 0. Public branch reconciliation (done first)

- Remote `main` HEAD: `1f0bfd2c15c16f1bec256377944e39a538d4e6e3` — verified
  via `git ls-remote` before any change; local matched.
- The raw README served by GitHub already reported 89 tests. The owner's
  "58 tests" view was a stale cached/rendered page, not a behind branch.
  No branch discrepancy existed. README count updated to 94 with this
  work order.

## 1. TEST_BACKED hardened — REFUSED (P1)

- **Source:** `src/msve/assurance.py` (`TEST_BACKED` awarded on
  caller-supplied `passed:true` + matching `claim_id`);
  `src/msve/pipeline.py` (no quarantine for `test_records`).
- **Policy decision:** no trusted test-execution mechanism exists in this
  prototype, so per the work order ("refuse TEST_BACKED rather than
  inventing one"), the basis is refused outright — same class as
  `KERNEL_PROOF`. An attestation-flag alternative was considered and
  rejected: it would still let fabricated-but-complete records earn a
  basis.
- **Changes:**
  - `admission.py`: `TEST_BACKED` → `UNSUPPORTED` (was `UNDERSPECIFIED`
    without records).
  - `assurance.py`: `TEST_BACKED` → `UNSUPPORTED_BASIS` at the direct
    boundary too (defense in depth).
  - `pipeline.py`: caller-supplied `test_records` quarantined visibly
    alongside `recompute` (uniform input-evidence policy).
  - `PROTOTYPE_CONTRACT.md` §1, §8 document the refusal and policy.
- **Regression tests** (`tests/test_assurance.py`): well-formed passing
  record → UNSUPPORTED + quarantined; fabricated record → UNSUPPORTED;
  direct `award()` → `UNSUPPORTED_BASIS`.

## 2. Recomputation binding completed at award()

- **Source:** `award()` checked only `claim_id`/`query_id`; the report
  claimed more.
- **Changes** (`src/msve/assurance.py`): `award()` now verifies all five
  contract fields — claim ID, query ID, checker identity, checker
  version, enumeration bound — against the current execution
  (`expected_bound` passed by the pipeline from config;
  `CHECKER_ID`/`CHECKER_VERSION` imported from `checker.py`).
  Mismatches name the failing fields.
- **Regression tests** (`tests/test_binding.py`, 6): fabricated checker
  identity, wrong version, mismatched bound, stale query_id, wrong
  claim_id all denied; genuine current-run record awarded.

## Test results

- Full suite: **94 passed, 0 failed** (89 prior − 4 superseded
  TEST_BACKED tests + 3 refusal tests + 6 binding tests).
  Log: `logs/test_run_2026-10-10_wo14.log`.
- Environment: Python 3.12.3, z3-solver==5.1.0.0, Z3 5.1.0.

## Scope compliance

- Implementation repository only. Archival spec/model/tests/history
  untouched. D1–D9 intact (D4 strengthened; no ruling narrowed).
- No freeze, release, or baseline. All outputs experimental (D8).
