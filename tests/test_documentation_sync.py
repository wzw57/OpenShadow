from __future__ import annotations

from pathlib import Path

from shadow_server.app import create_app

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_phase2_status_and_adr_are_delivered() -> None:
    gate = _read("docs/phase2-design-gate.md")
    adr = _read("docs/adr/0005-phase2-memory-lifecycle.md")
    status = _read("docs/phase2-memory-lifecycle-status.md")
    roadmap = _read("docs/roadmap.md")

    assert "Accepted / Phase 2 首个切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "PR [#8]" in status
    assert "合并到 `main`" in status
    assert "合并到 `main`" in roadmap
    assert "phase2/memory-lifecycle` 分支实现" not in roadmap


def test_phase3_and_phase4_status_do_not_drift() -> None:
    phase3 = _read("docs/phase3-state-profile-status.md")
    roadmap = _read("docs/roadmap.md")
    assert "已实现 / 已合并" in phase3
    assert "已实现 / 已合并前收口" not in phase3
    assert "完成并合并 Action 生命周期首片" in roadmap
    assert "进入合并收口" not in roadmap


def test_phase4_outbox_design_gate_precedes_implementation() -> None:
    gate = _read("docs/phase4-outbox-design-gate.md")
    adr = _read("docs/adr/0016-phase4-durable-outbox.md")
    status = _read("docs/phase4-outbox-status.md")
    schema = _read("contracts/schemas/outbox/1.0.0/schema.json")
    index = _read("docs/adr/README.md")
    sync = _read("docs/documentation-sync.md")

    assert "Accepted / Phase 4 Durable Outbox 获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "已实现 / 已合并" in status
    assert "OutboxIntentPayload" in schema
    assert "ADR-0016" in index
    assert "phase4-outbox-design-gate.md" in sync
    assert "不新增数据库表" in gate
    assert "通用 Queue" in gate
    assert "Event Bus" in gate
    assert "`OutboxService`" in status


def test_phase4_outbox_implementation_surface_is_documented() -> None:
    source = _read("packages/shadow-application/src/shadow_application/outbox.py")
    adapter = _read("adapters/test-deterministic/src/shadow_adapters/outbox.py")
    status = _read("docs/phase4-outbox-status.md")
    for symbol in (
        "class OutboxIntentCandidate",
        "class OutboxService",
        "def propose_intent",
        "def lease_intent",
        "def record_delivery_result",
        "def reconcile_unknown",
    ):
        assert symbol in source
    assert "class DeterministicOutboxAdapter" in adapter
    assert "Commit/CAS" in status


def test_phase4_router_policy_gate_precedes_implementation() -> None:
    gate = _read("docs/phase4-router-policy-design-gate.md")
    adr = _read("docs/adr/0017-phase4-router-policy.md")
    status = _read("docs/phase4-router-policy-status.md")
    schema = _read("contracts/schemas/routing/1.0.0/schema.json")
    index = _read("docs/adr/README.md")
    sync = _read("docs/documentation-sync.md")

    assert "Accepted / Phase 4 Router/Policy 获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "已实现 / 已合并" in status
    assert "PolicyDecision" in schema
    assert "BindingProposal" in schema
    assert "ADR-0017" in index
    assert "phase4-router-policy-design-gate.md" in sync
    assert "不能签发 Capability" in gate
    assert "`target_kind` 保持 namespaced" in gate
    assert "RoutingPolicyService" in status


def test_phase4_router_policy_implementation_surface_is_documented() -> None:
    source = _read("packages/shadow-application/src/shadow_application/routing.py")
    adapter = _read("adapters/test-deterministic/src/shadow_adapters/routing.py")
    status = _read("docs/phase4-router-policy-status.md")
    for symbol in (
        "class PolicyDecisionResult",
        "class BindingProposalResult",
        "class RoutingPolicyService",
        "def evaluate_policy",
        "def propose_binding",
        "def accept_binding",
    ):
        assert symbol in source
    assert "class DeterministicPolicyEngine" in adapter
    assert "class DeterministicRouterAdapter" in adapter
    assert "AdapterRegistry" in status


def test_next_phase2_slice_is_accepted_before_implementation() -> None:
    gate = _read("docs/phase2-recall-maintenance-design-gate.md")
    adr = _read("docs/adr/0006-phase2-recall-maintenance.md")
    status = _read("docs/phase2-memory-lifecycle-status.md")

    assert "Accepted / Phase 2 第二切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "已 Accepted；实现范围和验收证据见" in status
    assert "不新增 HTTP 路由" in gate
    assert "数据库表" in gate


def test_phase2_service_surface_is_documented() -> None:
    source = _read("packages/shadow-application/src/shadow_application/memory.py")
    status = _read("docs/phase2-memory-lifecycle-status.md")

    for method_name in (
        "propose_correction",
        "commit_correction",
        "propose_merge",
        "commit_merge",
        "logical_delete",
    ):
        assert f"def {method_name}(" in source

    for documented_name in (
        "MemoryService.propose_correction",
        "MemoryService.commit_correction",
        "propose_merge` / `commit_merge",
        "logical_delete",
    ):
        assert documented_name in status


def test_recall_maintenance_surface_is_documented() -> None:
    source = _read("packages/shadow-application/src/shadow_application/recall.py")
    status = _read("docs/phase2-recall-maintenance-status.md")

    for symbol in (
        "class MemoryRecallQuery",
        "class MemoryRecallResult",
        "class MemoryRecallService",
        "class MemoryMaintenanceRequest",
        "class MemoryMaintenanceResult",
        "class MemoryMaintenanceService",
    ):
        assert symbol in source
    for documented_name in (
        "MemoryRecallQuery",
        "MemoryRecallResult",
        "MemoryRecallService",
        "MemoryMaintenanceService",
        "DeterministicMemoryRecallAdapter",
        "DeterministicMemoryMaintenanceAdapter",
    ):
        assert documented_name in status
    assert "不新增 HTTP 路由、数据库表" in status


def test_derived_index_rebuild_gate_and_status_are_documented() -> None:
    gate = _read("docs/phase2-derived-index-design-gate.md")
    adr = _read("docs/adr/0007-phase2-derived-index-rebuild.md")
    status = _read("docs/phase2-derived-index-status.md")
    application_source = _read("packages/shadow-application/src/shadow_application/index.py")

    assert "Accepted / Phase 2 第三切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "MemoryIndexRebuildRequest" in status
    assert "MemoryIndexRebuildService" in status
    assert "创建" in gate
    assert "phase2/derived-index-rebuild" in gate
    assert "不新增公开 HTTP" in gate
    assert "数据库表" in status
    assert "class MemoryIndexRebuildService" in application_source


def test_derived_index_status_is_linked_from_recall_status() -> None:
    status = _read("docs/phase2-recall-maintenance-status.md")

    assert "第三切片状态" in status
    assert "phase2-derived-index-status.md" in status


def test_source_invalidation_gate_and_status_are_documented() -> None:
    gate = _read("docs/phase2-source-invalidation-design-gate.md")
    adr = _read("docs/adr/0008-phase2-source-dependent-invalidation.md")
    status = _read("docs/phase2-source-invalidation-status.md")
    recall_status = _read("docs/phase2-recall-maintenance-status.md")
    application_source = _read("packages/shadow-application/src/shadow_application/invalidation.py")

    assert "Accepted / Phase 2 第四切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "MemorySourceInvalidationRequest" in status
    assert "MemorySourceInvalidationService" in status
    assert "第四切片状态" in recall_status
    assert "memory_state=invalidated" in gate
    assert "不新增公开 HTTP" in gate
    assert "数据库表" in gate
    assert "class MemorySourceInvalidationService" in application_source


def test_skillasset_gate_and_adr_are_accepted_before_implementation() -> None:
    gate = _read("docs/phase2-skillasset-design-gate.md")
    adr = _read("docs/adr/0009-phase2-skillasset-sidecar.md")
    index = _read("docs/adr/README.md")
    roadmap = _read("docs/roadmap.md")

    assert "Accepted / Phase 2 第五切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "shadow.profile.skill-asset" in gate
    assert "shadow.skill-bundle-digest.v1" in gate
    assert "不新增" in gate
    assert "ADR-0009" in index
    assert "SkillAsset sidecar 第五切片已按" in roadmap


def test_skillasset_implementation_surface_and_status_are_documented() -> None:
    source = _read("packages/shadow-application/src/shadow_application/skillasset.py")
    status = _read("docs/phase2-skillasset-status.md")
    gate = _read("docs/phase2-skillasset-design-gate.md")

    for symbol in (
        "class SkillAssetRegistrationRequest",
        "class SkillAssetRegistrationResult",
        "class SkillAssetService",
        "def skill_bundle_manifest",
        "def skill_bundle_digest",
    ):
        assert symbol in source
    assert "已实现 / 已合并" in status
    assert "SkillAsset" in gate
    assert "HTTP" in status
    assert "数据库表" in status


def test_integration_gate_and_contract_are_accepted_before_implementation() -> None:
    gate = _read("docs/phase2-integration-design-gate.md")
    adr = _read("docs/adr/0010-phase2-integration-profile.md")
    schema = _read("contracts/schemas/integrations/1.0.0/schema.json")
    index = _read("docs/adr/README.md")

    assert "Accepted / Phase 2 第六切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "shadow.profile.integration" in gate
    assert "secret_refs" in gate
    assert "IntegrationPayload" in schema
    assert "ADR-0010" in index
    assert "不读取 Secret" in gate


def test_integration_implementation_surface_and_status_are_documented() -> None:
    source = _read("packages/shadow-application/src/shadow_application/integration.py")
    gate = _read("docs/phase2-integration-design-gate.md")
    status = _read("docs/phase2-integration-status.md")

    for symbol in (
        "class IntegrationRegistrationRequest",
        "class IntegrationRegistrationResult",
        "class IntegrationService",
        "def integration_result_digest",
    ):
        assert symbol in source
    assert "已实现 / 已合并" in status
    assert "secret_refs" in status
    assert "不读取 Secret" in gate
    assert "HTTP" in status


def test_portable_import_gate_and_adr_are_accepted_before_implementation() -> None:
    gate = _read("docs/phase2-portable-import-design-gate.md")
    adr = _read("docs/adr/0011-phase2-portable-import-restore.md")
    phase2 = _read("docs/phase2-design-gate.md")
    index = _read("docs/adr/README.md")

    assert "Accepted / Phase 2 第七切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "identity_mode" in gate
    assert "每个 `record_id` 必须至多包含一个 version" in gate
    assert "Tombstone" in gate
    assert "ADR-0011" in index
    assert "Portable Import/restore 第七切片" in phase2


def test_portable_import_implementation_surface_and_status_are_documented() -> None:
    source = _read("packages/shadow-application/src/shadow_application/portable_import.py")
    status = _read("docs/phase2-portable-import-status.md")
    gate = _read("docs/phase2-portable-import-design-gate.md")

    for symbol in (
        "class PortableImportRequest",
        "class PortableImportResult",
        "class PortableImportService",
        "def portable_import_result_digest",
    ):
        assert symbol in source
    assert "已实现 / 已合并" in status
    assert "Tombstone" in status
    assert "HTTP" in status
    assert "identity_mode" in gate


def test_physical_erase_gate_and_adr_are_accepted_before_implementation() -> None:
    gate = _read("docs/phase2-physical-erase-design-gate.md")
    adr = _read("docs/adr/0012-phase2-physical-erase-tombstone.md")
    phase2 = _read("docs/phase2-design-gate.md")
    index = _read("docs/adr/README.md")

    assert "Accepted / Phase 2 第八切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "quiesce" in gate
    assert "Tombstone" in gate
    assert "purge" in gate
    assert "ADR-0012" in index
    assert "ADR-0012" in phase2


def test_physical_erase_implementation_surface_and_status_are_documented() -> None:
    source = _read("packages/shadow-application/src/shadow_application/erase.py")
    adapter = _read("adapters/test-deterministic/src/shadow_adapters/erase.py")
    status = _read("docs/phase2-physical-erase-status.md")
    gate = _read("docs/phase2-physical-erase-design-gate.md")

    for symbol in (
        "class PhysicalEraseRequest",
        "class PhysicalEraseResult",
        "class PhysicalEraseService",
        "class ErasureAdapter",
        "def physical_erase_result_digest",
    ):
        assert symbol in source
    assert "class DeterministicErasureAdapter" in adapter
    assert "已实现 / 已合并" in status
    assert "Tombstone" in status
    assert "HTTP" in status
    assert "quiesce" in gate


def test_phase3_state_design_gate_and_contract_are_synchronized() -> None:
    gate = _read("docs/phase3-design-gate.md")
    adr = _read("docs/adr/0013-phase3-state-profile-lifecycle.md")
    status = _read("docs/phase3-state-profile-status.md")
    schema = _read("contracts/schemas/state/1.0.0/schema.json")
    openapi = _read("contracts/openapi/openapi.yaml")
    roadmap = _read("docs/roadmap.md")

    assert "Accepted / Phase 3 首个 State 切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "已实现 / 已合并" in status
    assert "shadow.profile.state" in gate
    assert "StateProposalPayload" in schema
    assert "/v1/states" in openapi
    assert "POST /v1/proposals" in gate
    assert "ADR-0013" in roadmap
    assert "不新增数据库表" in gate


def test_phase3_state_implementation_surface_and_api_are_documented() -> None:
    source = _read("packages/shadow-application/src/shadow_application/state.py")
    adapter = _read("adapters/test-deterministic/src/shadow_adapters/state.py")
    status = _read("docs/phase3-state-profile-status.md")
    app_source = _read("apps/shadow-server/shadow_server/app.py")

    for symbol in (
        "class StateService",
        "class StateProposalCandidate",
        "def propose(",
        "def submit_proposal(",
        "def accept_proposal(",
        "def list_states(",
        "def get_state(",
        "compute_freshness",
    ):
        assert symbol in source
    assert "class DeterministicStateSourceAdapter" in adapter
    assert "已实现 / 已合并" in status
    assert '"/v1/states"' in app_source
    assert '"/v1/proposals"' in app_source
    runtime_schema = create_app("sqlite://").openapi()
    for path, method in (
        ("/v1/states", "get"),
        ("/v1/states/{state_id}", "get"),
        ("/v1/proposals", "post"),
        ("/v1/proposals/{proposal_id}/accept", "post"),
    ):
        assert path in runtime_schema["paths"]
        assert method in runtime_schema["paths"][path]
        assert path in _read("contracts/openapi/openapi.yaml")


def test_phase3_completion_gate_is_accepted_before_remaining_implementation() -> None:
    gate = _read("docs/phase3-completion-design-gate.md")
    adr = _read("docs/adr/0014-phase3-continuity-completion.md")
    status = _read("docs/phase3-completion-status.md")
    schema = _read("contracts/schemas/continuity/1.0.0/schema.json")
    index = _read("docs/adr/README.md")

    assert "Accepted / Phase 3 全部剩余切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "已实现 / 已合并" in status
    assert "TaskPayload" in schema
    assert "CheckpointPayload" in schema
    assert "IntegrityManifest" in schema
    assert "ADR-0014" in index
    assert "不新增数据库表" in gate


def test_phase3_completion_implementation_surface_and_status_are_documented() -> None:
    task_source = _read("packages/shadow-application/src/shadow_application/task.py")
    continuity_source = _read("packages/shadow-application/src/shadow_application/continuity.py")
    app_source = _read("apps/shadow-server/shadow_server/app.py")
    status = _read("docs/phase3-completion-status.md")
    openapi = _read("contracts/openapi/openapi.yaml")
    runtime_schema = create_app("sqlite://").openapi()

    for symbol in ("class TaskService", "class TaskProposalCandidate", "def create_checkpoint", "def accept_proposal", "def link_run"):
        assert symbol in task_source
    for symbol in ("class DeterministicClock", "class DeterministicScheduleAdapter", "class StateConditionAdmission", "class IntegrityService", "class DeterministicMigrationAdapter"):
        assert symbol in continuity_source
    assert "已实现 / 已合并" in status
    assert '"/v1/tasks"' in app_source
    assert '"/v1/tasks/{task_id}/checkpoints"' in app_source
    for path, method in (
        ("/v1/tasks", "get"),
        ("/v1/tasks/{task_id}", "get"),
        ("/v1/tasks/{task_id}/checkpoints", "post"),
        ("/v1/tasks/{task_id}/completion", "post"),
    ):
        assert path in runtime_schema["paths"]
        assert method in runtime_schema["paths"][path]
        assert path in openapi


def test_phase4_action_design_gate_and_contract_are_synchronized() -> None:
    gate = _read("docs/phase4-design-gate.md")
    adr = _read("docs/adr/0015-phase4-action-lifecycle.md")
    status = _read("docs/phase4-action-status.md")
    schema = _read("contracts/schemas/action/1.0.0/schema.json")
    openapi = _read("contracts/openapi/openapi.yaml")
    roadmap = _read("docs/roadmap.md")

    assert "Accepted / Phase 4 首个 Action 生命周期切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "已实现 / 已合并" in status
    for definition in (
        "ActionPayload",
        "ActionProposalPayload",
        "ApprovalProposalPayload",
        "ProviderResultPayload",
        "ReconciliationPayload",
    ):
        assert definition in schema
    assert "ActionProposalCommand" in openapi
    assert "ActionApprovalProposalCommand" in openapi
    assert "/v1/actions" in openapi
    assert "/v1/actions/{action_id}" in openapi
    assert "ADR-0015" in roadmap
    assert "不新增数据库表" in gate


def test_phase4_action_implementation_surface_and_api_are_documented() -> None:
    source = _read("packages/shadow-application/src/shadow_application/action.py")
    adapter = _read("adapters/test-deterministic/src/shadow_adapters/action.py")
    app_source = _read("apps/shadow-server/shadow_server/app.py")
    status = _read("docs/phase4-action-status.md")
    openapi = _read("contracts/openapi/openapi.yaml")
    runtime_schema = create_app("sqlite://").openapi()

    for symbol in (
        "class ActionService",
        "class ActionProposalCandidate",
        "def propose_action(",
        "def propose_approval(",
        "def begin_execution(",
        "def record_provider_result(",
        "def reconcile_unknown(",
        "def list_actions(",
        "def get_action(",
    ):
        assert symbol in source
    assert "class DeterministicActionProvider" in adapter
    assert "已实现 / 已合并" in status
    assert '"/v1/actions"' in app_source
    assert '"/v1/proposals"' in app_source
    for path, method in (
        ("/v1/actions", "get"),
        ("/v1/actions/{action_id}", "get"),
        ("/v1/proposals", "post"),
        ("/v1/proposals/{proposal_id}/accept", "post"),
    ):
        assert path in runtime_schema["paths"]
        assert method in runtime_schema["paths"][path]
        assert path in openapi


def test_phase2_http_contract_matches_app_and_static_openapi() -> None:
    app_source = _read("apps/shadow-server/shadow_server/app.py")
    openapi_source = _read("contracts/openapi/openapi.yaml")
    status = _read("docs/phase2-memory-lifecycle-status.md")
    schema = create_app("sqlite://").openapi()
    required_headers = {
        "Expected-Version",
        "idempotency-key",
        "X-Principal-Ref",
        "X-Space-Id",
    }

    for path, method in (
        ("/v1/memories/{memory_id}/corrections", "post"),
        ("/v1/memories/{memory_id}", "delete"),
    ):
        assert path in schema["paths"]
        params = {
            parameter["name"]: parameter
            for parameter in schema["paths"][path][method]["parameters"]
            if parameter["in"] == "header"
        }
        assert required_headers <= params.keys()
        assert all(params[name]["required"] for name in required_headers)
        assert path in openapi_source

    for header in ("Expected-Version", "X-Principal-Ref", "X-Space-Id"):
        assert f"name: {header}" in openapi_source
    assert "name: Idempotency-Key" in openapi_source
    assert "/v1/memories/merges" not in app_source
    assert "/v1/memories/merges" not in openapi_source
    assert "merge 保持 Application / Contract" in status
