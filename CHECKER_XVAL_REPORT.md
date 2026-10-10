# Checker Cross-Validation Report — MSVE-WO-1.2

Date: 2026-10-10. Prototype: v0.1.0-proto. Environment: Python 3.12.3,
z3-solver==5.1.0.0, Z3 5.1.0, `solver_timeout_ms=5000`, `core_b_bound=5`.

## Question

Can the independently implemented Core B corroborate decisive Core A
results, and does disagreement withhold unjustified assurance without
manufacturing conclusions?

## Cases (all OBSERVED through the unmodified pipeline)

Inputs in `experiments/checker_xval/input_*.json`; per-case typed outputs
and `xval_records.json` preserved alongside.

| Case | Claim | Core A (Z3) | Core B (indep.) | Semantic | Assurance |
|---|---|---|---|---|---|
| holds_unsat | "∀x∈[0,5], x²≥x" (true) | UNSAT | UNKNOWN (cannot confirm UNSAT by design) | HOLDS | SOLVER_BACKED (asked) |
| holds_unsat + INDEPENDENT_RECOMPUTE probe | same | UNSAT | UNKNOWN | HOLDS | **withheld** — discrepancy recorded |
| violated_sat | "∀x∈[0,5], x+1>x+2" (false) | SAT, witness x=0 | SAT, witness x=0 (independently found) | VIOLATED + witness | **INDEPENDENT_RECOMPUTE awarded** |
| boundary_sat | "∃x: 50<x<200" | SAT, witness x=100 | UNKNOWN (witness outside bound) | VIOLATED | **withheld** — discrepancy recorded |

Scope account: Core B corroborates **SAT only** (it produces its own
witness by enumeration). It can never confirm UNSAT — its verdicts are
`SAT` or `UNKNOWN`, never bare `UNSAT` (pinned by tests). Agreement for
the VIOLATED case is genuine corroboration: two different algorithms
(Z3's solver vs bounded enumeration) independently found satisfying
assignments.

## Disagreement handling (design change during this work order)

On Core A/Core B disagreement the pipeline previously *raised*
`CHECKER_DISAGREEMENT`, losing the record. It now returns a typed result:
the observation-derived semantic is preserved, the disagreement is in
`discrepancies`, and the basis is withheld with an explicit note. This
matches MSVE's preserve-failures discipline. (`src/msve/pipeline.py`;
contract §8 updated.)

## Fault injection (label: INJECTED, `tests/test_fault_injection.py`)

1. **Core A lies** (reports SAT for a genuinely UNSAT query): Core B
   honestly UNKNOWN → discrepancy recorded, assurance withheld. The
   pipeline cannot see through Core A's lie about the *observation*
   (documented below) — but it does not award the asked basis.
2. **Core B falsely reports SAT** for an UNSAT query: SAT-vs-UNSAT
   mismatch → no agreement → discrepancy recorded, basis withheld.
3. **Core B lies about agreement** (returns True falsely): the basis IS
   awarded. **Trust boundary disclosed:** the awarding logic trusts Core
   B's agreement signal; a compromised checker is not detectable by this
   engine. Defense in depth (third checker, out-of-process verification)
   is future work.

## Bounded-checker limitations (label: OBSERVED, `tests/test_checker_limits.py`)

- Insufficient bound → UNKNOWN with "incomplete" note, never a
  universality claim. Pinned across a query battery: no bare UNSAT verdict.
- A SAT verdict always carries a checkable witness.
- Raising the bound finds witnesses Core B missed at bound 5 (x=100 found
  at bound 100) — the bound is a scope parameter, not a correctness claim.

## Shared-dependency analysis (D4)

| Layer | Core A | Core B | Shared? |
|---|---|---|---|
| Decision procedure | Z3 SMT solver | Bounded enumeration (`itertools.product`) | **No** — verified: 0 z3 references in `checker.py` |
| Query parser/validator | `queries.py` | `queries.py` | **Yes** (disclosed) |
| Runtime | CPython 3.12 | CPython 3.12 | **Yes** (disclosed) |
| Input layer | JSON decode | JSON decode | **Yes** (disclosed) |

Independence holds at the validation-core level, not below it — exactly
the D4 ruling ("shared infrastructure allowed, independently implemented
validation core, explicitly disclosed dependencies").

## Test results

- Full suite: **65 passed, 0 failed** (`logs/test_run_2026-10-10_wo12.log`).
- New: `test_checker_xval` behavior via experiment driver (4 cases),
  `test_fault_injection.py` (3 INJECTED), `test_checker_limits.py`
  (4 OBSERVED).

## Failures and unresolved limitations

- None of the observed cases failed. The trust-boundary finding (injected
  test 3) is a disclosed limitation, not a failure.
- Core B cannot corroborate UNSAT/HOLDS results — INDEPENDENT_RECOMPUTE
  is structurally limited to SAT-shaped claims in this prototype.
- Agreement on one VIOLATED case does not establish general checker
  independence or engine correctness.

## Conclusion

**Demonstrated:** Core B genuinely corroborates a decisive Core A SAT
result through an independent algorithm; disagreements (UNSAT
unconfirmable, witness outside bound, injected lies) are detected,
recorded in the typed result, and never converted into awarded assurance
or manufactured conclusions; bounded search is never promoted to
universal proof.

**Not demonstrated:** general checker independence, engine correctness,
or robustness beyond the tested cases. All results remain experimental
per D8. No freeze, release, or baseline approval follows from this work.
