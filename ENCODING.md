# D6 Canonical Encoding — msve-descriptor-1 (prototype, candidate 0.8.9)

Normative reference: candidate 0.8.9, Amendment A6 (D6).

## Primitives

- **String → bytes:** NFC-normalize (Unicode), then UTF-8 encode.
  Surrogate codepoints are rejected (no canonical form).
- **Scalar encoding:** `enc_scalar(s) = 0x00` if `s` is null/absent;
  otherwise `0x01 || u32be(len(bytes)) || bytes`. The tag byte
  distinguishes null from empty string.
- **Type representation:** types are carried by FIXED TYPED FIELD
  POSITIONS with mandatory validation, not by explicit byte-level type
  tags. The `0x00`/`0x01` tag distinguishes null/absent from present
  ONLY. A non-string value at a string position is a validation failure.
- **Normalization:** the encoder NORMALISES to NFC before hashing;
  non-NFC input is normalised, not rejected. Recorded descriptor fields
  are stored verbatim (byte-preservation); the identity is computed over
  the normalised encoding.
- **List encoding:** `enc_list(items) = u32be(count) || enc_scalar(i_1)
  || … || enc_scalar(i_n)`, with items sorted bytewise by encoded bytes
  before encoding. The count makes the collection boundary explicit.

## Descriptor encoding

Fixed field order:

1. `kind` (string, required)
2. `proposition` (string, required)
3. `goal_ref` (string or null; empty string distinct from null)
4. `inputs_ref` (string or null; empty string distinct from null)
5. `assumptions` (string list — **sorted by encoded byte string**,
   byte-wise lexicographic, before encoding; elements non-null)
6. `spec_version` (string, required)
7. `"msve-descriptor-1"` (encoding version, bound into the preimage)

```
preimage = enc_scalar(kind) || enc_scalar(proposition)
         || enc_scalar(goal_ref) || enc_scalar(inputs_ref)
         || enc_list(assumptions_sorted)
         || enc_scalar(spec_version) || enc_scalar("msve-descriptor-1")
```

`claim_id = sha256(preimage)` rendered as 64-char lowercase hex.

## Worked properties

- **Unambiguous boundaries:** length prefixes + the collection count make
  every field extent deterministic; the boundary between the
  variable-length assumptions collection and `spec_version` is explicit
  (no implicit "last frame" rule).
- **Null vs empty:** `goal_ref = null` → `0x00`; `goal_ref = ""` →
  `0x01 || u32be(0)` — distinct identities.
- **Version binding:** the encoding version is hashed into the preimage,
  so a future encoding version cannot silently redefine an identity.
- **Order sensitivity:** reordering fields changes the bytes — intended.
- **Collection order:** `["b","a"]` and `["a","b"]` share an identity —
  intended (assumptions are a set).
- **Duplicates:** preserved as listed after sorting; they change the
  count prefix and hence the id.
- **Transition:** identities from the pre-A6 prototype encoding are
  historical and are never recomputed under this rule.

## Test vectors

See `vectors/canonical_vectors.json`: each entry gives the descriptor
fields, the expected `claim_id`, and the encoding version. Vectors cover
empty/multiple assumptions, duplicate handling, collection boundaries,
ambiguous scalar boundaries (`a|b`, commas), Unicode normalization,
null vs empty, and encoding-version binding.
