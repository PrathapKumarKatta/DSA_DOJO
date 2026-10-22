# REST API Documentation

All protected endpoints require an `Authorization: Bearer <token>` header obtained from `/api/v1/auth/login`.

Base URL: `http://localhost:8000/api/v1` (Swagger UI at `/api/v1/docs`)

---

## 1. Authentication Endpoints

### `POST /auth/register`
Create a new user account.
```json
// Request Body
{
  "email": "developer@company.com",
  "password": "Password123!"
}
// Response 201 Created
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "email": "developer@company.com",
  "created_at": "2026-10-22T09:00:00Z"
}
```

### `POST /auth/login`
Authenticate credentials and obtain JWT access token.
```json
// Request Body
{
  "email": "developer@company.com",
  "password": "Password123!"
}
// Response 200 OK
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

### `GET /auth/me`
Retrieve currently authenticated user profile.
```json
// Response 200 OK
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "email": "developer@company.com",
  "created_at": "2026-10-22T09:00:00Z"
}
```

---

## 2. Project Endpoints

### `POST /projects`
Create a new codebase project.
```json
// Request Body
{
  "name": "payment-microservice"
}
```

### `GET /projects`
List all projects belonging to the authenticated user.
```json
// Response 200 OK
{
  "items": [
    {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "payment-microservice",
      "status": "ready",
      "file_count": 8,
      "chunk_count": 24,
      "created_at": "2026-10-22T09:10:00Z",
      "updated_at": "2026-10-22T09:12:00Z"
    }
  ],
  "total": 1
}
```

### `GET /projects/{id}`
Retrieve a single project by ID.

### `DELETE /projects/{id}`
Delete a project and cascade-delete all indexed files, vectors, chunks, and chats.

---

## 3. Ingestion & File Endpoints

### `POST /projects/{id}/upload`
Upload a codebase `.zip` archive. Dispatches asynchronous background ingestion.
- **Content-Type**: `multipart/form-data`
- **Field**: `file` (`.zip` format, max 50MB)
```json
// Response 202 Accepted
{
  "id": "1efdd7c5-9675-4c63-aaac-7a22b3619cd6",
  "project_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "pending",
  "processed_files": 0,
  "total_files": 0,
  "error_message": null,
  "created_at": "2026-10-22T09:15:00Z"
}
```

### `GET /projects/{id}/status`
Poll indexing progress and state.
```json
// Response 200 OK
{
  "project_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "project_status": "ready",
  "active_job": {
    "id": "1efdd7c5-9675-4c63-aaac-7a22b3619cd6",
    "project_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "completed",
    "processed_files": 8,
    "total_files": 8
  }
}
```

### `GET /projects/{id}/files`
List all source files extracted and indexed for this project.

### `GET /projects/{id}/files/{file_id}`
Retrieve the full source code content and line count of a specific file.

---

## 4. Search and RAG Chat

### `POST /projects/{id}/search`
Execute vector similarity, full-text keyword, or hybrid search.
```json
// Request Body
{
  "query": "authenticate_user",
  "top_k": 3,
  "use_reranker": false
}
```

### `POST /projects/{id}/chat`
Ask natural language questions about codebase architecture and implementation.
```json
// Request Body
{
  "message": "Where is user authentication implemented?",
  "conversation_id": null,
  "top_k": 5
}
// Response 200 OK
{
  "conversation_id": "99bb88aa-1234-5678-abcd-ef0123456789",
  "message": {
    "id": "message-uuid",
    "role": "assistant",
    "content": "Authentication is implemented in auth/service.py between lines 25–40...",
    "citations": [
      {
        "file_path": "auth/service.py",
        "start_line": 25,
        "end_line": 40,
        "chunk_id": "chunk-uuid"
      }
    ],
    "created_at": "2026-10-22T09:20:00Z"
  }
}
```

### `GET /projects/{id}/conversations`
List all conversation threads in the project.

### `GET /conversations/{id}/messages`
Retrieve message history and source citations for a conversation.

---

## 5. Health Endpoints

### `GET /health/live`
Kubernetes liveness probe. Returns `{ "status": "ok" }`.

### `GET /health/ready`
Kubernetes readiness probe. Returns database and Redis connection statuses.
