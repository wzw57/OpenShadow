import type {
  CanonicalRecord,
  Conversation,
  Message,
  Run,
  RunEvent,
  RuntimeStatus,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");
export const PRINCIPAL_REF = import.meta.env.VITE_PRINCIPAL_REF ?? "principal-local";
export const SPACE_ID = import.meta.env.VITE_SPACE_ID ?? "space-personal";
export const ENDPOINT_REF = import.meta.env.VITE_ENDPOINT_REF ?? "endpoint-local-web";

export class ApiError extends Error {
  status: number;
  code?: string;
  category?: string;
  retryable?: boolean;

  constructor(status: number, body: unknown) {
    const problem = body && typeof body === "object" ? (body as Record<string, unknown>) : {};
    super(typeof problem.message === "string" ? problem.message : `Request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.code = typeof problem.code === "string" ? problem.code : undefined;
    this.category = typeof problem.category === "string" ? problem.category : undefined;
    this.retryable = typeof problem.retryable === "boolean" ? problem.retryable : undefined;
  }
}

function requestHeaders(extra: Record<string, string> = {}): HeadersInit {
  return {
    Accept: "application/json",
    "X-Principal-Ref": PRINCIPAL_REF,
    "X-Space-Id": SPACE_ID,
    ...extra,
  };
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...requestHeaders(),
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers ?? {}),
    },
  });
  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new ApiError(response.status, body);
  }
  return body as T;
}

function requestId(prefix: string): string {
  const id = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${id}`;
}

export async function getReady(): Promise<{ status: string; durable: boolean }> {
  return request("/readyz");
}

export async function getRuntime(): Promise<RuntimeStatus> {
  const body = await request<{ runtime: RuntimeStatus }>("/v1/runtime");
  return body.runtime;
}

export async function listConversations(): Promise<Conversation[]> {
  const body = await request<{ records: Conversation[] }>("/v1/conversations");
  return body.records;
}

export async function createConversation(title?: string): Promise<Conversation> {
  const idempotencyKey = requestId("conversation");
  const body = await request<{ record: Conversation }>("/v1/conversations", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({ title: title?.trim() || undefined }),
  });
  return body.record;
}

export async function listMessages(conversationId: string): Promise<Message[]> {
  const body = await request<{ records: Message[] }>(
    `/v1/conversations/${encodeURIComponent(conversationId)}/messages`,
  );
  return body.records;
}

export async function submitTurn(conversationId: string, text: string): Promise<{
  runId: string;
  replayed: boolean;
}> {
  const key = requestId("turn");
  const body = await request<{
    root_run_ref: { record_id: string };
    replayed: boolean;
  }>(`/v1/conversations/${encodeURIComponent(conversationId)}/turns`, {
    method: "POST",
    headers: {
      "Idempotency-Key": key,
      "X-Endpoint-Ref": ENDPOINT_REF,
    },
    body: JSON.stringify({
      submission_id: key,
      content_blocks: [
        {
          block_type: "shadow.content.text",
          content_schema_ref: "https://schemas.openshadow.dev/content/text/1.0.0",
          typed_content: { text },
        },
      ],
    }),
  });
  return { runId: body.root_run_ref.record_id, replayed: body.replayed };
}

export async function getRun(runId: string): Promise<Run> {
  const body = await request<{ record: Run }>(`/v1/runs/${encodeURIComponent(runId)}`);
  return body.record;
}

export async function retryRun(runId: string): Promise<string> {
  const body = await request<{ root_run_ref: { record_id: string } }>(
    `/v1/runs/${encodeURIComponent(runId)}/retry`,
    {
      method: "POST",
      headers: { "Idempotency-Key": requestId("retry") },
    },
  );
  return body.root_run_ref.record_id;
}

export async function getRunEvents(runId: string, lastEventId?: number): Promise<RunEvent[]> {
  const response = await fetch(`${API_BASE}/v1/runs/${encodeURIComponent(runId)}/events`, {
    headers: requestHeaders(lastEventId ? { "Last-Event-ID": String(lastEventId) } : {}),
  });
  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    const body = contentType.includes("json") ? await response.json() : await response.text();
    throw new ApiError(response.status, body);
  }
  const text = await response.text();
  return text
    .split("\n\n")
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .map((chunk) => {
      const event: RunEvent = {};
      for (const line of chunk.split("\n")) {
        const separator = line.indexOf(":");
        if (separator < 0) continue;
        const key = line.slice(0, separator);
        const value = line.slice(separator + 1).trimStart();
        if (key === "id") event.sequence = Number(value);
        else if (key === "event") event.event_type = value;
        else if (key === "data") {
          try {
            Object.assign(event, JSON.parse(value));
          } catch {
            event.payload = { raw: value };
          }
        }
      }
      return event;
    });
}

export function recordTitle(record: CanonicalRecord): string {
  const title = record.typed_payload?.title;
  return typeof title === "string" && title.trim() ? title : "Untitled conversation";
}

export function messageText(record: CanonicalRecord): string {
  const blocks = record.typed_payload?.content_blocks;
  if (!Array.isArray(blocks)) return "";
  const textBlock = blocks.find((block) => {
    if (!block || typeof block !== "object") return false;
    const type = (block as Record<string, unknown>).block_type;
    return type === "shadow.content.text";
  });
  if (!textBlock || typeof textBlock !== "object") return "";
  const content = (textBlock as Record<string, unknown>).typed_content;
  if (typeof content === "string") return content;
  if (content && typeof content === "object") {
    const text = (content as Record<string, unknown>).text;
    if (typeof text === "string") return text;
  }
  return "";
}

export function messageKind(record: CanonicalRecord): "user" | "assistant" {
  return record.typed_payload?.message_type === "shadow.message.user" ? "user" : "assistant";
}
