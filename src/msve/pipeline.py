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


import re as _re
_HASH_RE = _re.compile(r"^[0-9a-f]{64}$")

def _validate_hash(v, field_name):
    """0.8.9.6: strict Hash validation. Rejects non-64-char hex."""
    from .errors import MSVEError
    if not isinstance(v, str) or not _HASH_RE.match(v):
        raise MSVEError("MALFORMED_INPUT",
                        f"{field_name} must be 64-char lowercase hex, got {v!r}")
    return v


def _invocation_id(claim_id_val, claim_kind, qid, query_canon, inputs_ref,
                     spec_version, tool, tool_version, config, timeout_ms,
                     nonce):
    # 0.8.9.5: execution-specific invocation ID. SHA-256 over canonical
    # encoding of complete metadata. Different configurations/timeouts/
    # versions yield different IDs even for same claim+query.
    import struct
    def enc_str(x):
        # 0.8.9.7: Normative invocation encoding for REQUIRED fields.
        # enc_str(s) = u32be(len(UTF8(s))) || UTF8(s).
        # All invocation-ID fields are required; the optional-value
        # 0x00/0x01 encoding is NOT used here (see descriptor encoding).
        # inputs_ref is always a valid hash (derived, never None).
        assert x is not None, "invocation field must not be None"
        b = str(x).encode("utf-8")
        return struct.pack(">I", len(b)) + b
    parts = [
        enc_str(claim_id_val), enc_str(claim_kind),
        enc_str(qid), enc_str(query_canon),
        enc_str(inputs_ref), enc_str(spec_version),
        enc_str(tool), enc_str(tool_version),
        enc_str(config), struct.pack(">I", timeout_ms),
        enc_str(nonce),
    ]
    return hashlib.sha256(b"".join(parts)).hexdigest()


def _run_impl(doc, cfg=None):
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
        # 0.8.9.6: derive verification_inputs_ref per normative.
        # If claim provides valid inputs_ref, use it; else hash the query.
        # NEVER copy null as empty string.
        _claim_inputs = claim.get("inputs_ref")
        if _claim_inputs is not None:
            _validate_hash(_claim_inputs, "claim.inputs_ref")
            _verif_inputs_ref = _claim_inputs
        else:
            # 0.8.9.7: No external inputs referenced. The query-ID is
            # SHA-256 over the canonical query bytes (see queries.query_id),
            # so it IS the fallback verification-input identity. Do NOT
            # hash the hex digest a second time.
            _verif_inputs_ref = qid
        import uuid
        # 0.8.9.6: cryptographically random nonce (UUID4) for robust
        # per-execution uniqueness. Timestamp-based nonces can collide
        # under concurrency or coarse clock resolution.
        nonce = str(uuid.uuid4())
        import json as _json
        qcanon = _json.dumps(query, sort_keys=True, separators=(",", ":")).encode("utf-8").decode("utf-8")
        inv_id = _invocation_id(
            cid, claim.get("kind", "msve/expr"),
            qid, qcanon,
            _verif_inputs_ref, doc["spec_version"],
            "z3", solv.VERSION if hasattr(solv, "VERSION") else "unknown",
            str(cfg.get("solver_config", "default")),
            cfg["solver_timeout_ms"], nonce)
        check_limit(cfg, "max_invocations", 1, "solver invocations")
        _solver_config = str(cfg.get("solver_config", "default"))
        solver_obs = solv.run(query, cfg["solver_timeout_ms"], inv_id,
                              config=_solver_config)
        # 0.8.9.6: provenance_ref IS the invocation_id (normative mapping).
        # The solver returns invocation_id; we map it to provenance_ref
        # for the SolverObs record. Config must match the invocation.
        solver_obs["provenance_ref"] = solver_obs.pop("invocation_id")
        assert solver_obs["config"] == _solver_config, "config mismatch"
        # A1 binding: the observation is bound to the actual claim, query,
        # and specification version (in addition to invocation_id, which
        # already binds claim_id + query_id).
        solver_obs["claim_id"] = cid
        solver_obs["spec_version"] = doc["spec_version"]
        # 0.8.9.3: explicit bound on the invocation for SAT-corroboration binding
        # 0.8.9.4: timeout_ms is DISTINCT from Core B enumeration bound
        solver_obs["timeout_ms"] = cfg["solver_timeout_ms"]
        # 0.8.9.5: full execution-specific invocation record
        evidence["solver_invocations"] = [{
            "invocation_id": inv_id,
            "claim_id": cid,
            "claim_kind": claim.get("kind", "msve/expr"),
            "query": query,
            "query_id": qid,
            "query_payload": qcanon,
            "inputs_ref": _verif_inputs_ref,
            "spec_version": doc["spec_version"],
            "tool": "z3",
            "version": solv.VERSION if hasattr(solv, "VERSION") else "unknown",
            "config": _solver_config,
            "timeout_ms": cfg["solver_timeout_ms"],
            "execution_nonce": nonce,
        }]
        evidence["solver_observation"] = solver_obs
        # 0.8.9.6: bundle-level duplicate invocation ID rejection
        _check_invocation_uniqueness(evidence["solver_invocations"])

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

    # 5b. typed SAT-corroboration records (0.8.9.2 §2): every binding explicit.
    sat_corrs = []
    rc = evidence.get("recompute")
    if rc and rc.get("agrees") and rc.get("witness_validated"):
        import hashlib, json as _json
        w = rc.get("witness") or {}
        wbytes = _json.dumps(w, sort_keys=True, separators=(",", ":")).encode("utf-8")
        wartifact = hashlib.sha256(wbytes).hexdigest()
        # 0.8.9.3: witness artifact resolves in evidence.witnesses
        if "witnesses" not in evidence:
            evidence["witnesses"] = []
        if wartifact not in evidence["witnesses"]:
            evidence["witnesses"].append(wartifact)
        sat_corrs.append({
            "claim_id": cid,
            "query_id": rc.get("query_id"),
            "spec_version": descriptor.get("spec_version"),
            "checker": rc.get("checker"),
            "checker_version": rc.get("checker_version"),
            "configured_bound": rc.get("bound"),
            "witness": {
                "artifact": wartifact,
                "checked_against": rc.get("query_id"),
                "checked_by": rc.get("checker"),
                "validation_result": "PASS",
            },
            "execution": {
                "method": "independent-sat-check",
                "detail": rc.get("note"),
            },
        })
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
        sat_corroborations=sat_corrs,
        quarantined_input_evidence=quarantined,
        provenance=dict(ARCHIVAL),
    )


def _check_invocation_uniqueness(invocations):
    """Reject duplicate invocation IDs within an evidence bundle.
    (0.8.9.6, Inv 27c normative requirement.)"""
    seen = set()
    for inv in invocations:
        iid = inv.get("invocation_id")
        if iid in seen:
            from .errors import MSVEError
            raise MSVEError("INVALID_INPUT",
                            f"duplicate invocation_id in evidence bundle: {iid[:16]}...")
        seen.add(iid)


def run(doc, cfg=None):
    """Execute the full pipeline. Returns the typed result dict.

    Capacity overflow (CAPACITY_EXCEEDED) is returned as a typed result with
    an explicit capacity_exceeded field (Correction 0.8.9.2 §6), not raised.
    Other MSVEError rejections are still raised.
    """
    try:
        return _run_impl(doc, cfg)
    except MSVEError as e:
        if e.code != "CAPACITY_EXCEEDED":
            raise
        # Build the minimal descriptor for the capacity-failure result.
        # (Identity is computable from the claim even when capacity fails.)
        claim = doc.get("claim", {})
        descriptor = {
            "kind": claim.get("kind"),
            "proposition": claim.get("proposition"),
            "goal_ref": claim.get("goal_ref"),
            "inputs_ref": claim.get("inputs_ref"),
            "assumptions": claim.get("assumptions", []),
            "spec_version": doc.get("spec_version"),
            "assurance_required": claim.get("assurance_required"),
        }
        try:
            cid = ident.claim_id(descriptor)
        except Exception:
            cid = None
        d = e.details or {}
        return resmod.build(
            admission_verdict="ACCEPTED",
            admission_notes=[],
            descriptor=descriptor,
            claim_id_val=cid,
            query_id_val=None,
            semantic_result={"variant": "INCONCLUSIVE", "reason": "CAPACITY_EXCEEDED"},
            solver_observation=None,
            assurance={"basis": None, "weak": False,
                       "notes": ["capacity exceeded; no basis awarded"]},
            evidence={},
            discrepancies=[],
            sat_corroborations=[],
            quarantined_input_evidence=[],
            provenance=dict(ARCHIVAL),
            capacity_exceeded={
                "parameter": d.get("key"),
                "limit": d.get("limit"),
                "actual": d.get("actual"),
                "detail": str(e),
            },
        )



def run_text(text, cfg=None):
    return run(dec.decode(text), cfg)
