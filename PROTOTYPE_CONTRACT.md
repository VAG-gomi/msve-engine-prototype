# Prototype Contract — MSVE exploratory engine v0.1.0-proto

Experimental prototype under MSVE-WO-1.0. Not a design freeze, not a
baseline, not verified MSVE capability. Every result carries
`experimental:true`.

## 1. Input schema

Top-level JSON object:

```json
{
  "spec_version": "0.8.8.1",
  "claim": {
    "kind": "holds | derive | prove | no_solution | contradiction | unique_under_projection | violated | underdetermined | disproved | artifact_constructed",
    "proposition": "string (canonical claim text)",
    "goal_ref": "string (hash hex or identifier)",
    "inputs_ref": "string (hash hex or identifier)",
    "assumptions": ["string", ...],
    "query": { "language": "msve-arith-v1", "declarations": [...], "assertions": [...] },
    "assurance_required": "LEVEL_A | LEVEL_B | null"
  },
  "evidence": {
    "test_records": [{"test_id": "string", "claim_id": "string", "passed": true}],
    "recompute": {"checker": "string", "agrees": true, "record_ref": "string"},
    "proof_artifact": null
  },
  "config": { "capacity": { ... } }
}
```

`query` is required for kinds `holds`, `derive`, `prove` when solver
evidence is requested; otherwise the claim is processed without solver
observation (recorded as underspecified for solver-backed assurance).

**Input evidence policy:** caller-supplied `evidence.recompute` and
`evidence.test_records` are **never trusted** as assurance evidence. The
pipeline quarantines them transparently (visible in
`quarantined_input_evidence`, never silently dropped) and only a recompute
record generated from the *current* Core B execution — bound to the
claim_id, query_id, checker identity/version and configured bound — can
satisfy `INDEPENDENT_RECOMPUTE`. `TEST_BACKED` cannot be earned at all in
this prototype (no trusted test-execution mechanism). A supplied
`agrees: true` or `passed: true` cannot override a failed corroboration.

## 2. Admission verdicts

- **ACCEPTED** — well-formed, in-scope, within capacity.
- **REJECTED** — malformed JSON, missing/invalid required fields, unknown
  `spec_version`, unknown claim kind, capacity exceeded, undecodable bytes.
- **UNSUPPORTED** — claim kind with undefined solver-outcome interpretation
  *for assurance purposes* (the seven kinds: recording proceeds, but
  SOLVER_BACKED justification is barred); assurance basis with no
  implemented evidence path (KERNEL_PROOF — no kernel exists).
- **UNDERSPECIFIED** — solver-backed assurance requested but no query
  supplied; recompute requested but no recompute record supplied.

## 3. Query language `msve-arith-v1` (D3)

Sorts: `Int`, `Bool`. Declarations bind names to sorts.
Assertions are S-expressions:

```
expr := integer | "true" | "false" | name
      | ["+", expr, expr] | ["-", expr, expr] | ["*", expr, expr]
      | ["=", expr, expr] | ["<", expr, expr] | ["<=", expr, expr]
      | [">", expr, expr] | [">=", expr, expr]
      | ["and", expr+] | ["or", expr+] | ["not", expr]
      | ["ite", expr, expr, expr]
```

Denotation: the conjunction of assertions over the declared signature,
checked for satisfiability by the solver. For kind `holds`, the query
**must** be the negation of the claimed property: `UNSAT` ⇒ the property
holds; `SAT` ⇒ violated, with the solver's model reported as witness.

Query identity: `query_id = sha256` of the canonical JSON encoding
(sorted keys, UTF-8) of the query object.

## 4. Assumptions (D3)

Assumptions are named natural-language strings. The engine records them
verbatim in the descriptor and the result, and reports them in every
typed output. **The engine does not verify assumptions.** Depending on a
claim whose assumptions are false is a user error the engine cannot
detect; this is stated in every result's `assumptions_unverified` field.

## 5. Claim identity (D6)

Byte-level rules (`ENCODING.md`):
1. Strings → NFC-normalized UTF-8 bytes.
2. Fixed field order: kind, proposition, goal_ref, inputs_ref,
   assumptions, spec_version.
3. Each field length-prefixed: 4-byte big-endian length + bytes.
   No separators, no escaping needed.
4. Assumptions: sorted by byte string; encoded as 4-byte BE count +
   length-prefixed elements.
5. `claim_id = sha256(canonical_bytes)` as 64-char lowercase hex.

## 6. Capacity (D5)

Configurable limits (defaults in `config/default.json`):
`max_assumptions` (16), `max_assertions` (64), `max_declarations` (16),
`max_verification_records` (2), `max_descriptors` (2),
`max_invocations` (2), `solver_timeout_ms` (5000).
Exceeding any limit → `REJECTED` with `CAPACITY_EXCEEDED`.
Config values are range-validated at load; invalid config → startup error.

## 7. Supported claim subset

| Kind | Solver role | Defined outcomes |
|---|---|---|
| `holds` | Query = negated property | UNSAT→`HOLDS`; SAT→`VIOLATED`+witness |
| `derive`, `prove` | Diagnostic only | Always `INCONCLUSIVE`; observations recorded, never basis-justifying (except D1 weak rule) |
| Seven kinds | Recording only | Descriptors accepted; observations recorded where inv 22/23 permit; SOLVER_BACKED barred for undefined interpretations |

## 8. Assurance discipline

- `SOLVER_BACKED`: requires linked invocation + observation +
  `outcome_compatible` per the table above. **D1:** `UNKNOWN` +
  `INCONCLUSIVE` may yield `SOLVER_BACKED` with `weak:true`; never a
  proof, never a positive conclusion.
- `TEST_BACKED`: **never awarded in this prototype** (WO-1.4). No
  trusted test-execution mechanism exists, so caller-supplied test records
  — however well-formed — cannot earn it. Supplied `test_records` are
  quarantined transparently. (Same refusal class as `KERNEL_PROOF`.)
- `INDEPENDENT_RECOMPUTE`: requires a Core B agreement record (D4)
  generated from the current execution and bound to claim_id, query_id,
  checker identity/version and configured bound — the expected bound is
  **required** (fail closed; omitting it refuses the basis). Caller-supplied
  `evidence.recompute` is quarantined, never trusted. If Core B does not
  confirm, the disagreement is **recorded** in the typed result's
  `discrepancies` and the basis is withheld — the observation-derived
  semantic is preserved, nothing is raised away.
- **Provenance limit:** field matching establishes *consistency*, not
  provenance. The trusted source of recomputation records is the
  pipeline's controlled checker execution. At the direct `award()`
  boundary, a perfectly consistent fabricated record is indistinguishable
  from a genuine one — the binding checks narrow the forgery surface but
  do not prove origin.
- `KERNEL_PROOF`: never awarded (no kernel in prototype) → UNSUPPORTED.
- Attempting any basis without its evidence → explicit rejection, not a
  silent downgrade.

## 9. Explicit exclusions

All seven kinds' solver-outcome interpretations; KERNEL_PROOF;
assumption verification; query synthesis; non-integer sorts; spec
versions other than `0.8.8.1`; any claim that MSVE is complete.

## 10. Claim/query boundary (D3 limitation — read before trusting output)

The engine solves a **formal query** (`msve-arith-v1`, §3). It does not
establish any correspondence between that query and the claim's
natural-language `proposition`. Concretely:

- **Formally represented and solved:** the denotation of the `query`
  object into Z3 (conjunction of Boolean assertions over declared sorts).
- **Relationship established between claim text and query:** **none.**
  The `proposition` is free text; the engine never parses it, never
  checks it against the query, and never proves the query formalizes it.
  A correct solver verdict on the query does not verify the prose claim.
- **Assumptions:** recorded verbatim as strings; not interpreted, not
  verified, not fed to the solver. Depending on a false assumption is a
  user error the engine cannot detect.
- **What the output claims:** every typed result carries
  `"claim_query_link": "UNVERIFIED"` with an explanatory note. The
  `semantic_result` describes **the query outcome only** (e.g. the
  negation was UNSAT), never "the natural-language proposition is true".

Do not present an MSVE result as verification of a natural-language
mathematical statement. The verified correspondence between prose claim
and formal query is future design work, explicitly out of scope here.
