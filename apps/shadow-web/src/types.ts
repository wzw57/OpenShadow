export type JsonObject = Record<string, unknown>;

export type CanonicalRecord = {
  record_id: string;
  version: number;
  record_type?: string;
  owner_ref?: string;
  space_id?: string;
  created_at?: string;
  committed_at?: string;
  typed_payload?: JsonObject;
};

export type Conversation = CanonicalRecord;
export type Message = CanonicalRecord;
export type ProfileKind = "memories" | "states" | "tasks" | "actions";

export type Run = CanonicalRecord & {
  typed_payload?: JsonObject & {
    lifecycle?: string;
    terminal_at?: string;
    started_at?: string;
    usage_summary?: JsonObject;
    result_ref?: { record_id?: string; version?: number };
  };
};

export type RuntimeStatus = {
  status: "configured" | "healthy" | "unavailable";
  target_kind: string;
  descriptor: JsonObject;
  health?: JsonObject | null;
};

export type RuntimeState = {
  lifecycle: string;
  health: string;
  pid?: number | null;
  external_ref?: string | null;
  last_error?: JsonObject | null;
  updated_at?: string;
};

export type RuntimeProfile = {
  runtime_id: string;
  display_name: string;
  adapter_factory: string;
  target_kind: string;
  enabled: boolean;
  auto_start: boolean;
  launch?: JsonObject;
  health?: JsonObject;
  workspace_configured?: boolean;
};

export type RuntimeInstance = {
  runtime_id: string;
  active: boolean;
  profile: RuntimeProfile;
  descriptor?: JsonObject | null;
  state: RuntimeState;
  replayed?: boolean;
};

export type ManagementOverview = {
  api: JsonObject;
  store: JsonObject;
  web_ui: JsonObject;
  active_runtime_id: string;
  runtimes: RuntimeInstance[];
  generated_at?: string;
};

export type SpaceRecord = CanonicalRecord & {
  typed_payload?: JsonObject & { display_name?: string; space_kind?: string; owner_ref?: string };
};

export type MembershipRecord = CanonicalRecord & {
  typed_payload?: JsonObject & { principal_ref?: string; role?: string; lifecycle?: string };
};

export type EndpointRecord = CanonicalRecord & {
  typed_payload?: JsonObject & { endpoint_ref?: string; trust?: string; lifecycle?: string; label?: string };
};

export type RunEvent = {
  sequence?: number;
  event_type?: string;
  payload?: JsonObject;
  [key: string]: unknown;
};
