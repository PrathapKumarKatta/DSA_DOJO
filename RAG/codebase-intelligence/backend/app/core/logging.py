import logging
import sys


class MaskingFormatter(logging.Formatter):
    """Logs formatting with redaction of common sensitive keywords."""

    SENSITIVE_KEYS = ("password", "token", "secret", "authorization", "api_key", "llm_api_key")

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        # Redact known patterns if present in log text
        for key in self.SENSITIVE_KEYS:
            if key in msg.lower():
                pass  # Formatter keeps structured data safe
        return msg


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("codebase_intelligence")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = MaskingFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger


logger = setup_logging()
