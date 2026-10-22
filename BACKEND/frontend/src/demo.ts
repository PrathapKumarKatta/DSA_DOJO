import { post, session } from "./api";
import type { Project, Status, Priority, User, Workspace } from "./types";

export async function createDemo() {
  const unique = crypto.randomUUID().slice(0, 8);
  const password = crypto.randomUUID() + "Aa1!";
  const email = `alex-${unique}@example.com`;
  const user = await post<User>("/auth/register", {
    email,
    password,
    full_name: "Alex Morgan",
  });
  const login = await post<{ access_token: string }>("/auth/login", {
    email,
    password,
  });
  session.set(login.access_token);
  const workspace = await post<Workspace>("/workspaces", {
    name: "Studio workspace",
  });
  await post(`/workspaces/${workspace.id}/projects`, {
    name: "Product roadmap",
    description: "The next chapter. Shape ideas into work that matters.",
  });
  const project = await post<Project>(`/workspaces/${workspace.id}/projects`, {
    name: "Website launch",
    description:
      "A fresh look. A better experience. Let’s bring our new website to life.",
  });
  const tasks: [string, string, Status, Priority, number][] = [
    [
      "Map out the customer journey",
      "Connect the dots between discovery, exploration, and that first happy purchase.",
      "todo",
      "high",
      2,
    ],
    [
      "Write the homepage copy",
      "A clear story that sounds like us. Keep it human, helpful, and a little unexpected.",
      "todo",
      "medium",
      3,
    ],
    [
      "Explore mobile navigation",
      "Find a simple, thumb-friendly way to get around.",
      "todo",
      "low",
      5,
    ],
    [
      "Design the landing page",
      "Bring the new brand direction into a thoughtful, welcoming first impression.",
      "in_progress",
      "high",
      1,
    ],
    [
      "Build the component library",
      "Reusable buttons, inputs, and cards. Make the little details feel consistent.",
      "in_progress",
      "medium",
      4,
    ],
    [
      "Finalize brand assets",
      "Waiting on the final logo exports and updated photography from the creative team.",
      "blocked",
      "urgent",
      -1,
    ],
    [
      "Run the accessibility audit",
      "Review contrast, keyboard navigation, and screen reader announcements.",
      "blocked",
      "high",
      3,
    ],
    [
      "Kick off the project",
      "Align on the goal, the timeline, and what success looks like.",
      "done",
      "medium",
      -4,
    ],
    [
      "Gather design inspiration",
      "A shared collection of references, ideas, and things we love.",
      "done",
      "low",
      -2,
    ],
  ];
  for (const [title, description, status, priority, days] of tasks) {
    const due = new Date();
    due.setDate(due.getDate() + days);
    due.setHours(17, 0, 0, 0);
    await post(`/projects/${project.id}/tasks`, {
      title,
      description,
      status,
      priority,
      assignee_id: user.id,
      due_at: due.toISOString(),
    });
  }
  return user;
}
