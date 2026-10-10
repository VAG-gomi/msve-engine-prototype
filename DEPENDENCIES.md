# Dependencies — disclosed per D4

## Runtime

- Python 3.12 (CPython). Prototype tested on 3.12.3.
- `z3-solver==5.1.0` (Core A solver backend). Pinned in
  `requirements.txt`.

## Checker independence (D4)

- **Core A** (primary evaluation): Z3-backed satisfiability of the
  `msve-arith-v1` denotation.
- **Core B** (independent checker, `src/msve/checker.py`): bounded
  enumeration over small integer domains + interval evaluation, written
  independently of the Z3 path. It shares the DSL *parser* with Core A
  (one parser, disclosed here) but implements its own decision procedure;
  agreement is computed, not assumed.
- **Shared infrastructure (disclosed):** CPython interpreter, the
  `msve-arith-v1` parser/denotation front-end, the JSON input layer.
  Independence holds at the validation-core level, not below it.

## No other dependencies

Standard library only besides z3-solver. No network access at runtime.
