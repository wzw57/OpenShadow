import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  getManagementOverview,
  probeRuntime,
  restartRuntime,
  selectRuntime,
  startRuntime,
  stopRuntime,
} from "./api";
import type { ManagementOverview, RuntimeInstance } from "./types";

function message(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Management request failed.";
}

type Props = { onRuntimeChanged: () => Promise<void> };

export default function ManagementView({ onRuntimeChanged }: Props) {
  const [overview, setOverview] = useState<ManagementOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const next = await getManagementOverview();
    setOverview(next);
  }, []);

  useEffect(() => {
    refresh().catch((loadError) => setError(message(loadError))).finally(() => setLoading(false));
  }, [refresh]);

  async function operate(runtime: RuntimeInstance, operation: string, action: () => Promise<RuntimeInstance>) {
    setBusy(`${operation}:${runtime.runtime_id}`);
    setError(null);
    try {
      await action();
      await refresh();
      if (operation === "select") await onRuntimeChanged();
    } catch (operationError) {
      setError(message(operationError));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="management-view">
      <div className="management-heading">
        <div>
          <div className="eyebrow">Project management</div>
          <h2>Runtime control plane</h2>
          <p>Start, inspect, and select a configured Runtime. User work still goes through Shadow Admission.</p>
        </div>
        <button className="text-button" onClick={() => refresh().catch((loadError) => setError(message(loadError)))} disabled={loading}>Refresh</button>
      </div>
      {error && <div className="error-banner" role="alert">{error}</div>}
      {loading && <div className="welcome-card compact">Loading project status…</div>}
      {overview && (
        <>
          <div className="management-health-grid">
            <StatusCard label="API" value={String(overview.api.status ?? "unknown")} />
            <StatusCard label="Store" value={String(overview.store.status ?? "unknown")} />
            <StatusCard label="Web UI" value={String(overview.web_ui.status ?? "unknown")} />
            <StatusCard label="Active Runtime" value={overview.active_runtime_id} />
          </div>
          <div className="runtime-card-grid">
            {overview.runtimes.map((runtime) => {
              const key = runtime.runtime_id;
              const isBusy = busy?.endsWith(`:${key}`) ?? false;
              return (
                <article className={`runtime-management-card ${runtime.active ? "active" : ""}`} key={key}>
                  <div className="runtime-card-header">
                    <div>
                      <span className={`status-dot ${runtime.state.health === "unavailable" ? "offline" : "online"}`} />
                      <strong>{runtime.profile.display_name}</strong>
                    </div>
                    {runtime.active && <span className="runtime-badge">ACTIVE</span>}
                  </div>
                  <dl className="runtime-details">
                    <div><dt>Runtime ID</dt><dd>{key}</dd></div>
                    <div><dt>Target kind</dt><dd>{runtime.profile.target_kind}</dd></div>
                    <div><dt>Lifecycle</dt><dd>{runtime.state.lifecycle}</dd></div>
                    <div><dt>Health</dt><dd>{runtime.state.health}</dd></div>
                    <div><dt>Adapter</dt><dd>{runtime.profile.adapter_factory}</dd></div>
                  </dl>
                  {!runtime.profile.enabled && <div className="runtime-disabled">Disabled in the local profile</div>}
                  {runtime.state.last_error && <div className="runtime-error">{String(runtime.state.last_error.message ?? "Runtime error")}</div>}
                  <div className="runtime-card-actions">
                    <button disabled={isBusy || !runtime.profile.enabled} onClick={() => operate(runtime, "start", () => startRuntime(key))}>Start</button>
                    <button disabled={isBusy} onClick={() => operate(runtime, "stop", () => stopRuntime(key))}>Stop</button>
                    <button disabled={isBusy || !runtime.profile.enabled} onClick={() => operate(runtime, "restart", () => restartRuntime(key))}>Restart</button>
                    <button disabled={isBusy || !runtime.profile.enabled} onClick={() => operate(runtime, "select", () => selectRuntime(key))}>Select</button>
                    <button disabled={isBusy || !runtime.profile.enabled} onClick={() => operate(runtime, "probe", () => probeRuntime(key))}>Health</button>
                  </div>
                </article>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}

function StatusCard({ label, value }: { label: string; value: string }) {
  return <div className="management-status-card"><span>{label}</span><strong>{value}</strong></div>;
}
