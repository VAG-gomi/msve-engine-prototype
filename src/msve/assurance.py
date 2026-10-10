"""Assurance discipline: bases are awarded only on evidence, never by default.

outcome_compatible(kind, outcome, semantic_variant):
  holds  : (UNSAT, HOLDS) | (SAT, VIOLATED)
  derive/prove: (any, INCONCLUSIVE) — solver diagnostic only
  UNKNOWN: (UNKNOWN, INCONCLUSIVE) — never a positive conclusion
  seven kinds: no defined compatibility (D2)

award(kind, outcome, semantic_variant, evidence, claim_id):
  returns (basis, weak, notes) or raises EVIDENCE_MISSING / UNSUPPORTED_BASIS.

D1: UNKNOWN + INCONCLUSIVE may yield SOLVER_BACKED with weak=True.
    weak is propagated and must never be presented as proof.
"""
from .admission import SEVEN_KINDS
from .errors import MSVEError


def outcome_compatible(kind, outcome, semantic_variant):
    if kind == "holds":
        return (outcome == "UNSAT" and semantic_variant == "HOLDS") or (
            outcome == "SAT" and semantic_variant == "VIOLATED"
        )
    if kind in ("derive", "prove"):
        return semantic_variant == "INCONCLUSIVE"
    if outcome == "UNKNOWN":
        return semantic_variant == "INCONCLUSIVE"
    if kind in SEVEN_KINDS:
        return False  # D2: undefined interpretations cannot justify SOLVER_BACKED
    return False


def semantic_for(kind, outcome):
    """Determine the semantic result variant from kind + solver outcome."""
    if kind == "holds":
        if outcome == "UNSAT":
            return "HOLDS"
        if outcome == "SAT":
            return "VIOLATED"
        return "INCONCLUSIVE"  # UNKNOWN or anything else
    if kind in ("derive", "prove"):
        return "INCONCLUSIVE"
    # seven kinds: recorded without interpretation
    return "RECORDED_UNINTERPRETED"


def award(kind, outcome, semantic_variant, evidence, claim_id, basis_ask):
    """Decide the achieved assurance basis. Returns dict or raises."""
    evidence = evidence or {}
    notes = []

    if basis_ask is None:
        return {"basis": None, "weak": False, "notes": ["no basis requested"]}

    if basis_ask == "KERNEL_PROOF":
        raise MSVEError(
            "UNSUPPORTED_BASIS",
            "KERNEL_PROOF has no implemented evidence path in this prototype",
        )

    if basis_ask == "SOLVER_BACKED":
        obs = evidence.get("solver_observation")
        if not obs:
            raise MSVEError("EVIDENCE_MISSING", "SOLVER_BACKED requires a linked solver observation")
        if obs.get("outcome") != outcome:
            raise MSVEError("EVIDENCE_MISSING", "observation outcome does not match executed outcome")
        # D1 weak chain
        if outcome == "UNKNOWN" and semantic_variant == "INCONCLUSIVE":
            notes.append(
                "D1 weak chain: UNKNOWN+INCONCLUSIVE qualifies for weak SOLVER_BACKED; "
                "not a proof, not a positive conclusion"
            )
            return {"basis": "SOLVER_BACKED", "weak": True, "notes": notes}
        # derive/prove: solver outcomes are diagnostic only (§E.5) —
        # only the D1 weak chain above may justify SOLVER_BACKED
        if kind in ("derive", "prove"):
            raise MSVEError(
                "EVIDENCE_MISSING",
                f"kind {kind!r}: solver outcomes are diagnostic only; "
                "SOLVER_BACKED denied",
            )
        if not outcome_compatible(kind, outcome, semantic_variant):
            raise MSVEError(
                "EVIDENCE_MISSING",
                f"outcome {outcome} with {semantic_variant} is not compatible "
                f"for kind {kind!r}; SOLVER_BACKED denied",
            )
        return {"basis": "SOLVER_BACKED", "weak": False, "notes": notes}

    if basis_ask == "TEST_BACKED":
        trs = evidence.get("test_records", [])
        linked = [t for t in trs if t.get("claim_id") == claim_id and t.get("passed") is True]
        if not linked:
            raise MSVEError(
                "EVIDENCE_MISSING",
                "TEST_BACKED requires at least one passing test record bound to the claim_id",
            )
        notes.append(f"{len(linked)} passing test record(s) bound to claim")
        return {"basis": "TEST_BACKED", "weak": False, "notes": notes}

    if basis_ask == "INDEPENDENT_RECOMPUTE":
        rec = evidence.get("recompute")
        if not rec or rec.get("agrees") is not True:
            raise MSVEError(
                "EVIDENCE_MISSING",
                "INDEPENDENT_RECOMPUTE requires a recompute record with agrees=true "
                "from the independent checker core",
            )
        notes.append(f"independent checker {rec.get('checker')!r} agrees (record {rec.get('record_ref')})")
        return {"basis": "INDEPENDENT_RECOMPUTE", "weak": False, "notes": notes}

    raise MSVEError("UNSUPPORTED_BASIS", f"unknown basis: {basis_ask!r}")
