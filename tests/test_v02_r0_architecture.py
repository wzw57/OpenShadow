from __future__ import annotations

import ast
from pathlib import Path

from fastapi.testclient import TestClient
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import CommitOperation, CommitPlan, Provenance, StableRecordRef
from shadow_server.app import create_app

from tests.v02_fixtures.example_profile_extension import ExampleProfileExtension
from tests.v02_fixtures.example_runtime_extension import (
    ExampleExecutionRequest,
    ExampleRuntimeExtension,
)

ROOT = Path(__file__).resolve().parents[1]


def _python_files(relative_root: str) -> list[Path]:
    return sorted((ROOT / relative_root).rglob("*.py"))


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_kernel_has_no_reverse_or_vendor_imports() -> None:
    forbidden_prefixes = (
        "shadow_application",
        "shadow_adapters",
        "shadow_hermes",
        "shadow_codex",
        "shadow_server",
        "shadow_store",
    )
    violations: list[str] = []
    for path in _python_files("packages/shadow-kernel/src/shadow_kernel"):
        for module in _imported_modules(path):
            if module == forbidden_prefixes or module.startswith(forbidden_prefixes):
                violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert not violations, "Kernel dependency boundary violated: " + ", ".join(violations)


def test_example_profile_exposes_minimal_extension_shape() -> None:
    extension = ExampleProfileExtension()
    descriptor = extension.descriptor

    assert descriptor.extension_id == "example.profile"
    assert descriptor.version
    assert descriptor.contract_packs
    assert descriptor.record_types == ("shadow.profile.example",)
    assert descriptor.input_types == ("example.profile.create",)
    intent = extension.handle_input(
        {"input_type": "example.profile.create", "label": "hello"},
        owner_ref="owner-example",
        space_id="space-example",
    )
    assert intent["record_type"] == "shadow.profile.example"
    assert intent["owner_ref"] == "owner-example"
    assert intent["space_id"] == "space-example"


def test_example_runtime_exposes_typed_request_boundary() -> None:
    runtime = ExampleRuntimeExtension()
    request = ExampleExecutionRequest(
        request_id="request-example",
        target_kind=runtime.target_kind,
        typed_input={"value": "hello"},
    )

    result = runtime.execute(request)
    assert runtime.describe()["target_kind"] == "example.runtime.v1"
    assert result.outcome == "succeeded"
    assert result.output == {"echo": {"value": "hello"}}


def test_example_profile_can_create_and_query_through_generic_api(tmp_path: Path) -> None:
    from tests.v02_fixtures.example_profile_extension import ExampleProfileExtension

    app = create_app(f"sqlite:///{(tmp_path / 'example.db').as_posix()}")

    class ExampleInputHandler:
        def submit(self, payload, *, principal_ref, space_id, idempotency_key):
            extension = ExampleProfileExtension()
            intent = extension.handle_input(
                payload, owner_ref=principal_ref, space_id=space_id
            )
            record_id = f"example-{sha256_digest({'owner': principal_ref, 'key': idempotency_key})[7:31]}"
            typed_payload = {
                "state_key": intent["typed_payload"]["label"],
                "value_schema_ref": "https://schemas.openshadow.dev/examples/example/1.0.0",
                "typed_value": intent["typed_payload"],
                "evidence_refs": [],
                "source_refs": ["example.profile"],
                "observed_at": "2026-08-22T08:00:00Z",
                "expires_at": "2099-08-22T00:00:00Z",
                "source_status": "available",
                "freshness": "fresh",
            }
            operation = CommitOperation(
                operation_id=f"operation-{record_id}",
                operation="create",
                record_id=record_id,
                record_type=intent["record_type"],
                target_schema_ref="https://schemas.openshadow.dev/contracts/state/1.0.0#/$defs/StatePayload",
                owner_ref=principal_ref,
                space_id=space_id,
                created_by=principal_ref,
                data_classification="personal",
                provenance=Provenance(
                    origin_type="shadow.origin.example-extension",
                    origin_ref=record_id,
                ),
                retention_policy_ref=StableRecordRef(record_id="retention-default"),
                typed_payload=typed_payload,
            )
            result = app.state.authority.commit(
                CommitPlan(
                    commit_request_id=f"commit-request-{record_id}",
                    idempotency_scope=f"example:{principal_ref}:{space_id}",
                    idempotency_key=idempotency_key,
                    request_digest=sha256_digest(typed_payload),
                    actor_ref=principal_ref,
                    operations=[operation],
                    prepared_at=utc_timestamp(),
                )
            )
            assert result.outcome in {"committed", "idempotent_replay"}
            return {"record": app.state.repository.get(record_id)}

    app.state.input_handlers.register("example.profile.create", ExampleInputHandler())
    client = TestClient(app)
    headers = {
        "X-Principal-Ref": "owner-example",
        "X-Space-Id": "space-example",
        "Idempotency-Key": "example-profile-input",
    }
    submitted = client.post(
        "/v1/inputs",
        json={"input_type": "example.profile.create", "label": "hello"},
        headers=headers,
    )
    assert submitted.status_code == 202, submitted.text
    record_id = submitted.json()["record"]["record_id"]
    queried = client.get(f"/v1/records/{record_id}", headers=headers)
    assert queried.status_code == 200
    assert queried.json()["record"]["record_type"] == "shadow.profile.example"


def test_example_runtime_is_discoverable_without_core_changes() -> None:
    source = (ROOT / "packages/shadow-application/src/shadow_application/runtime_management.py").read_text(
        encoding="utf-8"
    )
    assert "ExtensionRegistry" in source
    assert "register_extension" in source


def test_generic_proposal_dispatch_has_no_builtin_branches() -> None:
    source = (ROOT / "apps/shadow-server/shadow_server/app.py").read_text(encoding="utf-8")
    assert "StateProposalCommand" not in source
    assert "TaskProposalCommand" not in source
    assert "ActionProposalCommand" not in source
    assert "isinstance(command" not in source


def test_conversation_does_not_import_a_default_runtime_adapter() -> None:
    source = (ROOT / "packages/shadow-application/src/shadow_application/conversation.py").read_text(
        encoding="utf-8"
    )
    assert "from shadow_adapters import DeterministicTestAdapter" not in source
    assert "DeterministicTestAdapter()" not in source


def test_runtime_port_accepts_typed_execution_request() -> None:
    source = (ROOT / "packages/shadow-kernel/src/shadow_kernel/runtime.py").read_text(
        encoding="utf-8"
    )
    assert "ExecutionRequest" in source
    assert "def execute(self, request:" in source


def test_generic_api_routes_are_present() -> None:
    source = (ROOT / "apps/shadow-server/shadow_server/app.py").read_text(encoding="utf-8")
    assert '"/v1/extensions"' in source
    assert '"/v1/records"' in source
    assert '"/v1/inputs"' in source


def test_repository_port_keeps_optional_capabilities_out_of_the_base_protocol() -> None:
    source = (ROOT / "packages/shadow-kernel/src/shadow_kernel/repository.py").read_text(
        encoding="utf-8"
    )
    assert "class EventStoreCapability" in source
    assert "class ErasureCapability" in source
    base_port = source.split("class EventStoreCapability", 1)[0]
    assert "def erase_history" not in base_port
