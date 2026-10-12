"""Core A: Z3-backed solver interface with full observation recording."""
import time

import z3

from . import queries
from .errors import MSVEError

TOOL = "z3"
VERSION = z3.get_version_string()


def run(query, timeout_ms, invocation_id, config="default"):
    """Denote the query, run Z3, return an observation record.

    Observation: {tool, version, query_id, invocation_id, outcome,
                  elapsed_ms, config, model (optional), reason (for unknown)}.
    (0.8.9.6: config is recorded as actually applied.)
    outcome in {SAT, UNSAT, UNKNOWN}.
    """
    qid = queries.query_id(query)

    # Defensive boundary: denotation and solver construction failures are
    # reported as SOLVER_EXECUTION_FAILED, never disguised as UNKNOWN.
    # (Malformed input is rejected earlier by queries.validate with
    # MALFORMED_INPUT; this catches unexpected Z3-side failures.)
    try:
        zvars, zasserts = queries.denote(query)
    except MSVEError:
        raise
    except Exception as e:  # pragma: no cover - defensive
        raise MSVEError("QUERY_DENOTATION_FAILED", f"denotation failed: {e}")
    try:
        solver = z3.Solver()
        solver.set("timeout", int(timeout_ms))
        for a in zasserts:
            solver.add(a)
    except Exception as e:
        raise MSVEError("SOLVER_EXECUTION_FAILED", f"solver construction failed: {e}")

    t0 = time.monotonic()
    try:
        res = solver.check()
    except Exception as e:
        raise MSVEError("SOLVER_EXECUTION_FAILED", f"solver raised: {e}")
    elapsed = int((time.monotonic() - t0) * 1000)

    if res == z3.sat:
        outcome = "SAT"
    elif res == z3.unsat:
        outcome = "UNSAT"
    else:
        outcome = "UNKNOWN"

    obs = {
        "tool": TOOL,
        "version": VERSION,
        "query_id": qid,
        "invocation_id": invocation_id,
        "outcome": outcome,
        "elapsed_ms": elapsed,
        "config": config,
    }
    if outcome == "SAT":
        try:
            m = solver.model()
            obs["model"] = {str(d): str(m[d]) for d in m.decls()}
        except Exception:
            obs["model"] = {}
    if outcome == "UNKNOWN":
        obs["reason"] = str(solver.reason_unknown()) if hasattr(solver, "reason_unknown") else "unknown"
    return obs
