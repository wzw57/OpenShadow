from .adapter import CodexAgentRuntimeAdapter, CodexExecutionResult


def create_runtime_adapter() -> CodexAgentRuntimeAdapter:
    """Create the Codex adapter from the active Runtime profile environment."""
    return CodexAgentRuntimeAdapter.from_environment()


__all__ = ["CodexAgentRuntimeAdapter", "CodexExecutionResult", "create_runtime_adapter"]
