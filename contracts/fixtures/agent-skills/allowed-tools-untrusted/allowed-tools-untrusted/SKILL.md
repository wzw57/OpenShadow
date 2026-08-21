---
name: allowed-tools-untrusted
description: A format-valid fixture proving that experimental allowed-tools metadata cannot grant Shadow authority.
allowed-tools: Bash(git:*) Read
---

# Untrusted tool declaration

The bundle is valid, but Shadow must deny all tools unless a separate
CapabilityEnvelope grants them for the exact bundle digest.
