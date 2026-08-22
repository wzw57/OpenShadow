from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import new_id, sha256_digest, utc_timestamp
from shadow_kernel.models import CanonicalEnvelope

EXPORT_FORMAT = "shadow.canonical-export"
EXPORT_VERSION = "1.0.0"


def build_export_bundle(
    records: Iterable[dict[str, Any]], *, export_id: str | None = None
) -> dict[str, Any]:
    """Serialize immutable Canonical Envelopes without storage-specific fields."""
    normalized = [
        CanonicalEnvelope.model_validate(record).model_dump(mode="json", exclude_none=True)
        for record in records
    ]
    normalized.sort(key=lambda record: (record["record_id"], record["version"]))
    record_keys = [f"{record['record_id']}@{record['version']}" for record in normalized]
    if len(record_keys) != len(set(record_keys)):
        raise ShadowDomainError(
            ShadowError(
                code="shadow.export.duplicate-record",
                category="validation",
                message="Export input contains a duplicate record version.",
            )
        )
    record_digests = {
        key: sha256_digest(record) for key, record in zip(record_keys, normalized, strict=True)
    }
    manifest = {
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "records": normalized,
        "record_digests": record_digests,
    }
    return {
        **manifest,
        "export_id": export_id or new_id("export"),
        "created_at": utc_timestamp(),
        "manifest_digest": sha256_digest(manifest),
    }


def read_export_bundle(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate a portable bundle and return records ready for an Import operation."""
    if bundle.get("format") != EXPORT_FORMAT or bundle.get("version") != EXPORT_VERSION:
        raise ShadowDomainError(
            ShadowError(
                code="shadow.export.unsupported-format",
                category="validation",
                message="Export bundle format or version is not supported.",
            )
        )
    records = bundle.get("records")
    record_digests = bundle.get("record_digests")
    if not isinstance(records, list) or not isinstance(record_digests, dict):
        raise ShadowDomainError(
            ShadowError(
                code="shadow.export.invalid-bundle",
                category="validation",
                message="Export bundle is missing records or record digests.",
            )
        )
    manifest = {
        "format": bundle["format"],
        "version": bundle["version"],
        "records": records,
        "record_digests": record_digests,
    }
    if bundle.get("manifest_digest") != sha256_digest(manifest):
        raise ShadowDomainError(
            ShadowError(
                code="shadow.export.manifest-digest-mismatch",
                category="validation",
                message="Export manifest digest does not match its contents.",
            )
        )
    validated: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for record in records:
        try:
            envelope = CanonicalEnvelope.model_validate(record).model_dump(
                mode="json", exclude_none=True
            )
        except ValueError as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.export.invalid-envelope",
                    category="validation",
                    message="Export bundle contains an invalid Canonical Envelope.",
                )
            ) from exc
        key = f"{envelope['record_id']}@{envelope['version']}"
        if key in seen_keys:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.export.duplicate-record",
                    category="validation",
                    message=f"Export bundle contains duplicate record version {key}.",
                )
            )
        seen_keys.add(key)
        if record_digests.get(key) != sha256_digest(envelope):
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.export.record-digest-mismatch",
                    category="validation",
                    message=f"Export record digest mismatch for {key}.",
                )
            )
        validated.append(envelope)
    validated.sort(key=lambda record: (record["record_id"], record["version"]))
    return validated


__all__ = ["EXPORT_FORMAT", "EXPORT_VERSION", "build_export_bundle", "read_export_bundle"]
