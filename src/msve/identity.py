"""D6 canonical identity: byte-level encoding and SHA-256 claim identity.

Rules (see ENCODING.md):
- strings -> NFC-normalized UTF-8 bytes
- fixed field order: kind, proposition, goal_ref, inputs_ref, assumptions, spec_version
- each field length-prefixed with 4-byte big-endian length
- assumptions sorted by byte string, encoded as count + elements
- claim_id = sha256(canonical_bytes), 64-char lowercase hex
"""
import hashlib
import struct
import unicodedata

FIELD_ORDER = ("kind", "proposition", "goal_ref", "inputs_ref", "assumptions", "spec_version")


def _b(s):
    if not isinstance(s, str):
        raise TypeError(f"canonical field must be str, got {type(s).__name__}")
    return unicodedata.normalize("NFC", s).encode("utf-8")


def _field(b):
    return struct.pack(">I", len(b)) + b


def _str_list(items):
    if not isinstance(items, list) or not all(isinstance(x, str) for x in items):
        raise TypeError("assumptions must be a list of strings")
    enc = sorted(_b(x) for x in items)
    return struct.pack(">I", len(enc)) + b"".join(_field(e) for e in enc)


def canonical_bytes(descriptor):
    """descriptor: dict with keys kind, proposition, goal_ref, inputs_ref,
    assumptions (list), spec_version. Returns canonical bytes."""
    parts = []
    for key in FIELD_ORDER:
        if key not in descriptor:
            raise KeyError(f"descriptor missing field: {key}")
        if key == "assumptions":
            parts.append(_str_list(descriptor[key]))
        else:
            parts.append(_field(_b(descriptor[key])))
    return b"".join(parts)


def claim_id(descriptor):
    return hashlib.sha256(canonical_bytes(descriptor)).hexdigest()
