import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity as ActivityIcon,
  ArrowDownWideNarrow,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  Circle,
  CircleCheck,
  Clock3,
  Copy,
  Folder,
  FolderOpen,
  LayoutDashboard,
  LayoutGrid,
  List,
  LogOut,
  Menu,
  Plus,
  Search,
  Settings2,
  SlidersHorizontal,
  Sparkles,
  Target,
  Trash2,
  Users,
  X,
} from "lucide-react";
import {
  allPages,
  api,
  ApiError,
  errorMessage,
  patch,
  post,
  remove,
  session,
} from "./api";
import Auth from "./Auth";
import TaskPanel, {
  ActivityFeed,
  statusLabels,
  TaskFields,
  taskInput,
} from "./TaskPanel";
import Team from "./Team";
import type {
  Activity,
  Member,
  Priority,
  Project,
  Stats,
  Status,
  Task,
  User,
  Workspace,
} from "./types";
import {
  Avatar,
  Empty,
  ErrorState,
  formatDate,
  Logo,
  Modal,
  SaveButton,
  Spinner,
  ToastContext,
  useAction,
  useToast,
} from "./ui";

type View = "board" | "list" | "activity" | "team" | "overview";
type FormType =
  | "workspace"
  | "project"
  | "task"
  | "profile"
  | "delete-workspace"
  | null;
const statuses = Object.keys(statusLabels) as Status[];
const priorityRank: Record<Priority, number> = {
  low: 1,
  medium: 2,
  high: 3,
  urgent: 4,
};

export default function App() {
  const qc = useQueryClient();
  const [authenticated, setAuthenticated] = useState(!!session.get());
  const [notice, setNotice] = useState("");
  const [toast, setToast] = useState<{
    text: string;
    error: boolean;
    id: number;
  } | null>(null);
  const notify = useCallback(
    (text: string, error = false) => setToast({ text, error, id: Date.now() }),
    [],
  );
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/users/me"),
    enabled: authenticated,
    staleTime: 60_000,
  });
  const logout = useCallback(() => {
    session.clear();
    setAuthenticated(false);
    qc.clear();
  }, [qc]);

  useEffect(() => {
    const expired = () => {
      logout();
      setNotice("Your session has ended. Sign in to keep the flow going.");
    };
    window.addEventListener("taskflow:expired", expired);
    return () => window.removeEventListener("taskflow:expired", expired);
  }, [logout]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), toast.error ? 8000 : 4000);
    return () => clearTimeout(timer);
  }, [toast]);
  function onLogin(user: User) {
    qc.setQueryData(["me"], user);
    setNotice("");
    setAuthenticated(true);
  }

  return (
    <ToastContext.Provider value={notify}>
      {!authenticated ? (
        <Auth onLogin={onLogin} notice={notice} />
      ) : me.isPending ? (
        <div className="page-loader">
          <Logo />
          <Spinner />
          <p>Finding your flow…</p>
        </div>
      ) : me.isError ? (
        <div className="page-loader">
          <Logo />
          <ErrorState error={me.error} retry={() => me.refetch()} />
          <button className="text-button" onClick={logout}>
            Back to sign in
          </button>
        </div>
      ) : (
        <WorkspaceApp key={me.data.id} user={me.data} logout={logout} />
      )}
      {toast && (
        <div
          className={`toast ${toast.error ? "toast-error" : ""}`}
          role={toast.error ? "alert" : "status"}
        >
          {toast.error ? <Circle size={18} /> : <CircleCheck size={18} />}
          <span>{toast.text}</span>
          <button
            onClick={() => setToast(null)}
            aria-label="Dismiss notification"
          >
            <X size={16} />
          </button>
        </div>
      )}
    </ToastContext.Provider>
  );
}

function WorkspaceApp({ user, logout }: { user: User; logout: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [workspaceId, setWorkspaceId] = useState(
    () => sessionStorage.getItem(`taskflow.workspace.${user.id}`) ?? "",
  );
  const [projectId, setProjectId] = useState(
    () => sessionStorage.getItem(`taskflow.project.${user.id}`) ?? "",
  );
  const [view, setView] = useState<View>("board");
  const [mobileNav, setMobileNav] = useState(false);
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia("(max-width: 760px)").matches,
  );
  useEffect(() => {
    const media = window.matchMedia("(max-width: 760px)");
    const update = () => setIsMobile(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (!mobileNav) return;
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileNav(false);
    };
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [mobileNav]);
  const health = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const apiOrigin = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
      const response = await fetch(`${apiOrigin}/health/ready`);
      if (!response.ok) throw new Error("Backend unavailable");
      return response.json();
    },
    refetchInterval: 30_000,
  });
  const [form, setForm] = useState<FormType>(null);
  const [initialStatus, setInitialStatus] = useState<Status>("todo");
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("");
  const [status, setStatus] = useState("");
  const [onlyMine, setOnlyMine] = useState(false);
  const [sort, setSort] = useState("created");
  const [page, setPage] = useState(0);
  const [moving, setMoving] = useState<string | null>(null);
  const workspaces = useQuery({
    queryKey: ["workspaces"],
    queryFn: () => allPages<Workspace>("/workspaces"),
  });
  const workspace =
    workspaces.data?.find((w) => w.id === workspaceId) ?? workspaces.data?.[0];
  const wid = workspace?.id;
  const projects = useQuery({
    queryKey: ["projects", wid],
    queryFn: () => allPages<Project>(`/workspaces/${wid}/projects`),
    enabled: !!wid,
  });
  const members = useQuery({
    queryKey: ["members", wid],
    queryFn: () => api<Member[]>(`/workspaces/${wid}/members`),
    enabled: !!wid,
  });
  const project =
    projects.data?.find((p) => p.id === projectId) ?? projects.data?.[0];
  const tasks = useQuery({
    queryKey: ["tasks", project?.id],
    queryFn: () => allPages<Task>(`/projects/${project?.id}/tasks`),
    enabled: !!project,
  });
  const activity = useQuery({
    queryKey: ["activity", wid],
    queryFn: () => allPages<Activity>(`/workspaces/${wid}/activity`),
    enabled: !!wid && view === "activity",
  });
  const stats = useQuery({
    queryKey: ["stats", wid],
    queryFn: () => api<Stats>(`/workspaces/${wid}/stats`),
    enabled: !!wid && view === "overview",
  });
  const role = members.data?.find((m) => m.user_id === user.id)?.role;
  const manager = role === "owner" || role === "admin";
  const allTasks = tasks.data ?? [];
  const done = allTasks.filter((t) => t.status === "done").length;
  const percent = allTasks.length
    ? Math.round((done / allTasks.length) * 100)
    : 0;
  const refresh = useCallback(async () => {
    await qc.invalidateQueries();
  }, [qc]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const result = (tasks.data ?? []).filter(
      (t) =>
        (!q || `${t.title} ${t.description}`.toLowerCase().includes(q)) &&
        (!priority || t.priority === priority) &&
        (!status || t.status === status) &&
        (!onlyMine || t.assignee_id === user.id),
    );
    if (sort === "priority")
      result.sort(
        (a, b) =>
          priorityRank[b.priority] - priorityRank[a.priority] ||
          a.id.localeCompare(b.id),
      );
    if (sort === "due")
      result.sort(
        (a, b) =>
          (a.due_at ? new Date(a.due_at).getTime() : Infinity) -
            (b.due_at ? new Date(b.due_at).getTime() : Infinity) ||
          a.id.localeCompare(b.id),
      );
    return result;
  }, [tasks.data, search, priority, status, onlyMine, user.id, sort]);
  const safePage = Math.min(
    page,
    Math.max(0, Math.ceil(filtered.length / 10) - 1),
  );

  function chooseWorkspace(id: string) {
    sessionStorage.setItem(`taskflow.workspace.${user.id}`, id);
    sessionStorage.removeItem(`taskflow.project.${user.id}`);
    setWorkspaceId(id);
    setProjectId("");
    setSearch("");
    setStatus("");
    setPriority("");
    setOnlyMine(false);
    setView("board");
    setMobileNav(false);
    setSelectedTask(null);
    setPage(0);
  }
  function chooseProject(id: string) {
    sessionStorage.setItem(`taskflow.project.${user.id}`, id);
    setProjectId(id);
    setView("board");
    setSearch("");
    setStatus("");
    setPriority("");
    setOnlyMine(false);
    setMobileNav(false);
    setPage(0);
  }
  function newTask(next: Status = "todo") {
    setInitialStatus(next);
    setForm("task");
  }
  function canEdit(task: Task) {
    return (
      manager || task.creator_id === user.id || task.assignee_id === user.id
    );
  }
  async function move(task: Task, next: Status) {
    if (task.status === next || moving || !canEdit(task)) return;
    setMoving(task.id);
    try {
      await patch(`/tasks/${task.id}`, {
        status: next,
        expected_version: task.version,
      });
      await refresh();
      toast(
        next === "done"
          ? "Nicely done. Another one across the finish line."
          : `Moved to ${statusLabels[next].toLowerCase()}.`,
      );
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        await refresh();
        toast(
          "This task changed. The board is refreshed—try your move again.",
          true,
        );
      } else toast(errorMessage(error), true);
    } finally {
      setMoving(null);
    }
  }
  function nav(next: View, mine = false) {
    setView(next);
    setOnlyMine(mine);
    setMobileNav(false);
  }

  return (
    <div className="app-shell">
      {mobileNav && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobileNav(false)}
        />
      )}
      <aside
        className={`sidebar ${mobileNav ? "is-open" : ""}`}
        inert={isMobile && !mobileNav}
      >
        <Logo />
        <div className="workspace-switch">
          <span className="workspace-symbol">{workspace?.name[0] ?? "Y"}</span>
          <label className="workspace-select">
            <span className="sr-only">Current workspace</span>
            <select
              value={wid ?? ""}
              onChange={(e) => chooseWorkspace(e.target.value)}
              aria-label="Current workspace"
            >
              {!workspace && <option value="">Your workspace</option>}
              {workspaces.data?.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
            <span>
              {role
                ? `${role[0].toUpperCase()}${role.slice(1)} workspace`
                : "A place for your team"}
            </span>
          </label>
          <button
            className="icon-button"
            title="Create workspace"
            aria-label="Create workspace"
            onClick={() => setForm("workspace")}
          >
            <Plus size={16} />
          </button>
        </div>
        <div className="nav-section-label">WORKSPACE</div>
        <nav className="main-nav" aria-label="Main navigation">
          <button
            className={view === "overview" ? "active" : ""}
            onClick={() => nav("overview")}
          >
            <LayoutDashboard size={18} /> Overview
          </button>
          <button
            className={
              onlyMine && ["board", "list"].includes(view) ? "active" : ""
            }
            onClick={() => nav("list", true)}
          >
            <CircleCheck size={18} /> My tasks{" "}
            <span className="nav-count">
              {
                allTasks.filter(
                  (t) => t.assignee_id === user.id && t.status !== "done",
                ).length
              }
            </span>
          </button>
          <button
            className={view === "activity" ? "active" : ""}
            onClick={() => nav("activity")}
          >
            <ActivityIcon size={18} /> Activity
          </button>
          <button
            className={view === "team" ? "active" : ""}
            onClick={() => nav("team")}
          >
            <Users size={18} /> Team members
          </button>
        </nav>
        <div className="nav-section-label project-label">
          YOUR PROJECTS
          {manager && (
            <button
              className="icon-button"
              aria-label="Create project"
              onClick={() => setForm("project")}
            >
              <Plus size={16} />
            </button>
          )}
        </div>
        <nav className="project-nav" aria-label="Projects">
          {projects.isPending && wid ? (
            <Spinner />
          ) : (
            projects.data?.map((p, i) => (
              <button
                key={p.id}
                className={
                  project?.id === p.id &&
                  ["board", "list"].includes(view) &&
                  !onlyMine
                    ? "active"
                    : ""
                }
                onClick={() => chooseProject(p.id)}
              >
                <span className={`project-dot color-${i % 4}`} />
                <span>{p.name}</span>
                {project?.id === p.id && (
                  <span className="project-active-dot" />
                )}
              </button>
            ))
          )}
          {!projects.isPending && !projects.data?.length && (
            <span className="sidebar-empty">A fresh space for your ideas.</span>
          )}
          {manager && (
            <button className="add-project" onClick={() => setForm("project")}>
              <Plus size={16} /> New project
            </button>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="flow-note">
            <span>
              <Sparkles size={17} /> A little room to grow
            </span>
            <p>
              Big ideas start with
              <br />
              one small task.
            </p>
            <button onClick={() => newTask()} disabled={!project}>
              Make your next move <ArrowUpRight size={14} />
            </button>
          </div>
          <button className="profile-button" onClick={() => setForm("profile")}>
            <Avatar name={user.full_name} />
            <span>
              <strong>{user.full_name}</strong>
              <small>Personal settings</small>
            </span>
            <Settings2 size={16} />
          </button>
        </div>
      </aside>
      <div className="main-shell" inert={isMobile && mobileNav}>
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMobileNav(true)}
            >
              <Menu size={20} />
            </button>
            <FolderOpen size={16} />
            <span>Workspace</span>
            <ChevronRight size={13} />
            <strong>{workspace?.name ?? "Your workspace"}</strong>
          </div>
          <div className="topbar-right">
            <span className={`connection ${health.isError ? "offline" : ""}`}>
              <span />
              {health.isPending
                ? "Connecting…"
                : health.isError
                  ? "Offline"
                  : "Connected"}
            </span>
            <a
              className="topbar-help"
              href={`${(import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "")}/docs`}
              target="_blank"
              rel="noreferrer"
            >
              API docs <ArrowUpRight size={14} />
            </a>
            <button
              className="icon-button"
              aria-label="Sign out"
              title="Sign out"
              onClick={logout}
            >
              <LogOut size={17} />
            </button>
            <button
              className="topbar-avatar"
              aria-label="Open your profile"
              onClick={() => setForm("profile")}
            >
              <Avatar name={user.full_name} small />
            </button>
          </div>
        </header>
        <main className="main-content">
          {workspaces.isPending ? (
            <div className="page-loader">
              <Spinner />
              <p>Opening your workspace…</p>
            </div>
          ) : workspaces.isError ? (
            <ErrorState
              error={workspaces.error}
              retry={() => workspaces.refetch()}
            />
          ) : !workspace ? (
            <div className="welcome-empty">
              <span className="eyebrow">A CLEAN SLATE. A FRESH START.</span>
              <h1>
                Your best work
                <br />
                starts here<span>.</span>
              </h1>
              <p>
                Create a workspace, bring your people together,
                <br />
                and turn that next big idea into a plan.
              </p>
              <button
                className="button primary"
                onClick={() => setForm("workspace")}
              >
                <Plus size={17} /> Create your first workspace
              </button>
              <div className="empty-steps">
                <span>
                  <Folder size={18} /> A space for your team
                </span>
                <span>
                  <Target size={18} /> A plan for your projects
                </span>
                <span>
                  <CheckCheck size={18} /> A little more progress
                </span>
              </div>
            </div>
          ) : (
            <>
              <div className="project-heading">
                <div>
                  <div className="eyebrow">
                    <span className="project-dot color-0" />
                    {view === "team"
                      ? "BETTER TOGETHER"
                      : view === "activity"
                        ? "THE STORY SO FAR"
                        : view === "overview"
                          ? "THE BIG PICTURE"
                          : "LET’S MOVE THINGS FORWARD"}
                  </div>
                  <h1>
                    {view === "team"
                      ? "Your team"
                      : view === "activity"
                        ? "Workspace activity"
                        : view === "overview"
                          ? "Workspace overview"
                          : onlyMine
                            ? "My tasks"
                            : (project?.name ?? "Your next big thing")}
                    <span className="heading-dot">.</span>
                  </h1>
                  <p>
                    {view === "team"
                      ? "The right people. The right space. Great things ahead."
                      : view === "activity"
                        ? "Every little step, all in one place."
                        : view === "overview"
                          ? "A little perspective on everything you’re building together."
                          : onlyMine
                            ? `Your assignments in ${project?.name ?? "this project"}. One thing at a time.`
                            : project?.description ||
                              "Every great project starts with a little direction."}
                  </p>
                </div>
                <div className="heading-actions">
                  {project && ["board", "list"].includes(view) && (
                    <>
                      <div className="member-stack">
                        <Avatar name={user.full_name} small />
                        {(members.data?.length ?? 0) > 1 && (
                          <span className="extra-members">
                            +{members.data!.length - 1}
                          </span>
                        )}
                      </div>
                      <button
                        className="button secondary invite-button"
                        onClick={() => nav("team")}
                      >
                        <Users size={15} /> Team
                      </button>
                      <button
                        className="button primary"
                        onClick={() => newTask()}
                      >
                        <Plus size={17} /> New task
                      </button>
                    </>
                  )}
                </div>
              </div>
              {members.isError && (
                <ErrorState
                  error={members.error}
                  retry={() => members.refetch()}
                />
              )}
              {["board", "list"].includes(view) && (
                <>
                  {projects.isPending ? (
                    <div className="loading-line">
                      <Spinner /> Opening your projects…
                    </div>
                  ) : projects.isError ? (
                    <ErrorState
                      error={projects.error}
                      retry={() => projects.refetch()}
                    />
                  ) : !project ? (
                    <Empty
                      title="Something great starts with a project."
                      action={
                        manager ? (
                          <button
                            className="button primary"
                            onClick={() => setForm("project")}
                          >
                            <Plus size={16} /> Create a project
                          </button>
                        ) : undefined
                      }
                    >
                      {manager
                        ? "Give your idea a name. The rest will follow."
                        : "Your workspace owner or admin can create the first project."}
                    </Empty>
                  ) : (
                    <>
                      <div className="project-summary">
                        <div className="summary-progress">
                          <span
                            className="progress-ring"
                            style={
                              {
                                "--progress": `${percent}%`,
                              } as React.CSSProperties
                            }
                          >
                            <span>{percent}%</span>
                          </span>
                          <div>
                            <strong>Making it happen</strong>
                            <span>
                              {done} of {allTasks.length} tasks complete
                            </span>
                          </div>
                        </div>
                        <div className="summary-divider" />
                        <div className="summary-stat">
                          <span className="stat-icon orange-bg">
                            <Clock3 size={18} />
                          </span>
                          <div>
                            <strong>
                              {
                                allTasks.filter(
                                  (t) => t.status === "in_progress",
                                ).length
                              }{" "}
                              <span>in progress</span>
                            </strong>
                            <span>Good things in the works</span>
                          </div>
                        </div>
                        <div className="summary-divider" />
                        <div className="summary-stat">
                          <span className="stat-icon green-bg">
                            <CircleCheck size={19} />
                          </span>
                          <div>
                            <strong>
                              {done} <span>completed</span>
                            </strong>
                            <span>A little closer every day</span>
                          </div>
                        </div>
                        <span className="summary-note">
                          <Sparkles size={16} /> Small steps. Real progress.
                        </span>
                      </div>
                      <div className="view-bar">
                        <div className="view-tabs">
                          <button
                            className={view === "board" ? "active" : ""}
                            onClick={() => setView("board")}
                          >
                            <LayoutGrid size={16} /> Board{" "}
                            <span>{allTasks.length}</span>
                          </button>
                          <button
                            className={view === "list" ? "active" : ""}
                            onClick={() => setView("list")}
                          >
                            <List size={18} /> List
                          </button>
                        </div>
                        <span className="view-tip">
                          A place for everything. A little more clarity.
                        </span>
                      </div>
                      <div className="filter-bar">
                        <label className="search-field">
                          <Search size={16} />
                          <input
                            placeholder="Search tasks…"
                            aria-label="Search tasks"
                            value={search}
                            onChange={(e) => {
                              setSearch(e.target.value);
                              setPage(0);
                            }}
                          />
                          {search && (
                            <button
                              className="icon-button"
                              aria-label="Clear search"
                              onClick={() => setSearch("")}
                            >
                              <X size={14} />
                            </button>
                          )}
                        </label>
                        <div className="filters">
                          <label className="filter-select">
                            <SlidersHorizontal size={15} />
                            <select
                              aria-label="Filter by priority"
                              value={priority}
                              onChange={(e) => {
                                setPriority(e.target.value);
                                setPage(0);
                              }}
                            >
                              <option value="">Priority</option>
                              {Object.keys(priorityRank).map((p) => (
                                <option key={p} value={p}>
                                  {p[0].toUpperCase() + p.slice(1)}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="filter-select">
                            <Circle size={14} />
                            <select
                              aria-label="Filter by status"
                              value={status}
                              onChange={(e) => {
                                setStatus(e.target.value);
                                setPage(0);
                              }}
                            >
                              <option value="">Status</option>
                              {statuses.map((s) => (
                                <option key={s} value={s}>
                                  {statusLabels[s]}
                                </option>
                              ))}
                            </select>
                          </label>
                          <button
                            className={`filter-chip ${onlyMine ? "selected" : ""}`}
                            onClick={() => {
                              setOnlyMine(!onlyMine);
                              setPage(0);
                            }}
                          >
                            <Users size={15} /> Assigned to me{" "}
                            {onlyMine && <Check size={12} />}
                          </button>
                          <label className="filter-select sort-filter">
                            <ArrowDownWideNarrow size={16} />
                            <select
                              aria-label="Sort tasks"
                              value={sort}
                              onChange={(e) => setSort(e.target.value)}
                            >
                              <option value="created">Newest first</option>
                              <option value="priority">Priority</option>
                              <option value="due">Due date</option>
                            </select>
                          </label>
                        </div>
                      </div>
                      {tasks.isPending ? (
                        <div className="loading-board">
                          {statuses.map((s) => (
                            <div className="skeleton-column" key={s}>
                              <span />
                              <div />
                              <div />
                            </div>
                          ))}
                        </div>
                      ) : tasks.isError ? (
                        <ErrorState
                          error={tasks.error}
                          retry={() => tasks.refetch()}
                        />
                      ) : view === "board" ? (
                        <div className="board">
                          {statuses.map((s) => (
                            <BoardColumn
                              key={s}
                              status={s}
                              tasks={filtered.filter((t) => t.status === s)}
                              user={user}
                              open={setSelectedTask}
                              add={() => newTask(s)}
                              canEdit={canEdit}
                              moving={moving}
                              move={move}
                              onDrop={(id) => {
                                const task = allTasks.find((t) => t.id === id);
                                if (task) move(task, s);
                              }}
                            />
                          ))}
                        </div>
                      ) : (
                        <TaskList
                          tasks={filtered.slice(
                            safePage * 10,
                            safePage * 10 + 10,
                          )}
                          user={user}
                          open={setSelectedTask}
                          canEdit={canEdit}
                          move={move}
                          moving={moving}
                        />
                      )}
                      <div className="board-footer">
                        <span>
                          <span className="tiny-dot" />
                          {filtered.length}{" "}
                          {filtered.length === 1 ? "task" : "tasks"}
                          {search || priority || status || onlyMine
                            ? " match your filters"
                            : " in this project"}
                          {tasks.isFetching && !tasks.isPending && <Spinner />}
                        </span>
                        {view === "board" ? (
                          <span className="drag-tip">
                            Drag a task to move it, or open it to edit.
                          </span>
                        ) : (
                          <div className="pagination">
                            <span>
                              {safePage + 1} /{" "}
                              {Math.max(1, Math.ceil(filtered.length / 10))}
                            </span>
                            <button
                              className="icon-button"
                              aria-label="Previous page"
                              disabled={safePage === 0}
                              onClick={() => setPage(safePage - 1)}
                            >
                              <ChevronLeft size={17} />
                            </button>
                            <button
                              className="icon-button"
                              aria-label="Next page"
                              disabled={(safePage + 1) * 10 >= filtered.length}
                              onClick={() => setPage(safePage + 1)}
                            >
                              <ChevronRight size={17} />
                            </button>
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </>
              )}
              {view === "team" && members.data && (
                <Team
                  workspaceId={workspace.id}
                  members={members.data}
                  user={user}
                  refresh={refresh}
                />
              )}
              {view === "activity" && (
                <div className="workspace-activity">
                  <div className="section-card-head">
                    <h3>Every step forward</h3>
                    <span className="muted">Latest first</span>
                  </div>
                  {activity.isPending ? (
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
              )}
              {view === "overview" && (
                <>
                  {stats.isPending ? (
                    <Spinner />
                  ) : stats.isError ? (
                    <ErrorState
                      error={stats.error}
                      retry={() => stats.refetch()}
                    />
                  ) : (
                    <>
                      <div className="overview-grid">
                        {[
                          {
                            label: "Total tasks",
                            value: stats.data.total,
                            icon: <LayoutGrid size={21} />,
                            text: "All the pieces of your next big thing",
                          },
                          {
                            label: "In progress",
                            value: stats.data.by_status.in_progress,
                            icon: <Clock3 size={21} />,
                            text: "Ideas becoming something real",
                          },
                          {
                            label: "Completed",
                            value: stats.data.by_status.done,
                            icon: <CircleCheck size={21} />,
                            text: "Take a moment to celebrate",
                          },
                          {
                            label: "Overdue",
                            value: stats.data.overdue,
                            icon: <Target size={21} />,
                            text: "A little attention goes a long way",
                          },
                        ].map((item) => (
                          <div className="overview-stat" key={item.label}>
                            <span>
                              {item.label}
                              {item.icon}
                            </span>
                            <strong>{item.value}</strong>
                            <p>{item.text}</p>
                          </div>
                        ))}
                      </div>
                      <div className="overview-projects">
                        <div className="section-card-head">
                          <h3>Your projects</h3>
                          {manager && (
                            <button
                              className="text-button"
                              onClick={() => setForm("project")}
                            >
                              <Plus size={14} /> New project
                            </button>
                          )}
                        </div>
                        {projects.data?.map((p, i) => (
                          <button
                            className="overview-project"
                            key={p.id}
                            onClick={() => chooseProject(p.id)}
                          >
                            <span className={`project-tile tile-${i % 4}`}>
                              <Folder size={21} />
                            </span>
                            <span>
                              <strong>{p.name}</strong>
                              <p>
                                {p.description ||
                                  "A little space for your next big idea."}
                              </p>
                            </span>
                            <ArrowUpRight size={19} />
                          </button>
                        ))}
                        {!projects.data?.length && (
                          <p className="overview-empty">
                            No projects yet. Let’s give that idea a home.
                          </p>
                        )}
                      </div>
                    </>
                  )}
                  {role === "owner" && (
                    <button
                      className="text-button danger-text workspace-delete"
                      onClick={() => setForm("delete-workspace")}
                    >
                      <Trash2 size={14} /> Delete workspace
                    </button>
                  )}
                </>
              )}
            </>
          )}
        </main>
        <footer className="app-footer">
          <span>LESS BUSYWORK. MORE GOOD WORK.</span>
          <span>
            Made for your next big thing{" "}
            <span className="footer-spark">✳</span>
          </span>
        </footer>
      </div>
      {form && (
        <AppForm
          key={form}
          type={form}
          user={user}
          workspace={workspace}
          project={project}
          members={members.data ?? []}
          initialStatus={initialStatus}
          close={() => setForm(null)}
          refresh={refresh}
          onWorkspace={chooseWorkspace}
          onProject={chooseProject}
        />
      )}
      {selectedTask && (
        <TaskPanel
          key={selectedTask.id}
          task={selectedTask}
          members={members.data ?? []}
          user={user}
          close={() => setSelectedTask(null)}
          refresh={refresh}
        />
      )}
    </div>
  );
}

function BoardColumn({
  status,
  tasks,
  user,
  open,
  add,
  canEdit,
  moving,
  move,
  onDrop,
}: {
  status: Status;
  tasks: Task[];
  user: User;
  open: (task: Task) => void;
  add: () => void;
  canEdit: (task: Task) => boolean;
  moving: string | null;
  move: (task: Task, next: Status) => void;
  onDrop: (id: string) => void;
}) {
  const [over, setOver] = useState(false);
  return (
    <section
      className={`board-column column-${status} ${over ? "drag-over" : ""}`}
      aria-label={statusLabels[status]}
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        setOver(true);
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setOver(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        onDrop(e.dataTransfer.getData("text/plain"));
      }}
    >
      <div className="column-head">
        <span className={`status-dot ${status}`} />
        <h2>{statusLabels[status]}</h2>
        <span className="column-count">{tasks.length}</span>
        <button
          className="icon-button"
          aria-label={`Add task to ${statusLabels[status]}`}
          onClick={add}
        >
          <Plus size={17} />
        </button>
      </div>
      <div className="column-cards">
        {tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            user={user}
            open={() => open(task)}
            canEdit={canEdit(task)}
            moving={moving === task.id}
            complete={() =>
              move(task, task.status === "done" ? "todo" : "done")
            }
          />
        ))}
        <button className="column-add" onClick={add}>
          <Plus size={15} /> Add task
        </button>
      </div>
    </section>
  );
}

function TaskCard({
  task,
  user,
  open,
  canEdit,
  moving,
  complete,
}: {
  task: Task;
  user: User;
  open: () => void;
  canEdit: boolean;
  moving: boolean;
  complete: () => void;
}) {
  const overdue =
    task.due_at &&
    new Date(task.due_at).getTime() < Date.now() &&
    task.status !== "done";
  return (
    <article
      className={`task-card ${moving ? "is-moving" : ""}`}
      draggable={canEdit && !moving}
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", task.id);
        e.dataTransfer.effectAllowed = "move";
      }}
    >
      <div className="card-top">
        <span className={`priority-badge priority-${task.priority}`}>
          <span className="priority-bars">
            <i />
            <i />
            <i />
          </span>
          {task.priority[0].toUpperCase() + task.priority.slice(1)}
        </span>
        <span className="task-code">
          TF-{task.id.slice(0, 4).toUpperCase()}
        </span>
      </div>
      <button className="task-open" onClick={open}>
        <h3 className={task.status === "done" ? "completed-title" : ""}>
          {task.title}
        </h3>
        <p>{task.description || "A little idea, ready for its next step."}</p>
      </button>
      <div className="card-footer">
        <span className={`card-date ${overdue ? "overdue" : ""}`}>
          <Clock3 size={13} />
          {formatDate(task.due_at)}
        </span>
        <div className="card-people">
          {canEdit && (
            <button
              className={`complete-button ${task.status === "done" ? "is-done" : ""}`}
              disabled={moving}
              onClick={complete}
              aria-label={`${task.status === "done" ? "Reopen" : "Complete"} ${task.title}`}
              title={task.status === "done" ? "Reopen task" : "Mark complete"}
            >
              {moving ? (
                <Spinner />
              ) : task.status === "done" ? (
                <CircleCheck size={17} />
              ) : (
                <Circle size={17} />
              )}
            </button>
          )}
          {task.assignee_id ? (
            <Avatar
              name={
                task.assignee_id === user.id
                  ? user.full_name
                  : task.assignee_id.slice(0, 2)
              }
              small
            />
          ) : (
            <span className="unassigned" title="Unassigned">
              <Users size={13} />
            </span>
          )}
        </div>
      </div>
    </article>
  );
}

function TaskList({
  tasks,
  user,
  open,
  canEdit,
  moving,
  move,
}: {
  tasks: Task[];
  user: User;
  open: (task: Task) => void;
  canEdit: (task: Task) => boolean;
  moving: string | null;
  move: (task: Task, next: Status) => void;
}) {
  return tasks.length ? (
    <div className="table-scroll">
      <table className="task-table">
        <thead>
          <tr>
            <th>Task name</th>
            <th>Status</th>
            <th>Priority</th>
            <th>Due date</th>
            <th>Assignee</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.id}>
              <td>
                <button className="table-task-title" onClick={() => open(task)}>
                  {task.status === "done" ? (
                    <CircleCheck size={17} className="green-text" />
                  ) : (
                    <Circle size={17} />
                  )}
                  <span>
                    {task.title}
                    <small>TF-{task.id.slice(0, 4).toUpperCase()}</small>
                  </span>
                </button>
              </td>
              <td>
                <select
                  className={`inline-status ${task.status}`}
                  aria-label={`Status of ${task.title}`}
                  value={task.status}
                  disabled={!canEdit(task) || moving === task.id}
                  onChange={(e) => move(task, e.target.value as Status)}
                >
                  {statuses.map((s) => (
                    <option key={s} value={s}>
                      {statusLabels[s]}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <span className={`priority-badge priority-${task.priority}`}>
                  {task.priority}
                </span>
              </td>
              <td className="muted">{formatDate(task.due_at)}</td>
              <td>
                {task.assignee_id ? (
                  <Avatar
                    name={
                      task.assignee_id === user.id
                        ? user.full_name
                        : task.assignee_id.slice(0, 2)
                    }
                    small
                  />
                ) : (
                  <span className="muted">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty title="A little breathing room.">
      No tasks match these filters. Try a different search or start something
      new.
    </Empty>
  );
}

function AppForm({
  type,
  user,
  workspace,
  project,
  members,
  initialStatus,
  close,
  refresh,
  onWorkspace,
  onProject,
}: {
  type: Exclude<FormType, null>;
  user: User;
  workspace?: Workspace;
  project?: Project;
  members: Member[];
  initialStatus: Status;
  close: () => void;
  refresh: () => Promise<void>;
  onWorkspace: (id: string) => void;
  onProject: (id: string) => void;
}) {
  const action = useAction();
  const toast = useToast();
  const titles = {
    workspace: "A space for something great",
    project: "Give your next idea a home",
    task: "One small step forward",
    profile: "Make yourself at home",
    "delete-workspace": "Delete this workspace?",
  };
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const element = event.currentTarget;
    const data = new FormData(element);
    await action.run(async () => {
      if (type === "workspace") {
        const w = await post<Workspace>("/workspaces", {
          name: data.get("name"),
        });
        await refresh();
        onWorkspace(w.id);
        toast("Your workspace is ready. Make it yours.");
      }
      if (type === "project" && workspace) {
        const p = await post<Project>(`/workspaces/${workspace.id}/projects`, {
          name: data.get("name"),
          description: data.get("description"),
        });
        await refresh();
        onProject(p.id);
        toast("A new project. A fresh start.");
      }
      if (type === "task" && project) {
        await post(`/projects/${project.id}/tasks`, taskInput(element));
        await refresh();
        toast("Task added. Let’s make it happen.");
      }
      if (type === "profile") {
        await patch("/users/me", { full_name: data.get("full_name") });
        await refresh();
        toast("Profile updated.");
      }
      if (type === "delete-workspace" && workspace) {
        if (data.get("confirmation") !== workspace.name)
          throw new Error("Enter the exact workspace name to confirm.");
        await remove(`/workspaces/${workspace.id}`);
        await refresh();
        onWorkspace("");
        toast("Workspace deleted.");
      }
      close();
    });
  }
  return (
    <Modal
      title={titles[type]}
      subtitle={
        type === "task"
          ? project?.name
          : type === "profile"
            ? "Your corner of the workspace."
            : undefined
      }
      close={close}
    >
      <form className="stack-form modal-form" onSubmit={submit}>
        {(type === "workspace" || type === "project") && (
          <label>
            {type === "workspace" ? "Workspace" : "Project"} name
            <input
              name="name"
              placeholder={
                type === "workspace"
                  ? "e.g. The creative studio"
                  : "e.g. Website launch"
              }
              required
              maxLength={120}
              autoFocus
            />
          </label>
        )}
        {type === "project" && (
          <label>
            Description
            <textarea
              name="description"
              placeholder="What are we working toward?"
              maxLength={10000}
              rows={3}
            />
          </label>
        )}
        {type === "task" && (
          <TaskFields
            members={members}
            user={user}
            initialStatus={initialStatus}
          />
        )}
        {type === "profile" && (
          <>
            <div className="profile-banner">
              <Avatar name={user.full_name} />
              <div>
                <strong>{user.full_name}</strong>
                <span>{user.email}</span>
              </div>
            </div>
            <label>
              Full name
              <input
                name="full_name"
                defaultValue={user.full_name}
                required
                maxLength={120}
              />
            </label>
            <label>
              Your user ID
              <div className="copy-field">
                <input readOnly value={user.id} aria-label="Your user ID" />
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Copy user ID"
                  onClick={() =>
                    action.run(async () => {
                      await navigator.clipboard.writeText(user.id);
                      toast("User ID copied.");
                    })
                  }
                >
                  <Copy size={16} />
                </button>
              </div>
              <span className="field-hint">
                Share this with a workspace owner or admin to join their team.
              </span>
            </label>
          </>
        )}
        {type === "delete-workspace" && (
          <>
            <p className="delete-warning">
              All projects, tasks, comments, reminders, and activity in{" "}
              <strong>{workspace?.name}</strong> will be permanently deleted.
            </p>
            <label>
              Type the workspace name to confirm
              <input
                name="confirmation"
                required
                placeholder={workspace?.name}
                onChange={(e) =>
                  e.currentTarget.setCustomValidity(
                    e.target.value === workspace?.name
                      ? ""
                      : "Enter the exact workspace name",
                  )
                }
              />
            </label>
          </>
        )}
        <div className="form-actions">
          <button type="button" className="button secondary" onClick={close}>
            Cancel
          </button>
          {type === "delete-workspace" ? (
            <button className="button danger" disabled={action.busy}>
              {action.busy ? <Spinner /> : <Trash2 size={15} />} Delete
              workspace
            </button>
          ) : (
            <SaveButton busy={action.busy}>
              {type === "profile"
                ? "Save changes"
                : type === "task"
                  ? "Create task"
                  : type === "project"
                    ? "Create project"
                    : "Create workspace"}
            </SaveButton>
          )}
        </div>
      </form>
    </Modal>
  );
}
