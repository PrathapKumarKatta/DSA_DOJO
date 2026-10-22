import re
from typing import List, Tuple, Set

# Regex patterns for detecting API keys, private keys, and tokens
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "Private Key"),
    (re.compile(r"-----BEGIN CERTIFICATE-----"), "Certificate"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,60}"), "OpenAI/Anthropic API Key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"github_pat_[a-zA-Z0-9_]{50,100}"), "GitHub Fine-Grained Token"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key"),
    (re.compile(r"(?i)(bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*)"), "Bearer Token"),
    (re.compile(r"(?i)(api[_-]?key\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"])"), "API Key assignment"),
    (re.compile(r"(?i)(secret[_-]?key\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"])"), "Secret Key assignment"),
    (re.compile(r"(?i)(password\s*[:=]\s*['\"][^\n'\"]{8,}['\"])"), "Hardcoded Password"),
]

BLOCKED_FILENAMES: Set[str] = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.staging",
    "id_rsa",
    "id_dsa",
    "id_ed25519",
    "id_ecdsa",
    "credentials.json",
    "service-account.json",
    "client_secrets.json",
    "keystore.jks",
}

BLOCKED_EXTENSIONS: Set[str] = {
    ".pem",
    ".key",
    ".pfx",
    ".p12",
    ".pkcs12",
    ".cert",
    ".crt",
    ".der",
}


def is_sensitive_filename(file_path: str) -> bool:
    """Check if the filename itself is known to contain secrets or credentials."""
    from pathlib import PurePosixPath

    p = PurePosixPath(file_path)
    name = p.name.lower()

    if name in BLOCKED_FILENAMES or name.startswith(".env."):
        return True

    for ext in BLOCKED_EXTENSIONS:
        if name.endswith(ext):
            return True

    return False


def contains_secrets(content: str) -> Tuple[bool, List[str]]:
    """Scan string content for sensitive patterns."""
    found = []
    for pattern, name in SECRET_PATTERNS:
        if pattern.search(content):
            found.append(name)
    return len(found) > 0, found


def redact_secrets(content: str) -> str:
    """Redact any sensitive patterns before sending to an LLM."""
    sanitized = content
    for pattern, name in SECRET_PATTERNS:
        sanitized = pattern.sub(f"[REDACTED_{name.upper().replace(' ', '_')}]", sanitized)
    return sanitized
