import { useEffect, useMemo, useState } from "react";
import {
  ApiError,
  acceptInvitation,
  createInvitation,
  createSpace,
  getApiContext,
  listSpaceMembers,
  pairEndpoint,
  revokeMember,
} from "./api";
import type { MembershipRecord, SpaceRecord } from "./types";

type ContextPanelProps = {
  spaces: SpaceRecord[];
  onContextChanged: (spaceId: string, endpointRef: string) => Promise<void>;
  onSpacesChanged: () => Promise<void>;
};

function message(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Context operation failed.";
}

function spaceLabel(space: SpaceRecord): string {
  return String(space.typed_payload?.display_name ?? space.record_id);
}

export default function ContextPanel({ spaces, onContextChanged, onSpacesChanged }: ContextPanelProps) {
  const context = getApiContext();
  const [spaceId, setSpaceId] = useState(context.spaceId);
  const [endpointRef, setEndpointRef] = useState(context.endpointRef);
  const [newSpaceId, setNewSpaceId] = useState("");
  const [newSpaceName, setNewSpaceName] = useState("");
  const [invitee, setInvitee] = useState("");
  const [inviteRole, setInviteRole] = useState<"editor" | "viewer">("viewer");
  const [members, setMembers] = useState<MembershipRecord[]>([]);
  const [invitationId, setInvitationId] = useState("");
  const [invitationToken, setInvitationToken] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selectedSpace = useMemo(() => spaces.find((space) => space.record_id === spaceId), [spaces, spaceId]);
  const isOwner = selectedSpace?.typed_payload?.owner_ref === context.principalRef || spaceId === "space-personal";

  useEffect(() => {
    if (spaces.length > 0 && !spaces.some((space) => space.record_id === spaceId)) setSpaceId(spaces[0].record_id);
  }, [spaces, spaceId]);

  useEffect(() => {
    let active = true;
    listSpaceMembers(spaceId)
      .then((records) => active && setMembers(records))
      .catch(() => active && setMembers([]));
    return () => { active = false; };
  }, [spaceId]);

  async function switchContext(nextSpace: string, nextEndpoint = endpointRef) {
    setError(null);
    setNotice(null);
    setSpaceId(nextSpace);
    setEndpointRef(nextEndpoint);
    await onContextChanged(nextSpace, nextEndpoint);
  }

  async function handlePair() {
    try {
      const endpoint = await pairEndpoint(endpointRef);
      setEndpointRef(String(endpoint.typed_payload?.endpoint_ref ?? endpointRef));
      setNotice("Endpoint paired.");
    } catch (pairError) {
      setError(message(pairError));
    }
  }

  async function handleCreateSpace(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const space = await createSpace(newSpaceId.trim(), newSpaceName.trim());
      await onSpacesChanged();
      await switchContext(space.record_id);
      setNewSpaceId("");
      setNewSpaceName("");
      setNotice("Space created.");
    } catch (spaceError) {
      setError(message(spaceError));
    }
  }

  async function handleInvite(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const result = await createInvitation(invitee.trim(), inviteRole, new Date(Date.now() + 24 * 3600_000).toISOString());
      setInvitee("");
      setNotice(`Invitation token (copy now): ${result.invitationToken}`);
    } catch (inviteError) {
      setError(message(inviteError));
    }
  }

  async function handleAccept(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await acceptInvitation(invitationId.trim(), invitationToken.trim());
      setInvitationId("");
      setInvitationToken("");
      await onSpacesChanged();
      setNotice("Invitation accepted.");
    } catch (acceptError) {
      setError(message(acceptError));
    }
  }

  async function handleRevoke(principalRef: string, version: number) {
    if (!window.confirm(`Revoke ${principalRef} from this Space?`)) return;
    try {
      await revokeMember(principalRef, version);
      setMembers(await listSpaceMembers(spaceId));
      setNotice("Membership revoked.");
    } catch (revokeError) {
      setError(message(revokeError));
    }
  }

  return (
    <section className="context-panel" aria-label="Identity and Space context">
      <div className="context-heading"><strong>Workspace context</strong><span>{context.principalRef}</span></div>
      <label className="context-field"><span>Space</span><select value={spaceId} onChange={(event) => void switchContext(event.target.value)}>
        {spaces.map((space) => <option key={space.record_id} value={space.record_id}>{spaceLabel(space)}</option>)}
      </select></label>
      <div className="context-endpoint-row"><label className="context-field"><span>Endpoint ref</span><input value={endpointRef} onChange={(event) => setEndpointRef(event.target.value)} /></label><button className="text-button" onClick={() => void handlePair()}>Pair</button></div>
      <form className="context-create" onSubmit={handleCreateSpace}><input value={newSpaceId} onChange={(event) => setNewSpaceId(event.target.value)} placeholder="new-space-id" required /><input value={newSpaceName} onChange={(event) => setNewSpaceName(event.target.value)} placeholder="Space name" required /><button className="text-button">Create Space</button></form>
      {isOwner && <form className="context-create" onSubmit={handleInvite}><input value={invitee} onChange={(event) => setInvitee(event.target.value)} placeholder="invite principal" required /><select value={inviteRole} onChange={(event) => setInviteRole(event.target.value as "editor" | "viewer")}><option value="viewer">viewer</option><option value="editor">editor</option></select><button className="text-button">Invite</button></form>}
      <form className="context-create" onSubmit={handleAccept}><input value={invitationId} onChange={(event) => setInvitationId(event.target.value)} placeholder="invitation id" required /><input value={invitationToken} onChange={(event) => setInvitationToken(event.target.value)} placeholder="invitation token" required /><button className="text-button">Accept</button></form>
      {members.length > 0 && <div className="context-members"><span>Members</span>{members.map((member) => { const payload = member.typed_payload ?? {}; const principal = String(payload.principal_ref ?? member.record_id); return <div key={member.record_id} className="context-member"><span>{principal} · {String(payload.role ?? "unknown")}</span>{isOwner && principal !== context.principalRef && <button className="text-button" onClick={() => void handleRevoke(principal, member.version)}>Revoke</button>}</div>; })}</div>}
      {notice && <div className="context-notice">{notice}</div>}
      {error && <div className="context-error">{error}</div>}
    </section>
  );
}
