# Capacity Parameter Inventory (0.8.9.1, Finding 5)

Each parameter: source, default, valid range, precedence, overflow behaviour.
Precedence for all: explicit per-run config > embedded input config > defaults.
Overflow for all: explicit recorded failure (`CAPACITY_EXCEEDED`); never silent
truncation. Out-of-range configuration: `INVALID_INPUT` (A5).

## Normative A5 parameters (candidate 0.8.9.1 §B.8a)

| Parameter | Default | Range | Meaning |
|---|---|---|---|
| `max_verification_records` | 10,000 | 1–1,000,000 | Max verification records per result |
| `max_descriptors` | 1,000 | 1–100,000 | Max distinct claim descriptors per run |

These two are normative. Their values, ranges, and failure behaviour are
fixed by the approved amendment and must not be changed without a new
owner decision.

## Prototype-specific parameters

| Parameter | Default | Range | Meaning |
|---|---|---|---|
| `max_assumptions` | 16 | 0–1024 | Max assumptions per claim |
| `max_assertions` | 64 | 1–4096 | Max assertions per query |
| `max_declarations` | 16 | 0–256 | Max variable declarations per query |
| `max_invocations` | 2 | 0–16 | Max solver invocations per run |
| `solver_timeout_ms` | 5000 | 1–600000 | Per-invocation solver timeout |
| `checker_enumeration_bound` | 5 | 1–12 | Core B enumeration bound |

These are implementation limits of the experimental prototype, not
normative design parameters. They may be revised in future implementation
work without affecting the normative candidate.

## Disambiguation

- `max_descriptors` (normative) counts distinct **claim descriptors**
  (identities) processed in a run. `max_invocations` (prototype) counts
  **solver invocations** (Z3 runs). A single descriptor may involve zero
  or more invocations; the names refer to different capacities and do
  not conflict.
- No parameter name refers to two different capacities.
