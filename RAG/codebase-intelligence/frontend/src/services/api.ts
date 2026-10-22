import {
  AuthTokens,
  Conversation,
  ConversationDetail,
  Message,
  Project,
  ProjectStatus,
  SearchResultChunk,
  SourceFile,
  SourceFileDetail,
  User,
} from "../types";

const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
const BASE_URL = `${API_ORIGIN}/api/v1`;

export function getToken(): string | null {
  return localStorage.getItem("codebase_access_token");
}

export function setToken(token: string): void {
  localStorage.setItem("codebase_access_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("codebase_access_token");
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return {} as T;
  }

  if (!response.ok) {
    let errorMessage = "An unexpected error occurred";
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      errorMessage = response.statusText || errorMessage;
    }

    if (response.status === 401) {
      clearToken();
    }

    throw new Error(errorMessage);
  }

  return response.json();
}

export const api = {
  // Auth
  register: (email: string, password: string): Promise<User> =>
    request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string): Promise<AuthTokens> =>
    request<AuthTokens>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  getMe: (): Promise<User> => request<User>("/auth/me"),

  // Projects
  createProject: (name: string): Promise<Project> =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  listProjects: (): Promise<{ items: Project[]; total: number }> =>
    request<{ items: Project[]; total: number }>("/projects"),

  getProject: (id: string): Promise<Project> => request<Project>(`/projects/${id}`),

  deleteProject: (id: string): Promise<void> =>
    request<void>(`/projects/${id}`, { method: "DELETE" }),

  // Ingestion
  uploadCodebase: (projectId: string, file: File): Promise<any> => {
    const formData = new FormData();
    formData.append("file", file);
    return request<any>(`/projects/${projectId}/upload`, {
      method: "POST",
      body: formData,
    });
  },

  getProjectStatus: (projectId: string): Promise<ProjectStatus> =>
    request<ProjectStatus>(`/projects/${projectId}/status`),

  // Files
  listFiles: (projectId: string): Promise<{ items: SourceFile[]; total: number }> =>
    request<{ items: SourceFile[]; total: number }>(`/projects/${projectId}/files`),

  getFileDetail: (projectId: string, fileId: string): Promise<SourceFileDetail> =>
    request<SourceFileDetail>(`/projects/${projectId}/files/${fileId}`),

  // Search
  search: (
    projectId: string,
    query: string,
    topK: number = 5,
    useReranker: boolean = false
  ): Promise<{ query: string; total: number; results: SearchResultChunk[] }> =>
    request<{ query: string; total: number; results: SearchResultChunk[] }>(
      `/projects/${projectId}/search`,
      {
        method: "POST",
        body: JSON.stringify({ query, top_k: topK, use_reranker: useReranker }),
      }
    ),

  // Chat
  chat: (
    projectId: string,
    message: string,
    conversationId?: string,
    topK: number = 5,
    useReranker: boolean = false
  ): Promise<{ conversation_id: string; message: Message }> =>
    request<{ conversation_id: string; message: Message }>(`/projects/${projectId}/chat`, {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        top_k: topK,
        use_reranker: useReranker,
      }),
    }),

  listConversations: (projectId: string): Promise<Conversation[]> =>
    request<Conversation[]>(`/projects/${projectId}/conversations`),

  getConversationMessages: (conversationId: string): Promise<ConversationDetail> =>
    request<ConversationDetail>(`/conversations/${conversationId}/messages`),
};
