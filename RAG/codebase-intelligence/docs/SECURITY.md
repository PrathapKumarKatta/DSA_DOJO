# Security Architecture & Threat Model

Codebase repositories uploaded by developers are treated as **untrusted data**.

---

## 1. Threat Vectors and Mitigations

| Threat | Risk Level | Mitigation in Codebase Intelligence |
|---|---|---|
| **Zip Slip Path Traversal** | Critical | Entries with `..` or absolute paths (`/`) are rejected before extraction. Target paths are verified to strictly reside inside the designated sandbox directory using `Path.is_relative_to()`. |
| **Symlink Extraction Attacks** | High | Zip entry attributes are inspected (`external_attr >> 16 & 0o120000`). Any symlink or hardlink is immediately blocked. |
| **ZIP Bomb (Decompression Denial of Service)** | High | Per-entry compression ratios (> 100:1 for > 10MB) and cumulative uncompressed size limits (`MAX_EXTRACTED_SIZE_MB = 150MB`) are checked on header read. |
| **Malicious Code Execution** | Critical | **Uploaded code is never executed.** It is parsed purely as passive AST syntax trees by Tree-sitter in user space. |
| **Credential / Secret Leakage** | High | Two-stage secret protection: (1) Files like `.env`, `.pem`, `id_rsa`, and `credentials.json` are excluded from ingestion; (2) Regex patterns redact API tokens before any prompt is assembled for an LLM. |
| **Prompt Injection via Code** | Medium | Code snippets are enclosed inside explicit XML tags `<source_code_context>` with strict system prompt directives instructing the model to treat all code text as passive data, ignoring embedded instructions. |
| **Cross-Tenant Data Exposure** | Critical | Strict object-level authorization: All SQL queries join against `project.user_id == current_user.id`. Vector searches require `WHERE project_id = :project_id`. |

---

## 2. Authentication & Session Security

- **Password Hashing**: Direct `bcrypt` with random salt and automatic 72-byte safe truncation.
- **Tokens**: Short-lived JWT access tokens (HMAC SHA-256) signed with a minimum 32-character secret key.
- **CORS**: Explicit allowlist configuration restricting requests to authorized frontend origins.
- **Logging Safety**: Loggers implement sensitive keyword masking to prevent tokens and passwords from appearing in standard application logs.
