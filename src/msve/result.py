"""Typed result assembly with full provenance."""
import hashlib
import json
import time


def build(admission_verdict, admission_notes, descriptor, claim_id_val,
          semantic_result, solver_observation, assurance, evidence,
          discrepancies, provenance, quarantined_input_evidence=None,
          query_id_val=None, sat_corroborations=None, capacity_exceeded=None):
    result = {
        "experimental": True,
        "admission": admission_verdict,
        "admission_notes": admission_notes,
        "claim_id": claim_id_val,
        "claim_kind": descriptor["kind"],
        "proposition": descriptor["proposition"],
        "spec_version": descriptor["spec_version"],
        # Finding 2 (0.8.9.1): query_id declared on the result record,
        # matching the solver invocation's query_id per the binding rules.
        "query_id": query_id_val,
        # D3 boundary (see PROTOTYPE_CONTRACT.md §10): the engine solves the
        # formal query; it does NOT establish that the query represents the
        # natural-language proposition. The semantic result describes the
        # query outcome only.
        "claim_query_link": "UNVERIFIED",
        "claim_query_link_note": (
            "The solver decided the formal msve-arith-v1 query. No verified "
            "correspondence between the natural-language proposition and the "
            "formal query is established by this engine."
        ),
        "semantic_result": semantic_result,
        "solver_observation": solver_observation,
        "assurance_required": descriptor.get("assurance_required"),
        "assurance_achieved": assurance["basis"],
        "assurance_weak": assurance["weak"],
        "assurance_notes": assurance["notes"],
        "assumptions_unverified": descriptor["assumptions"],
        "evidence": evidence or {},
        "quarantined_input_evidence": quarantined_input_evidence or [],
        "verification_records": [],
        "sat_corroborations": sat_corroborations or [],
        "capacity_exceeded": capacity_exceeded,
        "discrepancies": discrepancies,
        "provenance": provenance,
        "produced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return result


def result_id(result):
    canon = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canon).hexdigest()
