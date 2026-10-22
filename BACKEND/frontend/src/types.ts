export type Role = "owner" | "admin" | "member";
export type Status = "todo" | "in_progress" | "blocked" | "done";
export type Priority = "low" | "medium" | "high" | "urgent";
export interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
}
export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}
export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  description: string;
  created_by: string;
  created_at: string;
}
export interface Member {
  user_id: string;
  workspace_id: string;
  role: Role;
  joined_at: string;
}
export interface Task {
  id: string;
  project_id: string;
  workspace_id: string;
  title: string;
  description: string;
  status: Status;
  priority: Priority;
  assignee_id: string | null;
  creator_id: string;
  due_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}
export interface Comment {
  id: string;
  task_id: string;
  author_id: string;
  body: string;
  created_at: string;
}
export interface Activity {
  id: string;
  actor_id: string;
  task_id: string | null;
  action: string;
  payload: Record<string, unknown>;
  created_at: string;
}
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
export interface Stats {
  total: number;
  overdue: number;
  by_status: Record<Status, number>;
}
export interface TaskInput {
  title: string;
  description: string;
  status: Status;
  priority: Priority;
  assignee_id: string | null;
  due_at: string | null;
}
