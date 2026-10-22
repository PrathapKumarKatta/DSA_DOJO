from app.rag.secret_filter import (
    contains_secrets,
    is_sensitive_filename,
    redact_secrets,
)


def test_is_sensitive_filename():
    assert is_sensitive_filename(".env") is True
    assert is_sensitive_filename(".env.production") is True
    assert is_sensitive_filename("config/credentials.json") is True
    assert is_sensitive_filename("certs/server.pem") is True
    assert is_sensitive_filename("ssh/id_rsa") is True
    assert is_sensitive_filename("app/main.py") is False
    assert is_sensitive_filename("docs/readme.md") is False


def test_contains_and_redact_secrets():
    content = """
    # Configuration
    api_key = "sk-abcdef1234567890abcdef1234567890"
    github_token = "ghp_1234567890abcdef1234567890abcdef1234"
    normal_code = "hello world"
    """
    has_secret, found_types = contains_secrets(content)
    assert has_secret is True
    assert len(found_types) >= 2

    redacted = redact_secrets(content)
    assert "sk-" not in redacted
    assert "ghp_" not in redacted
    assert "REDACTED" in redacted
    assert "hello world" in redacted
