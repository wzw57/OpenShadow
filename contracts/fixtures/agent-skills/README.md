# Agent Skills Contract Fixtures

These fixtures validate compatibility with the external Agent Skills directory
format and the independent OpenShadow governance boundary.

- `minimal-valid/` and `complete-valid/` must pass Agent Skills validation.
- `allowed-tools-untrusted/` is format-valid, but its experimental
  `allowed-tools` declaration must not create a Shadow Capability grant.
- `invalid-name-mismatch/` and `invalid-frontmatter/` must fail format
  validation.
- `invalid-path-traversal/manifest.json` must fail Shadow bundle import.
- `digest-changed/` demonstrates that one byte of content changes the bundle
  digest and invalidates digest-bound trust and high-risk permission.
- `manifests/` and `digest-results.json` pin the deterministic sidecar output
  for the positive and content-change fixtures.

Shadow sidecar data is deliberately not written into any fixture bundle.
