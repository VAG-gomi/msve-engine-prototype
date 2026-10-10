# MSVE exploratory engine prototype v0.1.0-proto

A bounded, runnable vertical slice of the MSVE design (MSVE-WO-1.0),
built from the owner's nine binding rulings D1–D9. **Experimental only:**
every result carries `experimental:true`. This is not a design freeze,
not a baseline, and not verified MSVE capability.

The authoritative design sources live in the separate archival bank
(`https://github.com/VAG-gomi/msve-project`); this workspace holds
executable code, tests, and implementation evidence only (D9).

## Setup

```sh
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Requires Python 3.12. Installs `z3-solver==5.1.0` and `pytest==9.1.1`.

## Usage

```sh
# run a claim through the pipeline
PYTHONPATH=src ./venv/bin/python -m msve.cli examples/example1_input.json

# run the test suite
./venv/bin/python -m pytest tests/ -q
```

Input is a JSON document per `PROTOTYPE_CONTRACT.md` §1. Output is a
typed result: admission verdict, claim identity, semantic result, solver
observation, assurance achieved (only on evidence), and provenance.

## Layout

- `src/msve/` — pipeline: decode, admission, identity (D6), queries (D3),
  solver (Core A), checker (Core B, D4), assurance, capacity (D5), result
- `config/default.json` — capacity limits (D5)
- `tests/` — 96 automated tests (WO-1.0 §6 + WO-1.1 genuine-UNKNOWN + WO-1.2 cross-validation + WO-1.3/WO-1.4/WO-1.5 hardening)
- `experiments/unknown_d1/` — genuine Z3 UNKNOWN end-to-end experiment
  (input, driver, typed output, metadata); report: `UNKNOWN_EXPERIMENT_REPORT.md`
- `vectors/canonical_vectors.json` — golden D6 encoding vectors
- `examples/` — machine-readable example input + typed output
- `PROTOTYPE_CONTRACT.md`, `DECISION_TRACEABILITY.md`, `ENCODING.md`,
  `DEPENDENCIES.md`, `LIMITATIONS.md`, `TEST_REPORT.md`

## Limitations

See `LIMITATIONS.md`. In short: seven claim kinds are recording-only;
no proof kernel; assumptions unverified; Core B confirms SAT only;
results are experimental evidence, not verification.
