import type { Page } from "./types";

const TOKEN_KEY = "taskflow.session.v1";
const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
export const session = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (token: string) => sessionStorage.setItem(TOKEN_KEY, token),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = session.get();
  let response: Response;
  try {
    response = await fetch(`${API_ORIGIN}/api/v1${path}`, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError(
      0,
      "Cannot reach TaskFlow. Check your connection and try again.",
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map(
                (e: { msg: string; loc: string[] }) =>
                  `${e.loc.slice(1).join(".")}: ${e.msg}`,
              )
              .join("; ")
          : "Something went wrong. Please try again.";
    if (response.status === 401 && token) {
      session.clear();
      window.dispatchEvent(new Event("taskflow:expired"));
    }
    throw new ApiError(response.status, message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const post = <T>(path: string, data: unknown) =>
  api<T>(path, { method: "POST", body: JSON.stringify(data) });
export const patch = <T>(path: string, data: unknown) =>
  api<T>(path, { method: "PATCH", body: JSON.stringify(data) });
export const remove = (path: string) => api<void>(path, { method: "DELETE" });

export async function allPages<T>(path: string): Promise<T[]> {
  const items: T[] = [];
  let total = 1;
  while (items.length < total) {
    const page = await api<Page<T>>(
      `${path}${path.includes("?") ? "&" : "?"}limit=100&offset=${items.length}`,
    );
    items.push(...page.items);
    total = page.total;
    if (!page.items.length) break;
  }
  return items;
}

export function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Please try again.";
}
