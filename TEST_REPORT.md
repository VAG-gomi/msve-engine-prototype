# TEST_REPORT — MSVE exploratory prototype v0.1.0-proto

Date: 2026-10-10. Work order: MSVE-WO-1.0.

## Environment

- Python 3.12.3 (CPython)
- z3-solver==5.1.0.0, Z3 runtime 5.1.0
- pytest==9.1.1
- OS: Linux (build VM)

## Commands

```sh
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python -m pytest tests/ -q          # full suite
PYTHONPATH=src ./venv/bin/python -m msve.cli examples/example1_input.json
```

## Results

- **54 passed, 0 failed** (full log: `logs/test_run_2026-10-10.log`)
- Suite runtime: ~0.1 s

### Coverage against WO-1.0 §6

| Required area | Tests |
|---|---|
| Valid / malformed / missing fields | test_admission.py (7) |
| Supported / unsupported / underspecified kinds | test_admission.py (9 incl. seven-kinds) |
| Query + assumption preservation | test_solver.py (assumptions, schema) |
| Stable identity on repeat input | test_identity.py |
| Ambiguous-boundary vectors | test_identity.py (pipe, comma, unicode, dup) |
| Type handling, collection ordering, capacity | test_identity.py, test_admission.py |
| Capacity exceeded + rejection paths | test_admission.py (4) |
| SAT / UNSAT / UNKNOWN outcomes | test_solver.py |
| D1 weak assurance, no positive conclusion | test_solver.py (2) |
| Unsupported assurance attempts | test_assurance.py (kernel, test-backed, seven-kinds) |
| Checker disagreement | test_assurance.py, test_checker.py |
| Clean-env reproduction | this report (fresh venv procedure above) |

### Failures during development (fixed, disclosed)

1. `derive`/`prove` with SAT/UNSAT wrongly awarded full SOLVER_BACKED —
   fixed in `assurance.py` (diagnostic-only; only D1 weak chain permitted).
2. UNSUPPORTED/UNDERSPECIFIED verdicts raised instead of returning typed
   results — fixed in `pipeline.py` (verdict recorded, nothing awarded).
3. Admission demanded a pre-supplied recompute record for
   INDEPENDENT_RECOMPUTE — fixed (core B generates it; D4).

### Not covered by real execution

- Genuine Z3 UNKNOWN outcomes: covered by injected-outcome tests only
  (timeout-forced UNKNOWN is not deterministic). Recorded in LIMITATIONS.md.

## Reproducibility

Fresh-venv procedure above reproduces 54/54. Golden vectors in
`vectors/canonical_vectors.json` pin the D6 encoding. Example I/O in
`examples/` pins one end-to-end run.

## Addendum 2026-10-10 — MSVE-WO-1.1

- New: `tests/test_unknown_experiment.py` (4 tests) exercising a genuine
  Z3 UNKNOWN through the unmodified pipeline (no mocks). Query:
  `x*y=1000003 ∧ x>1 ∧ y>1 ∧ x≤y` (ground truth UNSAT — 1000003 is prime —
  but Z3 5.1.0 returns UNKNOWN/reason `timeout` at 2s, 5s, and 15s).
- Full suite: **58 passed, 0 failed**.
  Log: `logs/test_run_2026-10-10_wo11.log`.
- Experiment driver `experiments/unknown_d1/run_experiment.py`: 3/3 runs
  → UNKNOWN → INCONCLUSIVE + weak SOLVER_BACKED; Core B UNKNOWN
  (bounded-incomplete), no false positive.
- Full detail: `UNKNOWN_EXPERIMENT_REPORT.md`.

## Addendum 2026-10-10 — MSVE-WO-1.2

- New: `tests/test_fault_injection.py` (3 INJECTED), `tests/test_checker_limits.py`
  (4 OBSERVED). Experiment: `experiments/checker_xval/` (3 inputs, driver,
  per-case typed outputs, `xval_records.json`).
- Design change: checker disagreement now returns a typed result with the
  discrepancy recorded (previously raised CHECKER_DISAGREEMENT); basis
  withheld with explicit note. `PROTOTYPE_CONTRACT.md` §8 updated.
- Full suite: **65 passed, 0 failed**.
  Log: `logs/test_run_2026-10-10_wo12.log`.
- Full detail: `CHECKER_XVAL_REPORT.md`.

## Addendum 2026-10-10 — MSVE-WO-1.3

- New: `tests/test_evidence_integrity.py` (4), `tests/test_wo13_hardening.py` (20).
- Fixes: recompute evidence bypass closed (quarantine + execution binding);
  D2 enforced at assurance boundary; Boolean assertions required;
  claim/query link labelled UNVERIFIED on every result.
- Full suite: **89 passed, 0 failed**.
  Log: `logs/test_run_2026-10-10_wo13.log`.
- Full detail: `CORRECTION_REPORT_WO13.md`.
