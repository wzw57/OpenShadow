"""Tiny Kernel primitives for the OpenShadow Phase 0 implementation."""

from .admission import AdmissionResult, AdmissionService
from .commit import CommitAuthority
from .extensions import ExtensionDescriptor, ExtensionRegistry
from .models import CanonicalEnvelope, CommitBatchResult, CommitPlan
from .registry import ContractPack, ContractRegistry
from .repository import CanonicalRepository, RepositoryUnavailable
from .runtime import RuntimeAdapter

__all__ = [
    "AdmissionResult",
    "AdmissionService",
    "CanonicalEnvelope",
    "CanonicalRepository",
    "CommitAuthority",
    "CommitBatchResult",
    "CommitPlan",
    "ContractPack",
    "ContractRegistry",
    "ExtensionDescriptor",
    "ExtensionRegistry",
    "RepositoryUnavailable",
    "RuntimeAdapter",
]
