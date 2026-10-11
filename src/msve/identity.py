"""D6 canonical identity: msve-descriptor-1 byte-level encoding.

Normative reference: candidate 0.8.9.1, Amendment A6 (D6), Finding 4.

Encoding (all integers unsigned big-endian; utf8_nfc = NFC-normalized UTF-8):
  enc_scalar(s) = b"\\x00"                            if s is None
                = b"\\x01" + u32be(len) + utf8_nfc(s)  otherwise
  enc_list(items) = u32be(count) + enc_scalar(i_1) + ... + enc_scalar(i_n)
                    with items sorted bytewise by utf8_nfc bytes
  preimage = enc_scalar(claim_kind) || enc_scalar(proposition)
           || enc_scalar(goal_ref) || enc_scalar(inputs_ref)
           || enc_list(assumptions)
           || enc_scalar(spec_version) || enc_scalar("msve-descriptor-1")
  claim_id = sha256(preimage), 64-char lowercase hex.

Type representation: FIXED TYPED FIELD POSITIONS with mandatory
validation, not explicit byte-level type tags. The 0x00/0x01 tag
distinguishes null/absent from present only.
Normalization: the encoder normalises to NFC; non-NFC input is
normalised, not rejected. Recorded fields are stored verbatim.
Null/empty/absent: kind/proposition/spec_version required non-empty;
goal_ref/inputs_ref may be null or non-empty string ("" != null);
assumptions is a required list of non-null strings.

The trailing encoding-version field binds the identity to this version.
Transition: identities computed by the pre-A6 prototype encoding are
historical and are never recomputed under this rule.
"""
import hashlib
import struct
import unicodedata

ENCODING_VERSION = "msve-descriptor-1"

FIELD_ORDER = ("kind", "proposition", "goal_ref", "inputs_ref", "assumptions", "spec_version")


def _b(s):
    if not isinstance(s, str):
        raise TypeError(f"canonical field must be str, got {type(s).__name__}")
    return unicodedata.normalize("NFC", s).encode("utf-8")


def _enc_scalar(s):
    if s is None:
        return b"\x00"
    b = _b(s)
    return b"\x01" + struct.pack(">I", len(b)) + b


def _enc_list(items):
    if not isinstance(items, list) or not all(isinstance(x, str) for x in items):
        raise TypeError("assumptions must be a list of strings")
    enc = sorted(_b(x) for x in items)
    return struct.pack(">I", len(enc)) + b"".join(
        b"\x01" + struct.pack(">I", len(e)) + e for e in enc
    )


def canonical_bytes(descriptor):
    """descriptor: dict with keys kind, proposition, goal_ref, inputs_ref,
    assumptions (list of str), spec_version. goal_ref/inputs_ref may be None.
    Returns the msve-descriptor-1 preimage bytes."""
    parts = []
    for key in FIELD_ORDER:
        if key not in descriptor:
            raise KeyError(f"descriptor missing field: {key}")
        if key == "assumptions":
            parts.append(_enc_list(descriptor[key]))
        else:
            parts.append(_enc_scalar(descriptor[key]))
    parts.append(_enc_scalar(ENCODING_VERSION))
    return b"".join(parts)


def claim_id(descriptor):
    return hashlib.sha256(canonical_bytes(descriptor)).hexdigest()
