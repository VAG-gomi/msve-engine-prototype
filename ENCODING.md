# D6 Canonical Encoding — byte-level rules (prototype v0.1.0-proto)

## Primitives

- **String → bytes:** NFC-normalize (Unicode), then UTF-8 encode.
- **Length prefix:** 4-byte unsigned big-endian integer = byte length.
- **Field:** `len(field_bytes) || field_bytes`.
- **String list:** `len(count) || field(elem_1) || … || field(elem_n)`,
  where `len(count)` is a 4-byte big-endian element count.

## Descriptor encoding

Fixed field order:

1. `kind` (string)
2. `proposition` (string)
3. `goal_ref` (string)
4. `inputs_ref` (string)
5. `assumptions` (string list — **sorted by encoded byte string**,
   byte-wise lexicographic, before encoding)
6. `spec_version` (string)

```
canonical = field(kind) || field(proposition) || field(goal_ref)
          || field(inputs_ref) || list(assumptions_sorted) || field(spec_version)
```

`claim_id = sha256(canonical)` rendered as 64-char lowercase hex.

## Worked properties

- **Unambiguous boundaries:** length prefixes make field extents
  deterministic; `|` and `,` in content cannot corrupt parsing (this
  repairs the escaping gap in the spec's `|`-joined form, which this
  prototype does not use).
- **Order sensitivity:** reordering fields changes the bytes and hence
  the id — intended.
- **Collection order:** assumptions are sorted, so `["b","a"]` and
  `["a","b"]` share an identity — intended (assumptions are a set).
- **Duplicates:** duplicate assumption strings are preserved as listed
  after sorting (not deduplicated); they change the count prefix and
  hence the id.

## Test vectors

See `vectors/canonical_vectors.json`: each entry gives the descriptor
fields and the expected `claim_id`. Vectors include ambiguous-boundary
cases (`a|b` vs `a` + `b`, commas in assumptions, empty proposition,
Unicode normalization pairs).
