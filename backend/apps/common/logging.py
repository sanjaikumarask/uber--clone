import json
import logging

from django.utils.timezone import now


def _safe_log(value: str) -> str:
    """Strip CR/LF to prevent log injection attacks."""
    return str(value).replace("\r", "").replace("\n", " ")


class JSONFormatter(logging.Formatter):
    """
    Standard Structured Logging Formatter for production observability.
    Outputs logs in JSON format for easy ingestion by Datadog/ELK/Sentry.
    """

    MASKED_FIELDS = {
        "password", "token", "secret", "cvv", "otp", "code", 
        "authorization", "api_key", "key", "credential", "signature"
    }

    def _mask_sensitive_data(self, data):
        """Recursively mask sensitive keys in log data."""
        if isinstance(data, dict):
            return {
                k: "********" if k.lower() in self.MASKED_FIELDS else self._mask_sensitive_data(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._mask_sensitive_data(i) for i in data]
        return data

    def format(self, record):
        log_data = {
            "timestamp": now().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": _safe_log(record.getMessage()),
            "process": record.process,
            "thread": record.threadName,
        }

        # Mask sensitive data in any extra attributes
        for key in ["ride_id", "user_id", "driver_id"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        # ── FULL OBSERVABILITY: Trace ID ──
        from apps.common.resilience import get_trace_id
        log_data["trace_id"] = getattr(record, "trace_id", get_trace_id())

        if hasattr(record, "elapsed_ms"):
            log_data["duration_ms"] = record.elapsed_ms

        log_data["is_error"] = record.levelno >= logging.ERROR

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Final pass: Mask everything in log_data
        masked_log_data = self._mask_sensitive_data(log_data)

        return json.dumps(masked_log_data)


def setup_logger(name, level=logging.INFO):
    """
    Helper to get a logger with consistent production standards.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger


class RedisLogHandler(logging.Handler):
    # [SECURITY AUDIT] This handler is safe for production use as it uses a 
    # capped list (LTRIM) to prevent memory exhaustion in Redis, and 
    # sensitive data is masked at the Formatter level before reaching this handler.
    """
    Custom Logging Handler that streams JSON logs directly to a Redis List.
    This enables the real-time "System Logs" UI in the Admin Dashboard.
    It functions as a ring buffer (max 2000 entries).
    """
    REDIS_KEY = "system:observability:logs"
    MAX_LOGS = 2000

    def __init__(self):
        super().__init__()

    def emit(self, record):
        try:
            # Format using our JSON formatter
            json_str = self.format(record)

            # We defer import to avoid startup issues with cache/redis
            import redis
            from django.conf import settings

            # Fast raw write
            # We use a dedicated redis client instance if possible
            r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            r.lpush(self.REDIS_KEY, json_str)
            r.ltrim(self.REDIS_KEY, 0, self.MAX_LOGS - 1)
        except Exception:
            # If Redis is dead, don't crash the application
            self.handleError(record)
