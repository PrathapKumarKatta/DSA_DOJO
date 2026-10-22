export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  status: "created" | "processing" | "ready" | "failed";
  file_count: number;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface SourceFile {
  id: string;
  project_id: string;
  path: string;
  language: string;
  line_count: number;
  size_bytes: number;
  created_at: string;
}

export interface SourceFileDetail extends SourceFile {
  content: string;
}

export interface IngestionJob {
  id: string;
  project_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  processed_files: number;
  total_files: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface ProjectStatus {
  project_id: string;
  project_status: string;
  active_job?: IngestionJob;
}

export interface SearchResultChunk {
  chunk_id: string;
  source_file_id: string;
  file_path: string;
  symbol_name?: string;
  chunk_type: string;
  start_line: number;
  end_line: number;
  content: string;
  score: number;
  retrieval_method: string;
}

export interface Citation {
  chunk_id?: string;
  file_path: string;
  start_line: number;
  end_line: number;
  snippet?: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface Conversation {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  message_count: number;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}
