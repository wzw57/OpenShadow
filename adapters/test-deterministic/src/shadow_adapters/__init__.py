from .action import DeterministicActionProvider
from .deterministic import DeterministicTestAdapter, ExecutionResult
from .erase import DeterministicErasureAdapter
from .erasure_backup import DeterministicCrossComponentErasureAdapter
from .index import DeterministicMemoryIndexAdapter
from .memory import DeterministicMemoryMaintenanceAdapter, DeterministicMemoryRecallAdapter
from .outbox import DeterministicOutboxAdapter
from .pulse import DeterministicSemanticPulseAdapter
from .routing import DeterministicPolicyEngine, DeterministicRouterAdapter
from .state import DeterministicStateSourceAdapter


def create_runtime_adapter() -> DeterministicTestAdapter:
    """Return the default RuntimeAdapter for the local management profile."""
    return DeterministicTestAdapter()

__all__ = [
    "DeterministicMemoryMaintenanceAdapter",
    "DeterministicMemoryIndexAdapter",
    "DeterministicMemoryRecallAdapter",
    "DeterministicErasureAdapter",
    "DeterministicTestAdapter",
    "create_runtime_adapter",
    "ExecutionResult",
    "DeterministicStateSourceAdapter",
    "DeterministicActionProvider",
    "DeterministicOutboxAdapter",
    "DeterministicPolicyEngine",
    "DeterministicRouterAdapter",
    "DeterministicSemanticPulseAdapter",
    "DeterministicCrossComponentErasureAdapter",
]
