# Codex Agent Runtime Adapter

This adapter invokes the installed open-source Codex CLI through the generic
`shadow.agent-runtime` boundary. It uses `codex exec --json` and parses the
JSONL stream into Shadow execution results. It does not import Codex internals,
write the Canonical Repository, or enable sandbox/approval bypass flags.
