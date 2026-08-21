# Stage 4 Contract Artifacts

This directory contains the machine-readable Stage 4 contract candidate. It is
normative together with `docs/contract-baseline.md`, but remains **Proposed**
until the Stage 4 validation and review gates are complete and the pull request
is merged.

## Layout

- `manifest.json` pins every offline JSON Schema by canonical `$id`, repository
  path, and SHA-256 digest.
- `schemas/` contains versioned JSON Schema 2020-12 contracts.
- `openapi/openapi.yaml` contains the minimal HTTP API surface.
- `fixtures/` contains positive and negative instances, including portable
  Agent Skills bundles and their sidecar manifests.
- `test-cases/` defines implementation-independent conformance cases.

All schema references must resolve from `manifest.json`; validators must not
fetch schemas from the network. Schema versions and bundle digests are immutable.

## Skill bundle digest v1

For `shadow.skill-bundle-digest.v1`, recursively enumerate regular files below
the skill root, reject absolute paths, traversal, links, and duplicate normalized
paths, then sort by POSIX relative path. For every file record `relative_path`,
`byte_length`, and the `sha256:`-prefixed lowercase SHA-256 of its unmodified
bytes. Serialize the manifest
as UTF-8 JSON with lexicographically sorted object keys and separators `,` and
`:` (no insignificant whitespace). The bundle digest is `sha256:` followed by
the lowercase SHA-256 of those serialized bytes.

The manifests under `fixtures/agent-skills/manifests/` are Shadow sidecars and
are deliberately outside each standards-compatible skill directory.
