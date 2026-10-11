# D1–D9 Decision Traceability — MSVE exploratory prototype

Owner rulings recorded 2026-10-10 (MSVE-WO-1.0 §4); integrated into the
archival decision ledger (DEC-008–DEC-016, DEC-025, all ACCEPTED-BY-OWNER).
This map binds each ruling to prototype requirements, implementation
locations, tests, and residual gaps.

| Ruling | Requirement | Implementation | Tests | Residual gap |
|---|---|---|---|---|
| **D1** UNKNOWN+INCONCLUSIVE may qualify for weak SOLVER_BACKED; never proof | `src/msve/assurance.py`: award `SOLVER_BACKED` with `weak:true` only when `outcome=UNKNOWN ∧ sr=INCONCLUSIVE`; the weak flag must propagate to the result and never be presented as a positive conclusion | `assurance.py::award()`; observation bound to claim/query/spec_version (`pipeline.py`) | `test_assurance.py::test_unknown_inconclusive_weak_backed`, `test_unknown_never_proof`; `tests/test_unknown_experiment.py` (genuine Z3 UNKNOWN, WO-1.1); `test_wo19_amendments.py` (A1 block) | Portability of timeout-induced UNKNOWN across Z3 versions/hardware unproven |
| **D2** Preserve recording of the seven kinds; undefined interpretations cannot justify SOLVER_BACKED | `src/msve/admission.py`: accept descriptors for all 10 kinds; `assurance.py`: `outcome_compatible()` returns False for the seven kinds' SOLVER_BACKED claims; observations still recorded per inv 22/23 | `admission.py`, `assurance.py` | `test_assurance.py::test_seven_kinds_recording`, `test_seven_kinds_no_solver_backed` | Per-kind table extension remains future design work |
| **D3** Formal schema + semantics for queries and assumptions before accepting dependent claims | `msve-arith-v1` query DSL: grammar, sorts, denotation into Z3 (`src/msve/queries.py`); assumptions schema: named strings, recorded verbatim, explicitly unverified | `queries.py`, `PROTOTYPE_CONTRACT.md §3–4` | `test_queries.py` (all), `test_pipeline.py::test_assumptions_preserved` | Assumption *verification* is out of scope by design |
| **D4** Checker independence: independently implemented core + disclosed dependencies | Core B (`src/msve/checker.py`): bounded-enumeration evaluator, independent algorithm from Core A (Z3); `DEPENDENCIES.md` discloses shared infra (CPython, DSL parser) | `checker.py`, `DEPENDENCIES.md` | `test_checker.py` (agreement + disagreement cases) | Independence is algorithmic, not hardware/process |
| **D5** Capacity as explicit config with validation + failure behaviour | `config/default.json`; `src/msve/capacity.py` validates ranges; overflow → `CAPACITY_EXCEEDED`; out-of-range → `INVALID_INPUT` (A5 reconciles retired `INVALID_CONFIG`); normative values: `max_verification_records` 10000 (1–1M), `max_descriptors` 1000 (1–100k); precedence explicit > embedded > defaults | `capacity.py`, `config/` | `test_wo19_amendments.py` (A5 block) | None in prototype scope |
| **D6** Structured canonical encoding: boundaries, order, bytes, normalisation, collection order, types | `ENCODING.md` byte-level rules; `src/msve/identity.py`: 4-byte BE length-prefix per field, fixed order kind→proposition→goal_ref→inputs_ref→assumptions→spec_version, UTF-8 NFC, assumptions sorted by bytes, `claim_id=sha256(canonical)` | `identity.py`, `ENCODING.md` | `test_identity.py` (vectors incl. ambiguous-boundary) | Prototype encoding differs from spec's `\|`-joined form (documented) |
| **D7** Freeze gates | Not implemented by the prototype; recorded here as the gate set the prototype's evidence feeds. Prototype results are experimental, never freeze evidence by themselves | — | — | All gates open |
| **D8** Staged engine; experimental evidence only | Every result carries `experimental:true`; `LIMITATIONS.md` states what is not demonstrated | `result.py`, `LIMITATIONS.md` | `test_pipeline.py::test_experimental_flag` | None — by construction |
| **D9** Archival/implementation separation | Prototype lives in `~/workspace/msve-engine/` (separate workspace); every capability links to its archival source below | This file, `PROTOTYPE_CONTRACT.md` | — | — |

## Archival source links

- Normative spec: `candidate/0.8.9.1/MSVE_DESIGN_SPEC_v0.8.9.1.md` (correction candidate, owner review required)
- Formal model: `candidate/0.8.9/audit_model_0889.py` (candidate, owner review required)
- D3 fragment schema: `candidate/0.8.9/D3_SOLVER_FRAGMENT_SCHEMA.md`
- Previous candidate preserved: `candidate/0.8.8.1/` (unmodified)
- Rulings: `decision-ledger/MSVE_BRAINSTORM_DECISION_LEDGER.csv` (DEC-008–DEC-016, DEC-025)
- Status: `PROJECT_STATE.md`; limits: `KNOWN_LIMITATIONS.md`
- Provenance corrections: `PROJECT_STATE.md` provenance notice (2026-10-09)

## Dependency/conflict notes

- D1 refines (does not contradict) the §E.5 outcome table: the table's
  UNKNOWN row is read per ruling D1(B).
- D2 + inv 22/23: recording preserved; justification barred. No conflict.
- D6 prototype encoding vs spec §E.6b `|`-joining: intentionally different;
  the spec form has the documented escaping gap. Prototype-only choice.
