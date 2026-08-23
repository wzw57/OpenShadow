import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  createConversation,
  getReady,
  getRun,
  getRunEvents,
  getRuntime,
  listSpaces,
  listProfileRecords,
  listConversations,
  listMessages,
  messageKind,
  messageText,
  recordTitle,
  retryRun,
  setApiContext,
  submitTurn,
} from "./api";
import ContextPanel from "./ContextPanel";
import ManagementView from "./ManagementView";
import ProfileView, { PROFILE_LABELS } from "./ProfileView";
import type { CanonicalRecord, Conversation, Message, ProfileKind, Run, RunEvent, RuntimeStatus, SpaceRecord } from "./types";

const TERMINAL_LIFECYCLES = new Set(["completed", "failed", "unknown", "cancelled", "canceled"]);
type WorkspaceView = "conversation" | ProfileKind | "management";
const PROFILE_NAV: ProfileKind[] = ["memories", "states", "tasks", "actions"];

function formatTime(value?: string): string {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? ""
    : new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(date);
}

function runtimeLabel(runtime: RuntimeStatus | null): string {
  if (!runtime) return "Runtime unknown";
  return `Runtime · ${runtime.target_kind}`;
}

function runLabel(run: Run | null): string {
  const lifecycle = run?.typed_payload?.lifecycle;
  if (!lifecycle) return "Ready";
  return lifecycle.replaceAll("_", " ");
}

function isTerminalRun(run: Run | null): boolean {
  return !run || TERMINAL_LIFECYCLES.has(run.typed_payload?.lifecycle ?? "");
}

function latestRecords<T extends { record_id: string; version: number; committed_at?: string }>(records: T[]): T[] {
  const heads = new Map<string, T>();
  for (const record of records) {
    const prior = heads.get(record.record_id);
    if (!prior || record.version > prior.version) heads.set(record.record_id, record);
  }
  return [...heads.values()].sort((left, right) => {
    if (left.committed_at && right.committed_at && left.committed_at !== right.committed_at) {
      return right.committed_at.localeCompare(left.committed_at);
    }
    return right.record_id.localeCompare(left.record_id);
  });
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}

export default function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [view, setView] = useState<WorkspaceView>("conversation");
  const [profileRecords, setProfileRecords] = useState<CanonicalRecord[]>([]);
  const [spaces, setSpaces] = useState<SpaceRecord[]>([]);
  const [profileLoading, setProfileLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [draft, setDraft] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedConversation = useMemo(
    () => conversations.find((conversation) => conversation.record_id === selectedId) ?? null,
    [conversations, selectedId],
  );

  const refreshConversations = useCallback(async () => {
    const records = await listConversations();
    const heads = latestRecords(records);
    setConversations(heads);
    setSelectedId((current) => current ?? heads[0]?.record_id ?? null);
    return heads;
  }, []);

  const refreshMessages = useCallback(async (conversationId: string) => {
    const records = await listMessages(conversationId);
    setMessages(records);
  }, []);

  const refreshRun = useCallback(async (runId: string) => {
    const nextRun = await getRun(runId);
    setRun(nextRun);
    try {
      const nextEvents = await getRunEvents(runId);
      setEvents(nextEvents);
    } catch {
      // Run state remains authoritative if the finite SSE response is unavailable.
    }
    return nextRun;
  }, []);

  const refreshStatus = useCallback(async () => {
    const [readyBody, runtimeBody] = await Promise.all([getReady(), getRuntime()]);
    setReady(readyBody.status === "healthy" && readyBody.durable);
    setRuntime(runtimeBody);
  }, []);

  const refreshRuntimeContext = useCallback(async () => {
    await refreshStatus();
  }, [refreshStatus]);

  const refreshProfiles = useCallback(async (profileKind: ProfileKind) => {
    setProfileLoading(true);
    try {
      const records = await listProfileRecords(profileKind);
      setProfileRecords(records);
    } finally {
      setProfileLoading(false);
    }
  }, []);

  const refreshSpaces = useCallback(async () => {
    const records = await listSpaces();
    setSpaces(records);
    return records;
  }, []);

  const handleContextChanged = useCallback(async (spaceId: string, endpointRef: string) => {
    setApiContext({ spaceId, endpointRef });
    setSelectedId(null);
    setMessages([]);
    setRun(null);
    setEvents([]);
    await Promise.all([refreshConversations(), refreshStatus()]);
  }, [refreshConversations, refreshStatus]);

  const refreshWorkspace = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const records = await refreshConversations();
      await refreshStatus();
      if (view !== "conversation" && view !== "management") await refreshProfiles(view);
      const conversationId = selectedId ?? records[0]?.record_id;
      if (conversationId) await refreshMessages(conversationId);
      if (run?.record_id) await refreshRun(run.record_id);
    } catch (refreshError) {
      setError(errorMessage(refreshError));
    } finally {
      setRefreshing(false);
    }
  }, [refreshConversations, refreshMessages, refreshProfiles, refreshRun, refreshStatus, run?.record_id, selectedId, view]);

  useEffect(() => {
    let active = true;
    Promise.all([refreshConversations(), refreshStatus(), refreshSpaces()])
      .then(() => {
        if (!active) return;
      })
      .catch((loadError) => active && setError(errorMessage(loadError)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [refreshConversations, refreshSpaces, refreshStatus]);

  useEffect(() => {
    if (!selectedId) {
      setMessages([]);
      setRun(null);
      setEvents([]);
      return;
    }
    setError(null);
    setRun(null);
    setEvents([]);
    refreshMessages(selectedId).catch((loadError) => setError(errorMessage(loadError)));
  }, [refreshMessages, selectedId]);

  useEffect(() => {
    if (view === "conversation" || view === "management") {
      setProfileRecords([]);
      return;
    }
    setError(null);
    refreshProfiles(view).catch((profileError) => setError(errorMessage(profileError)));
  }, [refreshProfiles, view]);

  useEffect(() => {
    const activeRun = run;
    if (!activeRun || isTerminalRun(activeRun)) return;
    const runId = activeRun.record_id;
    let active = true;
    const timer = window.setInterval(() => {
      refreshRun(runId).catch((pollError) => {
        if (active) setError(errorMessage(pollError));
      });
    }, 1000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [refreshRun, run?.record_id, run?.typed_payload?.lifecycle]);

  async function handleCreateConversation(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (creating) return;
    setCreating(true);
    setError(null);
    try {
      const conversation = await createConversation(newTitle);
      setConversations((current) => latestRecords([conversation, ...current]));
      setView("conversation");
      setSelectedId(conversation.record_id);
      setMessages([]);
      setRun(null);
      setEvents([]);
      setNewTitle("");
    } catch (createError) {
      setError(errorMessage(createError));
    } finally {
      setCreating(false);
    }
  }

  async function handleSend(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedId || !draft.trim() || sending) return;
    const text = draft.trim();
    setSending(true);
    setError(null);
    setDraft("");
    try {
      const result = await submitTurn(selectedId, text);
      await refreshRun(result.runId);
      await refreshMessages(selectedId);
      await refreshConversations();
    } catch (sendError) {
      setDraft(text);
      setError(errorMessage(sendError));
    } finally {
      setSending(false);
    }
  }

  async function handleRetry() {
    if (!run || !selectedId || sending) return;
    setSending(true);
    setError(null);
    try {
      const runId = await retryRun(run.record_id);
      await refreshRun(runId);
      await refreshMessages(selectedId);
      await refreshConversations();
    } catch (retryError) {
      setError(errorMessage(retryError));
    } finally {
      setSending(false);
    }
  }

  const lifecycle = run?.typed_payload?.lifecycle;
  const failed = lifecycle === "failed" || lifecycle === "unknown";
  const runActive = Boolean(run && !isTerminalRun(run));

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark">S</div>
          <div>
            <div className="brand-name">OpenShadow</div>
            <div className="brand-caption">personal agent workspace</div>
          </div>
        </div>

        <form className="new-conversation" onSubmit={handleCreateConversation}>
          <label htmlFor="new-title">New conversation</label>
          <div className="new-conversation-row">
            <input
              id="new-title"
              value={newTitle}
              onChange={(event) => setNewTitle(event.target.value)}
              placeholder="A name, or leave blank"
              maxLength={120}
            />
            <button className="icon-button" disabled={creating} aria-label="Create conversation">
              {creating ? "…" : "+"}
            </button>
          </div>
        </form>

        <ContextPanel
          spaces={spaces}
          onContextChanged={handleContextChanged}
          onSpacesChanged={async () => { await refreshSpaces(); }}
        />

        <nav className="workspace-nav" aria-label="Workspace views">
          <button
            className={view === "conversation" ? "selected" : ""}
            onClick={() => setView("conversation")}
          >
            <span className="workspace-nav-icon">↗</span>
            <span>Conversations</span>
          </button>
          {PROFILE_NAV.map((profileKind) => (
            <button
              className={view === profileKind ? "selected" : ""}
              key={profileKind}
              onClick={() => setView(profileKind)}
            >
              <span className="workspace-nav-icon">◇</span>
              <span>{PROFILE_LABELS[profileKind]}</span>
              </button>
            ))}
          <button
            className={view === "management" ? "selected" : ""}
            onClick={() => setView("management")}
          >
            <span className="workspace-nav-icon">⚙</span>
            <span>Project management</span>
          </button>
        </nav>

        <div className="sidebar-section-label">Conversations</div>
        <nav className="conversation-list" aria-label="Conversations">
          {loading && <div className="empty-sidebar">Loading…</div>}
          {!loading && conversations.length === 0 && (
            <div className="empty-sidebar">Create your first conversation.</div>
          )}
          {conversations.map((conversation) => (
            <button
              className={`conversation-item ${conversation.record_id === selectedId ? "selected" : ""}`}
              key={conversation.record_id}
              onClick={() => {
                setView("conversation");
                setSelectedId(conversation.record_id);
              }}
            >
              <span className="conversation-dot" />
              <span className="conversation-item-copy">
                <strong>{recordTitle(conversation)}</strong>
                <small>{formatTime(conversation.committed_at ?? conversation.created_at)}</small>
              </span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className={`status-dot ${ready ? "online" : "offline"}`} />
          <span>{ready ? "Shadow ready" : "Shadow unavailable"}</span>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <div className="eyebrow">{view === "conversation" ? "Conversation" : view === "management" ? "Project management" : "Profile"}</div>
            <h1>
              {view === "conversation"
                ? selectedConversation
                  ? recordTitle(selectedConversation)
                  : "Your workspace"
                : view === "management" ? "Runtime control plane" : PROFILE_LABELS[view]}
            </h1>
          </div>
          <div className="topbar-actions">
            <button className="text-button refresh-button" onClick={refreshWorkspace} disabled={refreshing}>
              {refreshing ? "Refreshing…" : "Refresh"}
            </button>
            <div className="runtime-pill" title={runtime?.target_kind}>
              <span className={`status-dot ${runtime?.status === "unavailable" ? "offline" : "online"}`} />
              <span>{runtimeLabel(runtime)}</span>
            </div>
          </div>
        </header>

        {error && (
          <div className="error-banner" role="alert">
            <span>{error}</span>
            <span className="error-actions">
              <button onClick={refreshWorkspace} disabled={refreshing}>Refresh</button>
              <button onClick={() => setError(null)} aria-label="Dismiss error">Dismiss</button>
            </span>
          </div>
        )}

        {view === "management" ? (
          <ManagementView onRuntimeChanged={refreshRuntimeContext} />
        ) : view !== "conversation" ? (
          <ProfileView
            kind={view}
            records={profileRecords}
            loading={profileLoading}
            refreshing={refreshing}
            onRefresh={() => refreshProfiles(view).catch((profileError) => setError(errorMessage(profileError)))}
            onChanged={() => refreshProfiles(view)}
          />
        ) : (
          <>
          <section className="conversation-view" aria-live="polite">
          {!selectedConversation && !loading && (
            <div className="welcome-card">
              <div className="welcome-orb">✦</div>
              <h2>A calm place to think.</h2>
              <p>Create a conversation to begin. Your records stay in Shadow&apos;s canonical store.</p>
            </div>
          )}
          {selectedConversation && messages.length === 0 && !sending && (
            <div className="welcome-card compact">
              <div className="welcome-orb">✦</div>
              <h2>What&apos;s on your mind?</h2>
              <p>Start with a question, a note, or a small task.</p>
            </div>
          )}
          {messages.map((message) => (
            <article className={`message-row ${messageKind(message)}`} key={message.record_id}>
              <div className="message-avatar">{messageKind(message) === "user" ? "You" : "S"}</div>
              <div className="message-body">
                <div className="message-meta">
                  <strong>{messageKind(message) === "user" ? "You" : "Shadow"}</strong>
                  <span>{formatTime(message.created_at ?? message.committed_at)}</span>
                </div>
                <div className="message-content">{messageText(message)}</div>
              </div>
            </article>
          ))}
          {sending && (
            <article className="message-row assistant">
              <div className="message-avatar">S</div>
              <div className="message-body">
                <div className="message-meta"><strong>Shadow</strong><span>working</span></div>
                <div className="typing-indicator"><i /><i /><i /></div>
              </div>
            </article>
          )}
          </section>

        <section className="composer-section">
          {run && (
            <div className="run-strip">
              <div className="run-state">
                <span className={`run-indicator ${failed ? "failed" : lifecycle === "completed" ? "complete" : "active"}`} />
                <span>Run {runLabel(run)}</span>
                {events.length > 0 && <small>{events.length} event{events.length === 1 ? "" : "s"}</small>}
              </div>
              {failed && (
                <button className="text-button" onClick={handleRetry} disabled={sending}>Retry</button>
              )}
            </div>
          )}
          {events.length > 0 && (
            <details className="event-details">
              <summary>Event timeline</summary>
              <div className="event-list">
                {events.map((event, index) => (
                  <div className="event-row" key={`${event.sequence ?? "event"}-${index}`}>
                    <span className="event-sequence">{event.sequence ?? index + 1}</span>
                    <span className="event-type">{event.event_type ?? "event"}</span>
                    {event.payload && (
                      <code>{JSON.stringify(event.payload)}</code>
                    )}
                  </div>
                ))}
              </div>
            </details>
          )}
          <form className="composer" onSubmit={handleSend}>
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={selectedConversation ? "Write a message…" : "Create a conversation first"}
              disabled={!selectedConversation || sending || runActive}
              rows={1}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <button className="send-button" disabled={!selectedConversation || !draft.trim() || sending || runActive}>
              <span>{sending || runActive ? "Working" : "Send"}</span>
              <span className="send-arrow">↗</span>
            </button>
          </form>
          <div className="composer-note">Enter to send · Shift + Enter for a new line</div>
          </section>
          </>
        )}
      </main>
    </div>
  );
}
