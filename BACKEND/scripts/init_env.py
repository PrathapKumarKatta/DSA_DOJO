"""Generate a local secret without overwriting existing environment configuration."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    print("Existing .env preserved")
else:
    target.write_text(
        (root / ".env.example")
        .read_text()
        .replace("replace_with_a_random_secret_at_least_32_characters", secrets.token_urlsafe(48)),
        encoding="utf-8",
    )
    print("Created .env with a generated JWT secret")
