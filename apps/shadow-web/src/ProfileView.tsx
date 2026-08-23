import type { CanonicalRecord, ProfileKind } from "./types";

type ProfileViewProps = {
  kind: ProfileKind;
  records: CanonicalRecord[];
  loading: boolean;
  refreshing: boolean;
  onRefresh: () => void;
};

const PROFILE_LABELS: Record<ProfileKind, string> = {
  memories: "Memories",
  states: "States",
  tasks: "Tasks",
  actions: "Actions",
};

function payload(record: CanonicalRecord): Record<string, unknown> {
  return record.typed_payload ?? {};
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function profileTitle(kind: ProfileKind, record: CanonicalRecord): string {
  const data = payload(record);
  const field = {
    memories: "memory_kind",
    states: "state_key",
    tasks: "task_key",
    actions: "action_kind",
  }[kind];
  return stringValue(data[field]) ?? PROFILE_LABELS[kind].slice(0, -1);
}

function profileStatus(kind: ProfileKind, record: CanonicalRecord): string | null {
  const data = payload(record);
  const fields = {
    memories: ["memory_state", "record_state"],
    states: ["freshness", "source_status"],
    tasks: ["lifecycle", "task_state"],
    actions: ["lifecycle", "action_state", "side_effect_level"],
  }[kind];
  for (const field of fields) {
    const value = stringValue(data[field]);
    if (value) return value.replaceAll("_", " ");
  }
  return null;
}

function profileSummary(kind: ProfileKind, record: CanonicalRecord): string {
  const data = payload(record);
  const candidates = {
    memories: [data.typed_content, data.memory_summary],
    states: [data.typed_value, data.proposed_value],
    tasks: [data.goal, data.completion_criteria],
    actions: [data.target_ref, data.typed_parameters],
  }[kind];
  const value = candidates.find((candidate) => candidate !== undefined && candidate !== null);
  if (typeof value === "string") return value;
  if (value && typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return "Structured value";
    }
  }
  return "No summary available";
}

function prettyPayload(record: CanonicalRecord): string {
  try {
    return JSON.stringify(record.typed_payload ?? {}, null, 2);
  } catch {
    return "Unable to render payload";
  }
}

function formatDate(value?: string): string {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? ""
    : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export default function ProfileView({
  kind,
  records,
  loading,
  refreshing,
  onRefresh,
}: ProfileViewProps) {
  return (
    <section className="profile-view" aria-live="polite">
      <div className="profile-toolbar">
        <div>
          <p>{records.length} active record{records.length === 1 ? "" : "s"}</p>
          <span>Read-only view · canonical heads</span>
        </div>
        <button className="text-button" onClick={onRefresh} disabled={loading || refreshing}>
          {refreshing || loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {loading && <div className="profile-empty">Loading {PROFILE_LABELS[kind].toLowerCase()}…</div>}
      {!loading && records.length === 0 && (
        <div className="profile-empty">
          <div className="welcome-orb">✦</div>
          <h2>No {PROFILE_LABELS[kind].toLowerCase()} yet.</h2>
          <p>Records created through the Shadow API will appear here.</p>
        </div>
      )}

      {!loading && records.length > 0 && (
        <div className="profile-list">
          {records.map((record) => {
            const status = profileStatus(kind, record);
            return (
              <details className="profile-card" key={`${record.record_id}:${record.version}`}>
                <summary>
                  <span className="profile-card-heading">
                    <strong>{profileTitle(kind, record)}</strong>
                    <small>{record.record_id}</small>
                  </span>
                  <span className="profile-card-meta">
                    {status && <em>{status}</em>}
                    <span>v{record.version}</span>
                  </span>
                </summary>
                <div className="profile-card-body">
                  <p className="profile-summary">{profileSummary(kind, record)}</p>
                  <div className="profile-card-facts">
                    <span>Version {record.version}</span>
                    {formatDate(record.committed_at ?? record.created_at) && (
                      <span>{formatDate(record.committed_at ?? record.created_at)}</span>
                    )}
                  </div>
                  <pre>{prettyPayload(record)}</pre>
                </div>
              </details>
            );
          })}
        </div>
      )}
    </section>
  );
}

export { PROFILE_LABELS };
