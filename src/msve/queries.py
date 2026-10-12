"""D3 query language msve-arith-v1: formal schema, validation, denotation.

Grammar:
  query       := {"language": "msve-arith-v1", "declarations": [decl*], "assertions": [expr+]}
  decl        := {"name": str, "sort": "Int" | "Bool"}
  expr        := int | bool | name
               | ["+", expr, expr] | ["-", expr, expr] | ["*", expr, expr]
               | ["=", expr, expr] | ["<", expr, expr] | ["<=", expr, expr]
               | [">", expr, expr] | [">=", expr, expr]
               | ["and", expr+] | ["or", expr+] | ["not", expr]
               | ["ite", expr, expr, expr]

Denotation: declarations bind names to Z3 sorts; the query denotes the
conjunction of the assertions. For kind "holds" the query must be the
NEGATION of the claimed property (UNSAT => property holds).

query_id = sha256 of canonical JSON (sorted keys, UTF-8, no whitespace).
"""
import hashlib
import json

import z3

from .errors import MSVEError

LANGUAGE = "msve-arith-v1"
SORTS = {"Int": z3.IntSort(), "Bool": z3.BoolSort()}

_BINOP_INT = {"+", "-", "*"}
_BINOP_CMP = {"=", "<", "<=", ">", ">="}


def validate(query):
    if not isinstance(query, dict):
        raise MSVEError("MALFORMED_INPUT", "query must be an object")
    # 0.8.9.5 (Finding 5): distinguish malformed from unsupported language.
    lang = query.get("language")
    if not isinstance(lang, str):
        raise MSVEError("MALFORMED_INPUT", f"language field must be a string, got {type(lang).__name__}")
    if lang != LANGUAGE:
        raise MSVEError("UNSUPPORTED", f"unsupported query language: {lang!r}")
    decls = query.get("declarations", [])
    assertions = query.get("assertions")
    if not isinstance(decls, list):
        raise MSVEError("MALFORMED_INPUT", "declarations must be a list")
    if not isinstance(assertions, list) or not assertions:
        raise MSVEError("MALFORMED_INPUT", "assertions must be a non-empty list")
    sig = {}
    for d in decls:
        if not isinstance(d, dict) or not isinstance(d.get("name"), str) or d.get("sort") not in SORTS:
            raise MSVEError("MALFORMED_INPUT", f"bad declaration: {d!r}")
        if d["name"] in sig:
            raise MSVEError("MALFORMED_INPUT", f"duplicate declaration: {d['name']}")
        if not d["name"] or not d["name"][0].isalpha():
            raise MSVEError("MALFORMED_INPUT", f"bad name: {d['name']!r}")
        sig[d["name"]] = d["sort"]
    for a in assertions:
        t = _check_expr(a, sig)
        if t != "Bool":
            raise MSVEError(
                "MALFORMED_INPUT",
                f"top-level assertion must have Boolean type, got {t}: {_short(a)}",
            )
    return sig


def _short(e):
    s = repr(e)
    return s if len(s) <= 80 else s[:77] + "..."


def _check_expr(e, sig):
    if isinstance(e, bool):
        return "Bool"
    if isinstance(e, int) and not isinstance(e, bool):
        return "Int"
    if isinstance(e, str):
        if e not in sig:
            raise MSVEError("MALFORMED_INPUT", f"unbound name: {e!r}")
        return sig[e]
    if not isinstance(e, list) or not e:
        raise MSVEError("MALFORMED_INPUT", f"bad expression: {_short(e)}")
    op = e[0]
    # operator must be a string: a list/dict/int operator would raise
    # TypeError on the set-membership checks below instead of a clean
    # MSVE input error.
    if not isinstance(op, str):
        raise MSVEError("MALFORMED_INPUT", f"operator must be a string: {_short(op)}")
    args = e[1:]
    if op in _BINOP_INT:
        if len(args) != 2:
            raise MSVEError("MALFORMED_INPUT", f"{op} needs 2 args")
        for a in args:
            if _check_expr(a, sig) != "Int":
                raise MSVEError("MALFORMED_INPUT", f"{op} needs Int args")
        return "Int"
    if op in _BINOP_CMP:
        if len(args) != 2:
            raise MSVEError("MALFORMED_INPUT", f"{op} needs 2 args")
        t = _check_expr(args[0], sig)
        if op == "=":
            if _check_expr(args[1], sig) != t:
                raise MSVEError("MALFORMED_INPUT", "= needs same-sort args")
        elif t != "Int" or _check_expr(args[1], sig) != "Int":
            raise MSVEError("MALFORMED_INPUT", f"{op} needs Int args")
        return "Bool"
    if op in ("and", "or"):
        if not args:
            raise MSVEError("MALFORMED_INPUT", f"{op} needs >=1 args")
        for a in args:
            if _check_expr(a, sig) != "Bool":
                raise MSVEError("MALFORMED_INPUT", f"{op} needs Bool args")
        return "Bool"
    if op == "not":
        if len(args) != 1 or _check_expr(args[0], sig) != "Bool":
            raise MSVEError("MALFORMED_INPUT", "not needs 1 Bool arg")
        return "Bool"
    if op == "ite":
        if len(args) != 3 or _check_expr(args[0], sig) != "Bool":
            raise MSVEError("MALFORMED_INPUT", "ite needs (Bool, T, T)")
        t = _check_expr(args[1], sig)
        if _check_expr(args[2], sig) != t:
            raise MSVEError("MALFORMED_INPUT", "ite branches must agree")
        return t
    raise MSVEError("MALFORMED_INPUT", f"unknown operator: {op!r}")


def denote(query):
    """Validate and denote as (z3_vars, z3_assertions)."""
    sig = validate(query)
    zvars = {}
    for d in query.get("declarations", []):
        zvars[d["name"]] = z3.Const(d["name"], SORTS[d["sort"]])
    return zvars, [_denote(a, zvars) for a in query["assertions"]]


def _denote(e, zvars):
    if isinstance(e, bool):
        return z3.BoolVal(e)
    if isinstance(e, int):
        return z3.IntVal(e)
    if isinstance(e, str):
        return zvars[e]
    op, args = e[0], [ _denote(a, zvars) for a in e[1:]]
    if op == "+":
        return args[0] + args[1]
    if op == "-":
        return args[0] - args[1]
    if op == "*":
        return args[0] * args[1]
    if op == "=":
        return args[0] == args[1]
    if op == "<":
        return args[0] < args[1]
    if op == "<=":
        return args[0] <= args[1]
    if op == ">":
        return args[0] > args[1]
    if op == ">=":
        return args[0] >= args[1]
    if op == "and":
        return z3.And(*args)
    if op == "or":
        return z3.Or(*args)
    if op == "not":
        return z3.Not(args[0])
    if op == "ite":
        return z3.If(args[0], args[1], args[2])
    raise MSVEError("QUERY_DENOTATION_FAILED", f"cannot denote: {op!r}")


def query_id(query):
    canon = json.dumps(query, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canon).hexdigest()
