"""Admission and scope validation: ACCEPTED / REJECTED / UNSUPPORTED / UNDERSPECIFIED."""
from . import capacity as capmod
from .errors import MSVEError

SEVEN_KINDS = (
    "no_solution", "contradiction", "unique_under_projection",
    "violated", "underdetermined", "disproved", "artifact_constructed",
)
SOLVER_KINDS = ("holds", "derive", "prove")


def admit(doc, cfg):
    """Returns (verdict, notes). Verdict in ACCEPTED/REJECTED/UNSUPPORTED/UNDERSPECIFIED.
    REJECTED raises MSVEError; other verdicts return with explanatory notes."""
    claim = doc["claim"]
    notes = []

    # capacity checks (D5) — hard rejects
    capmod.check_limit(cfg, "max_assumptions", len(claim["assumptions"]), "assumptions")
    query = claim.get("query")
    if query is not None:
        capmod.check_limit(cfg, "max_assertions", len(query.get("assertions", [])), "assertions")
        capmod.check_limit(cfg, "max_declarations", len(query.get("declarations", [])), "declarations")

    kind = claim["kind"]

    # assurance requested?
    basis_asked = doc.get("assurance_ask")
    if basis_asked == "KERNEL_PROOF":
        return ("UNSUPPORTED", ["KERNEL_PROOF has no implemented evidence path in this prototype (no kernel)"])
    if basis_asked == "SOLVER_BACKED" and query is None:
        return ("UNDERSPECIFIED", ["SOLVER_BACKED requested but no query supplied"])
    if basis_asked == "INDEPENDENT_RECOMPUTE":
        # The recompute record is produced by the pipeline's own core B
        # (D4 independent checker), not supplied in the input. If no query
        # is present there is nothing to recompute.
        if query is None:
            return ("UNDERSPECIFIED", ["INDEPENDENT_RECOMPUTE requested but no query supplied"])
    if basis_asked == "TEST_BACKED":
        trs = (doc.get("evidence") or {}).get("test_records", [])
        if not trs:
            return ("UNDERSPECIFIED", ["TEST_BACKED requested but no test records supplied"])

    # seven kinds: recording permitted, solver-backing barred (D2)
    if kind in SEVEN_KINDS:
        notes.append(
            f"kind {kind!r}: solver-outcome interpretation undefined; "
            "recording permitted, SOLVER_BACKED justification barred (D2)"
        )
        if basis_asked == "SOLVER_BACKED":
            return ("UNSUPPORTED", notes + ["SOLVER_BACKED cannot be justified for undefined kind interpretations"])
        return ("ACCEPTED", notes)

    # derive/prove: solver is diagnostic only
    if kind in ("derive", "prove") and basis_asked == "SOLVER_BACKED":
        notes.append("derive/prove: solver outcomes are diagnostic only per §E.5")
        # D1 still permits the weak UNKNOWN+INCONCLUSIVE chain; decided at assurance time
        return ("ACCEPTED", notes)

    return ("ACCEPTED", notes)
