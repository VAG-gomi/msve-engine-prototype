"""Decode: parse top-level JSON input and validate its schema."""
import json

from .errors import MSVEError

SPEC_VERSIONS = ("0.8.8.1",)
CLAIM_KINDS = (
    "derive", "prove", "holds",
    "no_solution", "contradiction", "unique_under_projection",
    "violated", "underdetermined", "disproved", "artifact_constructed",
)
ASSURANCE_LEVELS = ("LEVEL_A", "LEVEL_B")


def decode(text):
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise MSVEError("MALFORMED_INPUT", f"input is not valid JSON: {e}")
    if not isinstance(doc, dict):
        raise MSVEError("MALFORMED_INPUT", "top-level input must be an object")
    return doc


def validate_document(doc):
    if doc.get("spec_version") not in SPEC_VERSIONS:
        raise MSVEError(
            "UNKNOWN_SPEC_VERSION",
            f"unsupported spec_version: {doc.get('spec_version')!r}",
            {"supported": list(SPEC_VERSIONS)},
        )
    claim = doc.get("claim")
    if not isinstance(claim, dict):
        raise MSVEError("MALFORMED_INPUT", "missing 'claim' object")
    for f in ("kind", "proposition", "goal_ref", "inputs_ref", "assumptions"):
        if f not in claim:
            raise MSVEError("MALFORMED_INPUT", f"claim missing required field: {f}")
    if claim["kind"] not in CLAIM_KINDS:
        raise MSVEError("MALFORMED_INPUT", f"unknown claim kind: {claim['kind']!r}")
    if not isinstance(claim["proposition"], str):
        raise MSVEError("MALFORMED_INPUT", "proposition must be a string")
    for f in ("goal_ref", "inputs_ref"):
        v = claim[f]
        # 0.8.9.1 (Finding 4): null/absent permitted per normative A6;
        # empty string distinct from null; non-strings rejected.
        if v is not None and (not isinstance(v, str) or not v):
            raise MSVEError("MALFORMED_INPUT", f"{f} must be null or a non-empty string")
    if not isinstance(claim["assumptions"], list) or not all(
        isinstance(a, str) for a in claim["assumptions"]
    ):
        raise MSVEError("MALFORMED_INPUT", "assumptions must be a list of strings")
    ar = claim.get("assurance_required")
    if ar is not None and ar not in ASSURANCE_LEVELS:
        raise MSVEError("MALFORMED_INPUT", f"bad assurance_required: {ar!r}")
    # query shape is validated here (dict or absent) so admission and the
    # pipeline never call .get() on a scalar/list. Full DSL validation
    # happens in queries.validate() via the solver path.
    q = claim.get("query")
    if q is not None and not isinstance(q, dict):
        raise MSVEError("MALFORMED_INPUT",
                        f"query must be an object, got {type(q).__name__}")
    # assurance_ask selects the specific basis the engine should attempt.
    # It is top-level (not inside claim) and validated here; admission and
    # award() act on it. claim.assurance_required is a recorded requirement
    # level only (see PROTOTYPE_CONTRACT.md §1).
    ask = doc.get("assurance_ask")
    if ask is not None and ask not in ("SOLVER_BACKED", "TEST_BACKED",
                                       "INDEPENDENT_RECOMPUTE", "KERNEL_PROOF"):
        raise MSVEError("MALFORMED_INPUT", f"bad assurance_ask: {ask!r}")
    ev = doc.get("evidence", {})
    if not isinstance(ev, dict):
        raise MSVEError("MALFORMED_INPUT", "evidence must be an object")
    return doc
