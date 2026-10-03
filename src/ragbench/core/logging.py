"""Structured logging configuration with automated zero-leakage secret masking."""
import logging
import sys
from ragbench.core.config import settings


class SecretRedactingFilter(logging.Filter):
    """Logging filter that automatically scrubs sensitive API keys from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        from ragbench.core.tracing import redact_text
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: redact_text(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_text(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
        return True


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(settings.APP_NAME)
    logger.setLevel(settings.LOG_LEVEL.upper())

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(SecretRedactingFilter())
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()