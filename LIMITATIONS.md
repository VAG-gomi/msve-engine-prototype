# LIMITATIONS — MSVE exploratory prototype v0.1.0-proto

Experimental prototype under MSVE-WO-1.0. Nothing here is verified MSVE
capability; every result carries `experimental:true`.

## Unsupported semantics

- The seven claim kinds (`no_solution`, `contradiction`,
  `unique_under_projection`, `violated`, `underdetermined`, `disproved`,
  `artifact_constructed`) are **recorded only**. Their solver-outcome
  interpretations are undefined (D2); SOLVER_BACKED is barred for them.
- `KERNEL_PROOF` is never awarded — no proof kernel exists in the prototype.
- Assumptions are **recorded verbatim and never verified**. A claim whose
  assumptions are false will still process; the engine cannot detect this.
- Query language is limited to `msve-arith-v1` (integer/boolean arithmetic,
  no quantifiers, no other sorts).

## Incomplete assurance mechanisms

- `INDEPENDENT_RECOMPUTE`: Core B confirms SAT only, never UNSAT (bounded
  enumeration is incomplete by construction). Solver-UNSAT claims cannot
  earn this basis in the prototype.
- `TEST_BACKED`: trusts caller-supplied test records; the engine does not
  execute them.
- D1 weak chain (`UNKNOWN`+`INCONCLUSIVE` → weak SOLVER_BACKED) is
  implemented and flagged. Genuine Z3 UNKNOWN demonstrated end-to-end in
  MSVE-WO-1.1 (`UNKNOWN_EXPERIMENT_REPORT.md`): timeout-induced UNKNOWN on
  a hard NIA instance, 3/3 reproducible in the declared environment;
  portability across Z3 versions/hardware not claimed.

## Known defects and gaps

- The D6 canonical encoding used here (length-prefixed fields) differs
  intentionally from the spec's `|`-joined form (§E.6b), which has the
  documented escaping gap. Prototype-only choice.
- `goal_ref` / `inputs_ref` are opaque strings in the prototype; the
  archival ArtifactRef binding is not enforced.
- Capacity `max_descriptors`/`max_verification_records` are validated at
  config load but the single-claim pipeline does not yet exercise
  multi-descriptor batches.
- No persistence: results are returned, not stored; no result database.

## Claims not yet demonstrated

- Any mathematical result beyond the tested arithmetic examples.
- Robustness of Z3 UNKNOWN handling against real solver unknowns.
- Performance or scalability characteristics.
- Conformance of the prototype's outcome table to a frozen specification
  (no freeze exists; D7 gates are all open).

## WO-1.2 additions

- Core B corroborates SAT only; INDEPENDENT_RECOMPUTE is structurally
  unavailable for UNSAT/HOLDS claims in this prototype.
- Trust boundary: the awarding logic trusts Core B's agreement signal; a
  compromised checker is not detectable by this engine (demonstrated by
  injected test, disclosed as limitation).
