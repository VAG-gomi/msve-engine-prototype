"""Typed result assembly with full provenance."""
import hashlib
import json
import time


def build(admission_verdict, admission_notes, descriptor, claim_id_val,
          semantic_result, solver_observation, assurance, evidence,
          discrepancies, provenance):
    result = {
        "experimental": True,
        "admission": admission_verdict,
        "admission_notes": admission_notes,
        "claim_id": claim_id_val,
        "claim_kind": descriptor["kind"],
        "proposition": descriptor["proposition"],
        "spec_version": descriptor["spec_version"],
        "semantic_result": semantic_result,
        "solver_observation": solver_observation,
        "assurance_required": descriptor.get("assurance_required"),
        "assurance_achieved": assurance["basis"],
        "assurance_weak": assurance["weak"],
        "assurance_notes": assurance["notes"],
        "assumptions_unverified": descriptor["assumptions"],
        "evidence": evidence or {},
        "verification_records": [],
        "discrepancies": discrepancies,
        "provenance": provenance,
        "produced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return result


def result_id(result):
    canon = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canon).hexdigest()
