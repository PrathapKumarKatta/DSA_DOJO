import { useState } from "react";
import type { FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Clock3,
  MessageSquare,
  Send,
  Trash2,
} from "lucide-react";
import {
  allPages,
  api,
  ApiError,
  errorMessage,
  patch,
  post,
  remove,
} from "./api";
import type { Activity, Comment, Member, Task, TaskInput, User } from "./types";
import {
  Avatar,
  ErrorState,
  formatTime,
  Modal,
  SaveButton,
  Spinner,
  useAction,
  useToast,
} from "./ui";

export const statusLabels = {
  todo: "To do",
  in_progress: "In progress",
  blocked: "Blocked",
  done: "Done",
};

export function TaskFields({
  task,
  members,
  user,
  initialStatus = "todo",
}: {
  task?: Task;
  members: Member[];
  user: User;
  initialStatus?: string;
}) {
  const localDue = task?.due_at
    ? new Date(
        new Date(task.due_at).getTime() -
          new Date(task.due_at).getTimezoneOffset() * 60_000,
      )
        .toISOString()
        .slice(0, 16)
    : "";
  return (
    <>
      <label>
        Task name
        <input
          name="title"
          placeholder="What needs to happen?"
          defaultValue={task?.title}
          required
          maxLength={200}
          autoFocus
        />
      </label>
      <label>
        Description
        <textarea
          name="description"
          placeholder="Add a little context, a few details, or a big idea…"
          defaultValue={task?.description}
          maxLength={10000}
          rows={4}
        />
      </label>
      <div className="form-grid">
        <label>
          Status
          <select name="status" defaultValue={task?.status ?? initialStatus}>
            {Object.entries(statusLabels).map(([key, label]) => (
              <option value={key} key={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Priority
          <select name="priority" defaultValue={task?.priority ?? "medium"}>
            {["low", "medium", "high", "urgent"].map((p) => (
              <option key={p} value={p}>
                {p[0].toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Assignee
          <select name="assignee_id" defaultValue={task?.assignee_id ?? ""}>
            <option value="">Unassigned</option>
            {members.map((member) => (
              <option key={member.user_id} value={member.user_id}>
                {member.user_id === user.id
                  ? `${user.full_name} (you)`
                  : `Member ${member.user_id.slice(0, 8)}`}
              </option>
            ))}
          </select>
        </label>
        <label>
          Due date <span className="field-hint">(local time)</span>
          <input type="datetime-local" name="due_at" defaultValue={localDue} />
        </label>
      </div>
    </>
  );
}

export function taskInput(form: HTMLFormElement): TaskInput {
  const data = new FormData(form);
  return {
    title: String(data.get("title")).trim(),
    description: String(data.get("description") ?? ""),
    status: data.get("status") as TaskInput["status"],
    priority: data.get("priority") as TaskInput["priority"],
    assignee_id: String(data.get("assignee_id") ?? "") || null,
    due_at: data.get("due_at")
      ? new Date(String(data.get("due_at"))).toISOString()
      : null,
  };
}

export default function TaskPanel({
  task,
  user,
  members,
  close,
  refresh,
}: {
  task: Task;
  user: User;
  members: Member[];
  close: () => void;
  refresh: () => Promise<void>;
}) {
  const [snapshot, setSnapshot] = useState(task);
  const [tab, setTab] = useState<"comments" | "activity">("comments");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [saving, setSaving] = useState(false);
  const action = useAction();
  const toast = useToast();
  const qc = useQueryClient();
  const role = members.find((m) => m.user_id === user.id)?.role;
  const canEdit =
    role === "owner" ||
    role === "admin" ||
    [snapshot.creator_id, snapshot.assignee_id].includes(user.id);
  const canDelete =
    role === "owner" || role === "admin" || snapshot.creator_id === user.id;
  const comments = useQuery({
    queryKey: ["comments", task.id],
    queryFn: () => allPages<Comment>(`/tasks/${task.id}/comments`),
  });
  const activity = useQuery({
    queryKey: ["task-activity", task.id],
    queryFn: () => allPages<Activity>(`/tasks/${task.id}/activity`),
    enabled: tab === "activity",
  });

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = taskInput(event.currentTarget);
    setSaving(true);
    try {
      const updated = await patch<Task>(`/tasks/${snapshot.id}`, {
        ...input,
        expected_version: snapshot.version,
      });
      setSnapshot(updated);
      setConflict(false);
      await refresh();
      await qc.invalidateQueries({ queryKey: ["task-activity", task.id] });
      toast("Task updated. A little more progress.");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) setConflict(true);
      else toast(errorMessage(error), true);
    } finally {
      setSaving(false);
    }
  }

  async function comment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const body = String(new FormData(form).get("body")).trim();
    if (!body) return;
    await action.run(async () => {
      await post(`/tasks/${task.id}/comments`, { body });
      form.reset();
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["comments", task.id] }),
        qc.invalidateQueries({ queryKey: ["task-activity", task.id] }),
        qc.invalidateQueries({ queryKey: ["activity"] }),
      ]);
      toast("Comment added.");
    });
  }

  return (
    <Modal
      wide
      title="A closer look"
      subtitle={`TASK-${task.id.slice(0, 4).toUpperCase()} · Created ${formatTime(task.created_at)}`}
      close={close}
    >
      <div className="task-detail-layout">
        <div className="task-edit">
          <form className="stack-form" onSubmit={save}>
            <fieldset
              disabled={!canEdit || saving || conflict}
              key={snapshot.version}
            >
              <TaskFields task={snapshot} members={members} user={user} />
            </fieldset>
            {!canEdit && (
              <p className="notice">
                You can view and discuss this task. Its creator, assignee, or a
                workspace manager can edit it.
              </p>
            )}
            {conflict && (
              <div className="conflict" role="alert">
                <strong>This task has changed.</strong>
                <p>
                  Your draft is still here. Load the latest version before
                  making another update.
                </p>
                <button
                  type="button"
                  className="button secondary"
                  onClick={() =>
                    action.run(async () => {
                      setSnapshot(await api<Task>(`/tasks/${task.id}`));
                      setConflict(false);
                    })
                  }
                  disabled={action.busy}
                >
                  Load latest version <ArrowUpRight size={15} />
                </button>
              </div>
            )}
            <div className="form-actions">
              <span className="version-label">
                <Clock3 size={13} /> Version {snapshot.version}
              </span>
              {canEdit && <SaveButton busy={saving} disabled={conflict} />}
            </div>
          </form>
          {canDelete && (
            <div className="danger-area">
              {confirmDelete ? (
                <>
                  <p>
                    Delete this task and its comments? This cannot be undone.
                  </p>
                  <div className="button-row">
                    <button
                      className="button danger"
                      disabled={action.busy}
                      onClick={() =>
                        action.run(async () => {
                          await remove(`/tasks/${task.id}`);
                          await refresh();
                          toast("Task deleted.");
                          close();
                        })
                      }
                    >
                      Delete task
                    </button>
                    <button
                      className="button secondary"
                      onClick={() => setConfirmDelete(false)}
                    >
                      Keep task
                    </button>
                  </div>
                </>
              ) : (
                <button
                  className="text-button danger-text"
                  onClick={() => setConfirmDelete(true)}
                >
                  <Trash2 size={14} /> Delete task
                </button>
              )}
            </div>
          )}
        </div>
        <aside className="discussion">
          <div className="detail-tabs">
            <button
              className={tab === "comments" ? "active" : ""}
              onClick={() => setTab("comments")}
            >
              <MessageSquare size={15} /> Comments{" "}
              <span>{comments.data?.length ?? 0}</span>
            </button>
            <button
              className={tab === "activity" ? "active" : ""}
              onClick={() => setTab("activity")}
            >
              Activity
            </button>
          </div>
          <div className="discussion-feed">
            {tab === "comments" ? (
              comments.isPending ? (
                <Spinner />
              ) : comments.isError ? (
                <ErrorState
                  error={comments.error}
                  retry={() => comments.refetch()}
                />
              ) : comments.data.length ? (
                comments.data.map((c) => (
                  <article className="comment" key={c.id}>
                    <Avatar
                      name={
                        c.author_id === user.id
                          ? user.full_name
                          : c.author_id.slice(0, 2)
                      }
                      small
                    />
                    <div>
                      <strong>
                        {c.author_id === user.id
                          ? user.full_name
                          : `Member ${c.author_id.slice(0, 8)}`}
                      </strong>
                      <time>{formatTime(c.created_at)}</time>
                      <p>{c.body}</p>
                    </div>
                  </article>
                ))
              ) : (
                <div className="discussion-empty">
                  <MessageSquare size={26} />
                  <h4>Start the conversation</h4>
                  <p>
                    A question, an idea, or a little encouragement goes a long
                    way.
                  </p>
                </div>
              )
            ) : activity.isPending ? (
              <Spinner />
            ) : activity.isError ? (
              <ErrorState
                error={activity.error}
                retry={() => activity.refetch()}
              />
            ) : (
              <ActivityFeed events={activity.data ?? []} user={user} />
            )}
          </div>
          {tab === "comments" && (
            <form className="comment-form" onSubmit={comment}>
              <label className="sr-only" htmlFor="comment-body">
                Your comment
              </label>
              <textarea
                id="comment-body"
                name="body"
                placeholder="Add to the conversation…"
                required
                maxLength={10000}
                rows={3}
              />
              <button className="button primary" disabled={action.busy}>
                {action.busy ? <Spinner /> : <Send size={14} />} Send comment
              </button>
            </form>
          )}
        </aside>
      </div>
    </Modal>
  );
}

export function ActivityFeed({
  events,
  user,
}: {
  events: Activity[];
  user: User;
}) {
  const labels: Record<string, string> = {
    "task.created": "created a task",
    "task.updated": "updated a task",
    "task.deleted": "deleted a task",
    "task.unassigned": "removed an assignment",
    "comment.created": "added a comment",
  };
  return events.length ? (
    <div className="activity-feed">
      {events.map((event) => (
        <article className="activity-item" key={event.id}>
          <span
            className={`activity-dot ${event.action === "task.created" ? "orange-dot" : ""}`}
          />
          <div>
            <p>
              <strong>
                {event.actor_id === user.id
                  ? user.full_name
                  : `Member ${event.actor_id.slice(0, 8)}`}
              </strong>{" "}
              {labels[event.action] ?? event.action}
            </p>
            {typeof event.payload.title === "string" && (
              <span className="activity-title">{event.payload.title}</span>
            )}
            {event.action === "task.updated" &&
              typeof event.payload.after === "object" &&
              event.payload.after !== null && (
                <span className="activity-title">
                  {Object.keys(event.payload.after)
                    .map((k) => k.replaceAll("_", " "))
                    .join(", ")}
                </span>
              )}
            <time>{formatTime(event.created_at)}</time>
          </div>
        </article>
      ))}
    </div>
  ) : (
    <div className="discussion-empty">
      <Clock3 size={26} />
      <h4>A fresh start</h4>
      <p>As work moves forward, its story will appear here.</p>
    </div>
  );
}
