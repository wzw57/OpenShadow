# Hermes Agent Runtime Adapter

This adapter talks to the Hermes Agent API server through its OpenAI-compatible
`/v1/chat/completions` endpoint. It is intentionally separate from the Kernel and
does not import Hermes internals or write the Canonical Repository.

The first slice supports text input, final results, usage and a local event cursor.
Hermes tools are not exposed through this adapter yet. Tool requests require a
separate Shadow Capability/Action design gate.
