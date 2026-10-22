import { useState } from "react";
import type { FormEvent } from "react";
import {
  Copy,
  Crown,
  ShieldCheck,
  Trash2,
  UserPlus,
  Users,
} from "lucide-react";
import { patch, post, remove } from "./api";
import type { Member, Role, User } from "./types";
import { Avatar, SaveButton, useAction, useToast } from "./ui";

export default function Team({
  workspaceId,
  members,
  user,
  refresh,
}: {
  workspaceId: string;
  members: Member[];
  user: User;
  refresh: () => Promise<void>;
}) {
  const role = members.find((m) => m.user_id === user.id)?.role;
  const manager = role === "owner" || role === "admin";
  const [removing, setRemoving] = useState<string | null>(null);
  const action = useAction();
  const toast = useToast();
  async function invite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await action.run(async () => {
      await post(`/workspaces/${workspaceId}/members`, {
        user_id: data.get("user_id"),
        role: data.get("role"),
      });
      await refresh();
      form.reset();
      toast("A new teammate. Welcome to the workspace.");
    });
  }
  return (
    <div className="team-page">
      <div className="section-intro">
        <span className="section-icon">
          <Users size={24} />
        </span>
        <h2>Good work takes good people.</h2>
        <p>One shared space. A whole lot of possibilities.</p>
      </div>
      <div className="team-card">
        <div className="section-card-head">
          <h3>
            Workspace members <span className="count">{members.length}</span>
          </h3>
          <span className="muted">Your people, all in one place</span>
        </div>
        {members.map((member) => (
          <div className="member-row" key={member.user_id}>
            <Avatar
              name={
                member.user_id === user.id
                  ? user.full_name
                  : member.user_id.slice(0, 2)
              }
            />
            <div className="member-info">
              <strong>
                {member.user_id === user.id ? (
                  <>
                    {user.full_name} <small>(you)</small>
                  </>
                ) : (
                  `Member ${member.user_id.slice(0, 8)}`
                )}
              </strong>
              <span>
                {member.user_id === user.id ? user.email : member.user_id}
              </span>
            </div>
            <span className={`role-badge ${member.role}`}>
              {member.role === "owner" ? (
                <Crown size={13} />
              ) : (
                <ShieldCheck size={13} />
              )}
              {member.role}
            </span>
            {role === "owner" && member.role !== "owner" && (
              <select
                aria-label={`Role for member ${member.user_id.slice(0, 8)}`}
                value={member.role}
                disabled={action.busy}
                onChange={(e) => {
                  const next = e.target.value as Role;
                  action.run(async () => {
                    await patch(
                      `/workspaces/${workspaceId}/members/${member.user_id}`,
                      { role: next },
                    );
                    await refresh();
                    toast("Member role updated.");
                  });
                }}
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
              </select>
            )}
            {manager &&
              member.role !== "owner" &&
              (role === "owner" || member.role === "member") && (
                <button
                  className="icon-button danger-text"
                  aria-label={`Remove member ${member.user_id.slice(0, 8)}`}
                  onClick={() => setRemoving(member.user_id)}
                >
                  <Trash2 size={16} />
                </button>
              )}
          </div>
        ))}
      </div>
      {removing && (
        <div className="notice removal-confirm" role="alert">
          <p>
            Remove this member? Their tasks will become unassigned and they will
            lose access.
          </p>
          <div className="button-row">
            <button
              className="button danger"
              disabled={action.busy}
              onClick={() =>
                action.run(async () => {
                  await remove(
                    `/workspaces/${workspaceId}/members/${removing}`,
                  );
                  setRemoving(null);
                  await refresh();
                  toast("Member removed.");
                })
              }
            >
              Remove member
            </button>
            <button
              className="button secondary"
              onClick={() => setRemoving(null)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      {manager && (
        <form className="team-card stack-form invite-form" onSubmit={invite}>
          <div>
            <h3>
              <UserPlus size={18} /> Bring someone into the flow
            </h3>
            <p>
              Add an existing TaskFlow user with the user ID from their profile.
            </p>
          </div>
          <div className="invite-fields">
            <label>
              User ID
              <input
                name="user_id"
                required
                placeholder="Paste their user ID"
                pattern="[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}"
              />
            </label>
            <label>
              Workspace role
              <select name="role">
                <option value="member">Member</option>
                {role === "owner" && <option value="admin">Admin</option>}
              </select>
            </label>
            <SaveButton busy={action.busy}>Add member</SaveButton>
          </div>
        </form>
      )}
      <div className="your-id">
        <p>Joining another workspace? Share your user ID.</p>
        <button
          className="text-button"
          onClick={() =>
            action.run(async () => {
              await navigator.clipboard.writeText(user.id);
              toast("Your user ID is copied.");
            })
          }
        >
          <Copy size={14} /> Copy my user ID
        </button>
      </div>
    </div>
  );
}
