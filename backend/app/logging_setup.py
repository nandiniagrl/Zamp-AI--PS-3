"""Logging with a filter that redacts anything that looks like an API key or bearer token."""
import logging
import re

_SECRET = re.compile(r"(gsk_[A-Za-z0-9]{8,}|tvly-[A-Za-z0-9-]{8,}|Bearer\s+[A-Za-z0-9._-]{10,})")


def redact(text: str) -> str:
    return _SECRET.sub("[REDACTED]", text)


class RedactSecrets(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(str(record.msg))
        if record.args:
            record.args = tuple(redact(str(a)) for a in record.args)
        return True


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for handler in logging.getLogger().handlers:
        handler.addFilter(RedactSecrets())
    logging.getLogger("httpx").setLevel(logging.WARNING)  # avoid logging request URLs/headers
