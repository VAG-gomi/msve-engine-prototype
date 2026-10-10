"""Core B (D4): independently implemented validation core.

Algorithm (independent of the Z3 path): bounded enumeration. For each
declared Int variable, enumerate values in [-bound, +bound]; for Bool,
both values. Evaluate every assertion under each assignment:
- some assignment satisfies all assertions -> SAT (with witness)
- no assignment satisfies, and the bound was exhaustive for the problem
  class only if flagged complete -> UNSAT_WITHIN_BOUND / UNKNOWN otherwise

Core B never claims UNSAT beyond its bound: if no assignment in the bound
satisfies, the verdict is UNKNOWN (bounded-incomplete), never UNSAT.
This asymmetry is deliberate and documented: Core B can independently
CONFIRM sat (witness) and can REFUTE specific assignments, but its
UNSAT verdicts are bound-qualified.

Shared infrastructure with Core A (disclosed): the msve-arith-v1 parser
and schema validation in queries.py; the CPython interpreter.
"""
import itertools

from . import queries
from .errors import MSVEError

CHECKER_ID = "core-b"
CHECKER_VERSION = "0.1.0-proto"


def _eval(e, env):
    if isinstance(e, bool):
        return e
    if isinstance(e, int):
        return e
    if isinstance(e, str):
        return env[e]
    op, args = e[0], e[1:]
    a = [_eval(x, env) for x in args]
    if op == "+":
        return a[0] + a[1]
    if op == "-":
        return a[0] - a[1]
    if op == "*":
        return a[0] * a[1]
    if op == "=":
        return a[0] == a[1]
    if op == "<":
        return a[0] < a[1]
    if op == "<=":
        return a[0] <= a[1]
    if op == ">":
        return a[0] > a[1]
    if op == ">=":
        return a[0] >= a[1]
    if op == "and":
        return all(a)
    if op == "or":
        return any(a)
    if op == "not":
        return not a[0]
    if op == "ite":
        return a[1] if a[0] else a[2]
    raise MSVEError("QUERY_DENOTATION_FAILED", f"core B cannot evaluate: {op!r}")


def check(query, bound):
    """Return {'verdict': 'SAT'|'UNSAT_BOUNDED'|'UNKNOWN', 'witness'?}.

    SAT: found satisfying assignment within bound (witness included).
    UNKNOWN: no satisfying assignment within bound (incomplete search).
    Core B never returns unqualified UNSAT.
    """
    sig = queries.validate(query)
    decls = query.get("declarations", [])
    assertions = query["assertions"]
    domains = []
    for d in decls:
        if d["sort"] == "Int":
            domains.append((d["name"], list(range(-bound, bound + 1))))
        else:
            domains.append((d["name"], [True, False]))
    names = [n for n, _ in domains]
    for combo in itertools.product(*[v for _, v in domains]):
        env = dict(zip(names, combo))
        try:
            vals = [_eval(a, env) for a in assertions]
        except Exception:
            continue
        if all(v is True for v in vals):
            return {"verdict": "SAT", "witness": {k: v for k, v in env.items()}, "bound": bound}
    return {"verdict": "UNKNOWN", "bound": bound,
            "note": "no satisfying assignment within enumeration bound; search incomplete"}


def agrees_with_solver(query, solver_outcome, bound):
    """Independent agreement check for INDEPENDENT_RECOMPUTE.

    Agreement: core B SAT + solver SAT (witnesses need not match);
    core B cannot confirm UNSAT, so solver UNSAT is NEVER confirmed by
    core B -> returns (False, reason). This is conservative by design.
    """
    res = check(query, bound)
    if res["verdict"] == "SAT" and solver_outcome == "SAT":
        return True, "core B independently found a satisfying assignment"
    return False, (
        f"no independent confirmation (core B: {res['verdict']}, solver: {solver_outcome}); "
        "core B confirms SAT only, never UNSAT"
    )
