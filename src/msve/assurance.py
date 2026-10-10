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
from .checker import CHECKER_ID, CHECKER_VERSION
from .errors import MSVEError


def outcome_compatible(kind, outcome, semantic_variant):
    # D2 first: undefined interpretations can never justify SOLVER_BACKED,
    # including via the UNKNOWN row below.
    if kind in SEVEN_KINDS:
        return False
    if kind == "holds":
        return (outcome == "UNSAT" and semantic_variant == "HOLDS") or (
            outcome == "SAT" and semantic_variant == "VIOLATED"
        )
    if kind in ("derive", "prove"):
        return semantic_variant == "INCONCLUSIVE"
    if outcome == "UNKNOWN":
        return semantic_variant == "INCONCLUSIVE"
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


def award(kind, outcome, semantic_variant, evidence, claim_id, basis_ask,
          expected_bound=None):
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
        # D2 guard (defense in depth; admission also blocks): the D1
        # exception below must never grant SOLVER_BACKED for the seven
        # undefined kinds.
        if kind in SEVEN_KINDS:
            raise MSVEError(
                "EVIDENCE_MISSING",
                f"kind {kind!r}: interpretation undefined (D2); SOLVER_BACKED denied",
            )
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
        # WO-1.4: refused — no trusted test-execution mechanism exists in
        # this prototype, so caller-supplied test records must not earn the
        # basis (not even well-formed ones). See PROTOTYPE_CONTRACT.md §8.
        raise MSVEError(
            "UNSUPPORTED_BASIS",
            "TEST_BACKED has no trusted test-execution mechanism in this prototype",
        )

    if basis_ask == "INDEPENDENT_RECOMPUTE":
        rec = evidence.get("recompute")
        if not rec or rec.get("agrees") is not True:
            raise MSVEError(
                "EVIDENCE_MISSING",
                "INDEPENDENT_RECOMPUTE requires a recompute record with agrees=true "
                "from the independent checker core",
            )
        # Fail closed (WO-1.5): the expected enumeration bound is required.
        # Omitting it must not grant the basis.
        if expected_bound is None:
            raise MSVEError(
                "EVIDENCE_MISSING",
                "INDEPENDENT_RECOMPUTE requires an expected enumeration bound; "
                "refusing without one",
            )
        # Complete binding: the record must match the current execution on
        # every contract-required field — claim ID, query ID, checker
        # identity, checker version, and enumeration bound (missing and
        # mismatched both rejected). The pipeline quarantines
        # caller-supplied records, but award() does not rely on that alone.
        #
        # Provenance note: field matching establishes CONSISTENCY, not
        # provenance. The trusted source of recomputation records is the
        # pipeline's controlled checker execution; at this direct-function
        # boundary a perfectly consistent fabricated record is
        # indistinguishable from a genuine one.
        obs = evidence.get("solver_observation") or {}
        mismatches = []
        if rec.get("claim_id") != claim_id:
            mismatches.append("claim_id")
        if rec.get("query_id") != obs.get("query_id"):
            mismatches.append("query_id")
        if rec.get("checker") != CHECKER_ID:
            mismatches.append("checker identity")
        if rec.get("checker_version") != CHECKER_VERSION:
            mismatches.append("checker version")
        if rec.get("bound") != expected_bound:
            mismatches.append("enumeration bound")
        if mismatches:
            raise MSVEError(
                "EVIDENCE_MISSING",
                "recompute record binding mismatch "
                f"({', '.join(mismatches)}); INDEPENDENT_RECOMPUTE denied",
            )
        notes.append(f"independent checker {rec.get('checker')!r} agrees (record {rec.get('record_ref')})")
        return {"basis": "INDEPENDENT_RECOMPUTE", "weak": False, "notes": notes}

    raise MSVEError("UNSUPPORTED_BASIS", f"unknown basis: {basis_ask!r}")
