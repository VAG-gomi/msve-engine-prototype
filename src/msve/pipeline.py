"""Pipeline orchestration: decode -> admission -> identity -> solver -> assurance -> typed result."""
import hashlib

from . import admission as adm
from . import assurance as asr
from . import checker
from . import decode as dec
from . import identity as ident
from . import queries
from . import result as resmod
from . import solver as solv
from .capacity import check_limit, load_config
from .errors import MSVEError

ARCHIVAL = {
    "spec": "candidate/0.8.8.1/MSVE_DESIGN_SPEC_v0.8.md",
    "spec_sha256": "dbc610c3a97d7107ab0f4de499b240e243f45c49b56f0a1855b7333c80cb7782",
    "rulings": "decision-ledger/MSVE_BRAINSTORM_DECISION_LEDGER.csv (DEC-008..DEC-016, DEC-025)",
    "prototype": "MSVE-WO-1.0 exploratory prototype v0.1.0-proto",
}


def _invocation_id(claim_id_val, qid):
    return hashlib.sha256(f"{claim_id_val}:{qid}".encode()).hexdigest()


def run(doc, cfg=None):
    """Execute the full pipeline on a decoded+validated document dict.
    Returns the typed result dict. Raises MSVEError on rejection."""
    cfg = cfg or load_config()
    doc = dec.validate_document(doc)
    claim = doc["claim"]
    evidence = doc.get("evidence", {})
    discrepancies = []

    # 1. admission
    verdict, notes = adm.admit(doc, cfg)
    if verdict == "REJECTED":
        raise MSVEError("ADMISSION_REJECTED", "; ".join(notes))

    # 2. identity (D6) — computed even for non-accepted verdicts so the
    #    result identifies the claim that was judged
    descriptor = {
        "kind": claim["kind"],
        "proposition": claim["proposition"],
        "goal_ref": claim["goal_ref"],
        "inputs_ref": claim["inputs_ref"],
        "assumptions": claim["assumptions"],
        "spec_version": doc["spec_version"],
        "assurance_required": claim.get("assurance_required"),
    }
    cid = ident.claim_id(descriptor)

    # UNSUPPORTED / UNDERSPECIFIED: record the verdict explicitly, award nothing
    if verdict in ("UNSUPPORTED", "UNDERSPECIFIED"):
        return resmod.build(
            admission_verdict=verdict,
            admission_notes=notes,
            descriptor=descriptor,
            claim_id_val=cid,
            semantic_result={"variant": "RECORDED_UNINTERPRETED",
                             "reason": f"admission verdict {verdict}"},
            solver_observation=None,
            assurance={"basis": None, "weak": False, "notes": notes},
            evidence={},
            discrepancies=[],
            provenance=dict(ARCHIVAL),
        )

    # 3. solver (if query present and kind uses it)
    solver_obs = None
    query = claim.get("query")
    if query is not None:
        qid = queries.query_id(query)
        inv_id = _invocation_id(cid, qid)
        check_limit(cfg, "max_invocations", 1, "solver invocations")
        solver_obs = solv.run(query, cfg["solver_timeout_ms"], inv_id)
        evidence = dict(evidence)
        evidence["solver_observation"] = solver_obs

    outcome = solver_obs["outcome"] if solver_obs else None

    # 4. semantic result
    kind = claim["kind"]
    if solver_obs is None:
        semantic = {"variant": "RECORDED_UNINTERPRETED" if kind in adm.SEVEN_KINDS else "INCONCLUSIVE",
                     "reason": "no solver observation; claim recorded"}
    else:
        variant = asr.semantic_for(kind, outcome)
        semantic = {"variant": variant}
        if variant == "VIOLATED":
            semantic["witness_ref"] = "solver_observation.model"
            semantic["witness"] = solver_obs.get("model", {})
        if variant == "INCONCLUSIVE":
            semantic["reason"] = f"solver outcome {outcome} for kind {kind!r}"
        if variant == "RECORDED_UNINTERPRETED":
            semantic["reason"] = "kind interpretation undefined (D2); observation recorded only"

    # 5. independent recompute check (D4) — run core B when asked
    basis_ask = doc.get("assurance_ask")
    if basis_ask == "INDEPENDENT_RECOMPUTE" and query is not None and solver_obs:
        ok, why = checker.agrees_with_solver(query, outcome, cfg["checker_enumeration_bound"])
        if not ok:
            discrepancies.append({"checker": "core-b", "issue": why})
            raise MSVEError("CHECKER_DISAGREEMENT", f"independent checker did not confirm: {why}")
        evidence["recompute"] = {
            "checker": "core-b",
            "agrees": True,
            "record_ref": f"core-b:{queries.query_id(query)[:16]}",
            "note": why,
        }

    # 6. assurance
    assurance = asr.award(kind, outcome, semantic["variant"], evidence, cid, basis_ask)

    # 7. verification records (capacity-gated slots)
    check_limit(cfg, "max_verification_records", 0, "verification records")

    return resmod.build(
        admission_verdict=verdict,
        admission_notes=notes,
        descriptor=descriptor,
        claim_id_val=cid,
        semantic_result=semantic,
        solver_observation=solver_obs,
        assurance=assurance,
        evidence={k: v for k, v in evidence.items() if k != "solver_observation"},
        discrepancies=discrepancies,
        provenance=dict(ARCHIVAL),
    )


def run_text(text, cfg=None):
    return run(dec.decode(text), cfg)
