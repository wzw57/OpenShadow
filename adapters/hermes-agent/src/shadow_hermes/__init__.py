from .adapter import HermesAgentRuntimeAdapter, HermesExecutionResult


def create_runtime_adapter() -> HermesAgentRuntimeAdapter:
    """Create the generic RuntimeAdapter implementation from deployment settings."""

    return HermesAgentRuntimeAdapter.from_environment()


__all__ = ["HermesAgentRuntimeAdapter", "HermesExecutionResult", "create_runtime_adapter"]
