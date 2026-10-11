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
    # Both operands are fixed 64-char lowercase hex (sha256). The ":"
    # delimiter is therefore at a deterministic position (byte 64) and the
    # parse is unique without additional framing (see spec §E.6b, 0.8.9.1).
    assert len(claim_id_val) == 64 and len(qid) == 64
    return hashlib.sha256(f"{claim_id_val}:{qid}".encode()).hexdigest()


def run(doc, cfg=None):
    """Execute the full pipeline on a decoded+validated document dict.
    Returns the typed result dict. Raises MSVEError on rejection.

    Configuration (D5): if cfg is given explicitly it is used as-is.
    Otherwise it is built from defaults plus the input document's
    config.capacity overrides, range-validated by load_config().
    """
    doc = dec.validate_document(doc)
    if cfg is None:
        input_capacity = None
        config_node = doc.get("config")
        if config_node is not None:
            if not isinstance(config_node, dict):
                raise MSVEError("MALFORMED_INPUT", "'config' must be an object")
            input_capacity = config_node.get("capacity")
        cfg = load_config(overrides=input_capacity)
    claim = doc["claim"]
    evidence = doc.get("evidence", {})
    discrepancies = []
    quarantined = []

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

    # Input policy (applies on all paths): caller-supplied evidence records
    # are NEVER trusted as assurance evidence. Quarantine them transparently;
    # only records generated from the CURRENT execution can satisfy award().
    #  - evidence.recompute: regenerated from the current Core B run (D4).
    #  - evidence.test_records: no trusted test-execution mechanism exists in
    #    this prototype, so TEST_BACKED is refused outright (WO-1.4).
    evidence = dict(evidence)
    for _field in ("recompute", "test_records"):
        if _field in evidence:
            quarantined.append({
                "field": f"evidence.{_field}",
                "reason": ("caller-supplied evidence records are not trusted; "
                           "only current-execution records are used" if _field == "recompute"
                           else "no trusted test-execution mechanism exists in this prototype; "
                                "TEST_BACKED cannot be earned from supplied records"),
                "record": evidence.pop(_field),
            })

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
            quarantined_input_evidence=quarantined,
            provenance=dict(ARCHIVAL),
        )

    # 3. solver (if query present and kind uses it)
    solver_obs = None
    qid = None
    query = claim.get("query")
    if query is not None:
        qid = queries.query_id(query)
        inv_id = _invocation_id(cid, qid)
        check_limit(cfg, "max_invocations", 1, "solver invocations")
        solver_obs = solv.run(query, cfg["solver_timeout_ms"], inv_id)
        # A1 binding: the observation is bound to the actual claim, query,
        # and specification version (in addition to invocation_id, which
        # already binds claim_id + query_id).
        solver_obs["claim_id"] = cid
        solver_obs["spec_version"] = doc["spec_version"]
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

    # 5. independent recompute check (D4) — run core B when asked.
    # Input policy: caller-supplied evidence.recompute records were already
    # quarantined above (never trusted). Only a record generated from the
    # CURRENT checker execution — bound to claim_id, query_id, checker
    # identity/version and bound — can satisfy award(). Disagreement is
    # RECORDED in the typed result: the observation-derived semantic is
    # preserved, the discrepancy is explicit, and no basis is awarded.
    basis_ask = doc.get("assurance_ask")
    if basis_ask == "INDEPENDENT_RECOMPUTE" and query is not None and solver_obs:
        qid = queries.query_id(query)
        ok, why, witness = checker.agrees_with_solver(query, outcome, cfg["checker_enumeration_bound"])
        if ok:
            evidence["recompute"] = {
                "checker": checker.CHECKER_ID,
                "checker_version": checker.CHECKER_VERSION,
                "agrees": True,
                "claim_id": cid,
                "query_id": qid,
                "bound": cfg["checker_enumeration_bound"],
                "record_ref": f"core-b:{qid[:16]}",
                # Finding 3: SAT-corroboration path carries the independently
                # generated witness, validated against the exact formal query.
                "witness": witness,
                "witness_validated": True,
                "note": why,
            }
        else:
            discrepancies.append({"checker": "core-b", "issue": why,
                                  "solver_outcome": outcome})

    # 6. assurance — awarded only on evidence; a failed corroboration
    # yields an explicit no-basis result, never a silent downgrade
    try:
        assurance = asr.award(kind, outcome, semantic["variant"], evidence, cid, basis_ask,
                              expected_bound=cfg["checker_enumeration_bound"])
    except MSVEError as e:
        if basis_ask == "INDEPENDENT_RECOMPUTE" and discrepancies:
            assurance = {"basis": None, "weak": False,
                         "notes": [f"withheld: {e.code}: {e}"]}
        else:
            raise

    # 7. verification records (capacity-gated slots)
    check_limit(cfg, "max_verification_records", 0, "verification records")

    return resmod.build(
        admission_verdict=verdict,
        admission_notes=notes,
        descriptor=descriptor,
        claim_id_val=cid,
        query_id_val=qid,
        semantic_result=semantic,
        solver_observation=solver_obs,
        assurance=assurance,
        evidence={k: v for k, v in evidence.items() if k != "solver_observation"},
        discrepancies=discrepancies,
        quarantined_input_evidence=quarantined,
        provenance=dict(ARCHIVAL),
    )


def run_text(text, cfg=None):
    return run(dec.decode(text), cfg)
