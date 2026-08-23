import { useEffect, useMemo, useState } from "react";
import {
  ApiError,
  PRINCIPAL_REF,
  acceptProposal,
  completeTask,
  correctMemory,
  createCheckpoint,
  createMemory,
  deleteMemory,
  submitProposal,
} from "./api";
import type { CanonicalRecord, ProfileKind } from "./types";

type OperationMode = "create" | "update" | "delete" | "completion_pending" | "complete" | "checkpoint" | "approve" | "reject";

type ProfileActionsProps = {
  kind: ProfileKind;
  records: CanonicalRecord[];
  onChanged: () => Promise<void>;
};

function nowPlus(hours: number): string {
  return new Date(Date.now() + hours * 60 * 60 * 1000).toISOString();
}

function errorText(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "The operation could not be completed.";
}

function parseObject(value: string, label: string): Record<string, unknown> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new Error(`${label} must be valid JSON.`);
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON object.`);
  }
  return parsed as Record<string, unknown>;
}

function targetLabel(record: CanonicalRecord): string {
  return `${record.record_id.slice(0, 20)} · v${record.version}`;
}

export default function ProfileActions({ kind, records, onChanged }: ProfileActionsProps) {
  const [mode, setMode] = useState<OperationMode>("create");
  const [targetId, setTargetId] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [memoryKind, setMemoryKind] = useState("shadow.memory.note");
  const [memoryText, setMemoryText] = useState("");
  const [memoryScope, setMemoryScope] = useState('{"scope_kind":"shadow.scope.personal","scope_refs":[]}');

  const [stateKey, setStateKey] = useState("profile.note");
  const [stateValue, setStateValue] = useState("");
  const [stateSchema, setStateSchema] = useState("schema:text");
  const [observedAt, setObservedAt] = useState(() => new Date().toISOString());
  const [expiresAt, setExpiresAt] = useState(() => nowPlus(24));

  const [taskKey, setTaskKey] = useState("task-new");
  const [taskGoal, setTaskGoal] = useState("");
  const [taskCriteria, setTaskCriteria] = useState('{"kind":"manual"}');
  const [resultRef, setResultRef] = useState("{}");
  const [checkpointDigest, setCheckpointDigest] = useState("");

  const [actionKind, setActionKind] = useState("shadow.action.send-notification");
  const [actionTarget, setActionTarget] = useState('{"record_id":"target-local","resource_kind":"notification"}');
  const [actionParameters, setActionParameters] = useState("{}");
  const [dataClassification, setDataClassification] = useState("personal");
  const [sideEffectLevel, setSideEffectLevel] = useState("none");
  const [capabilities, setCapabilities] = useState("[]");
  const [deadline, setDeadline] = useState(() => nowPlus(1));
  const [secretRefs, setSecretRefs] = useState("[]");
  const [approvalEvidence, setApprovalEvidence] = useState("[]");

  const target = useMemo(
    () => records.find((record) => record.record_id === targetId) ?? null,
    [records, targetId],
  );

  useEffect(() => {
    setMode("create");
    setTargetId(records[0]?.record_id ?? "");
    setNotice(null);
    setError(null);
  }, [kind, records]);

  const options: Array<{ value: OperationMode; label: string }> =
    kind === "memories"
      ? [
          { value: "create", label: "Create memory" },
          { value: "update", label: "Correct selected" },
          { value: "delete", label: "Logically delete selected" },
        ]
      : kind === "states"
        ? [
            { value: "create", label: "Create state" },
            { value: "update", label: "Update selected" },
            { value: "delete", label: "Logically delete selected" },
          ]
        : kind === "tasks"
          ? [
              { value: "create", label: "Create task" },
              { value: "completion_pending", label: "Request completion" },
              { value: "complete", label: "Complete selected" },
              { value: "checkpoint", label: "Checkpoint selected" },
            ]
          : [
              { value: "create", label: "Propose action" },
              { value: "approve", label: "Approve selected" },
              { value: "reject", label: "Reject selected" },
            ];

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setNotice(null);
    setError(null);
    try {
      if (kind === "memories") {
        const command = {
          memory_kind: memoryKind,
          content_schema_ref: "https://schemas.openshadow.dev/content/text/1.0.0",
          typed_content: { text: memoryText },
          applicability_scope: parseObject(memoryScope, "Applicability scope"),
          evidence_refs: [],
          source_dependency: "independent",
        };
        if (mode === "create") await createMemory(command);
        else if (target && mode === "update") await correctMemory(target.record_id, target.version, command);
        else if (target && mode === "delete") {
          if (!window.confirm("Logically delete this Memory?")) return;
          await deleteMemory(target.record_id, target.version);
        }
        await onChanged();
        setNotice("Memory change committed.");
      } else if (kind === "states") {
        const operation = mode === "create" ? "create" : mode === "update" ? "update" : "logical_delete";
        const command: Record<string, unknown> = {
          input_type: "shadow.state-proposal",
          proposed_operation: operation,
          state_key: stateKey,
          value_schema_ref: stateSchema,
          proposed_value: stateValue,
          evidence_refs: [],
          source_refs: [],
          observed_at: observedAt,
          expires_at: expiresAt,
          source_status: "available",
        };
        if (mode !== "create" && target) {
          command.target_ref = { record_id: target.record_id };
          command.expected_version = target.version;
        }
        const proposal = await submitProposal(command);
        await acceptProposal(proposal.record_id, proposal.version);
        await onChanged();
        setNotice("State proposal accepted.");
      } else if (kind === "tasks") {
        if (mode === "checkpoint" && target) {
          await createCheckpoint(target.record_id, target.version, {
            checkpoint_kind: "semantic",
            checkpoint_digest: checkpointDigest || `sha256:${"0".repeat(64)}`,
            runtime_target_kind: "shadow.deterministic-runner",
            runtime_capabilities: [],
            artifact_refs: [],
            native_resume: false,
          });
        } else if (mode === "complete" && target) {
          const parsedResult = parseObject(resultRef, "Result reference");
          await completeTask(
            target.record_id,
            target.version,
            Object.keys(parsedResult).length > 0 ? parsedResult : null,
          );
        } else {
          const current = target?.typed_payload ?? {};
          const proposal = await submitProposal({
            input_type: "shadow.durable-task-proposal",
            proposed_operation: mode,
            task_key: mode === "create" ? taskKey : String(current.task_key ?? taskKey),
            goal: mode === "create" ? taskGoal : String(current.goal ?? taskGoal),
            completion_criteria: mode === "create"
              ? parseObject(taskCriteria, "Completion criteria")
              : current.completion_criteria ?? parseObject(taskCriteria, "Completion criteria"),
            ...(mode === "create" ? {} : {
              target_ref: { record_id: target?.record_id },
              expected_version: target?.version,
            }),
          });
          await acceptProposal(proposal.record_id, proposal.version);
        }
        await onChanged();
        setNotice("Task change committed.");
      } else if (kind === "actions") {
        if (mode === "create") {
          const proposal = await submitProposal({
            input_type: "shadow.action-proposal",
            proposed_operation: "create",
            action_kind: actionKind,
            target_ref: parseObject(actionTarget, "Action target"),
            typed_parameters: parseObject(actionParameters, "Action parameters"),
            data_classification: dataClassification,
            side_effect_level: sideEffectLevel,
            required_capabilities: JSON.parse(capabilities),
            deadline,
            secret_refs: JSON.parse(secretRefs),
          });
          await acceptProposal(proposal.record_id, proposal.version);
        } else if (target) {
          const decision = mode === "approve" ? "approved" : "rejected";
          const proposal = await submitProposal({
            input_type: "shadow.action-approval-proposal",
            proposed_operation: decision === "approved" ? "approve" : "reject",
            action_ref: { record_id: target.record_id },
            expected_version: target.version,
            approver_ref: PRINCIPAL_REF,
            decision,
            evidence_refs: JSON.parse(approvalEvidence),
          });
          await acceptProposal(proposal.record_id, proposal.version);
        }
        await onChanged();
        setNotice("Action proposal committed.");
      }
    } catch (operationError) {
      setError(errorText(operationError));
    } finally {
      setBusy(false);
    }
  }

  const requiresTarget = mode !== "create";
  return (
    <section className="profile-actions" aria-label="Profile operations">
      <div className="profile-actions-heading">
        <div>
          <strong>Controlled operation</strong>
          <span>Uses the existing Proposal / Commit boundary.</span>
        </div>
        <select value={mode} onChange={(event) => setMode(event.target.value as OperationMode)}>
          {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      </div>
      {requiresTarget && (
        <label className="profile-field">
          <span>Target record</span>
          <select value={targetId} onChange={(event) => setTargetId(event.target.value)} disabled={records.length === 0}>
            {records.length === 0 && <option value="">No active records</option>}
            {records.map((record) => <option key={record.record_id} value={record.record_id}>{targetLabel(record)}</option>)}
          </select>
        </label>
      )}
      <form className="profile-form" onSubmit={handleSubmit}>
        {kind === "memories" && (mode === "create" || mode === "update") && (
          <>
            <label className="profile-field"><span>Memory kind</span><input value={memoryKind} onChange={(event) => setMemoryKind(event.target.value)} required /></label>
            <label className="profile-field"><span>Text content</span><textarea value={memoryText} onChange={(event) => setMemoryText(event.target.value)} required rows={3} /></label>
            <label className="profile-field"><span>Applicability scope (JSON)</span><textarea value={memoryScope} onChange={(event) => setMemoryScope(event.target.value)} rows={2} /></label>
          </>
        )}
        {kind === "states" && (
          <>
            <label className="profile-field"><span>State key</span><input value={stateKey} onChange={(event) => setStateKey(event.target.value)} required /></label>
            {mode !== "delete" && <label className="profile-field"><span>Value</span><input value={stateValue} onChange={(event) => setStateValue(event.target.value)} required /></label>}
            <label className="profile-field"><span>Value schema ref</span><input value={stateSchema} onChange={(event) => setStateSchema(event.target.value)} required /></label>
            {mode !== "delete" && <div className="profile-field-grid"><label className="profile-field"><span>Observed at</span><input value={observedAt} onChange={(event) => setObservedAt(event.target.value)} required /></label><label className="profile-field"><span>Expires at</span><input value={expiresAt} onChange={(event) => setExpiresAt(event.target.value)} required /></label></div>}
          </>
        )}
        {kind === "tasks" && (mode === "create" || mode === "completion_pending") && (
          <>
            {mode === "create" && <label className="profile-field"><span>Task key</span><input value={taskKey} onChange={(event) => setTaskKey(event.target.value)} required /></label>}
            {mode === "create" && <label className="profile-field"><span>Goal</span><textarea value={taskGoal} onChange={(event) => setTaskGoal(event.target.value)} required rows={2} /></label>}
            {mode === "create" && <label className="profile-field"><span>Completion criteria (JSON)</span><textarea value={taskCriteria} onChange={(event) => setTaskCriteria(event.target.value)} rows={2} /></label>}
          </>
        )}
        {kind === "tasks" && mode === "complete" && <label className="profile-field"><span>Result reference (JSON)</span><textarea value={resultRef} onChange={(event) => setResultRef(event.target.value)} rows={2} /></label>}
        {kind === "tasks" && mode === "checkpoint" && <label className="profile-field"><span>Checkpoint digest</span><input value={checkpointDigest} onChange={(event) => setCheckpointDigest(event.target.value)} placeholder="sha256:…" /></label>}
        {kind === "actions" && mode === "create" && (
          <>
            <div className="profile-field-grid"><label className="profile-field"><span>Action kind</span><input value={actionKind} onChange={(event) => setActionKind(event.target.value)} required /></label><label className="profile-field"><span>Side effect</span><select value={sideEffectLevel} onChange={(event) => setSideEffectLevel(event.target.value)}><option value="none">none</option><option value="low">low</option><option value="medium">medium</option><option value="high">high</option></select></label></div>
            <label className="profile-field"><span>Target (JSON)</span><textarea value={actionTarget} onChange={(event) => setActionTarget(event.target.value)} rows={2} /></label>
            <label className="profile-field"><span>Parameters (JSON)</span><textarea value={actionParameters} onChange={(event) => setActionParameters(event.target.value)} rows={2} /></label>
            <div className="profile-field-grid"><label className="profile-field"><span>Classification</span><input value={dataClassification} onChange={(event) => setDataClassification(event.target.value)} required /></label><label className="profile-field"><span>Deadline</span><input value={deadline} onChange={(event) => setDeadline(event.target.value)} required /></label></div>
            <label className="profile-field"><span>Capabilities (JSON array)</span><input value={capabilities} onChange={(event) => setCapabilities(event.target.value)} /></label>
            <label className="profile-field"><span>Secret references (JSON array only)</span><input value={secretRefs} onChange={(event) => setSecretRefs(event.target.value)} /></label>
          </>
        )}
        {kind === "actions" && mode !== "create" && <label className="profile-field"><span>Evidence (JSON array)</span><textarea value={approvalEvidence} onChange={(event) => setApprovalEvidence(event.target.value)} rows={2} /></label>}
        <div className="profile-form-footer">
          {notice && <span className="profile-notice">{notice}</span>}
          {error && <span className="profile-form-error">{error}</span>}
          <button className="send-button" disabled={busy || (requiresTarget && !target)}>{busy ? "Committing…" : "Commit"}</button>
        </div>
      </form>
    </section>
  );
}
