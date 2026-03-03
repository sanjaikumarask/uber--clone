import json
import logging
import traceback
from django.utils.timezone import now

class JSONFormatter(logging.Formatter):
    """
    Standard Structured Logging Formatter for production observability.
    Outputs logs in JSON format for easy ingestion by Datadog/ELK/Sentry.
    """
    def format(self, record):
        log_data = {
            "timestamp": now().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
            "process": record.process,
            "thread": record.threadName,
        }

        # ── FULL OBSERVABILITY: Trace ID ──
        # Pulls from the TracingMiddleware/Celery Signals 
        from apps.common.resilience import get_trace_id
        log_data["trace_id"] = getattr(record, "trace_id", get_trace_id())

        # ── RED METRICS DATA ──
        # Duration: If record has 'elapsed_ms'
        if hasattr(record, "elapsed_ms"):
            log_data["duration_ms"] = record.elapsed_ms
        
        # Error: Captured if level >= ERROR
        log_data["is_error"] = record.levelno >= logging.ERROR

        # Handle extra context
        if hasattr(record, "ride_id"):
            log_data["ride_id"] = record.ride_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "driver_id"):
            log_data["driver_id"] = record.driver_id

        # Include exception data
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

def setup_logger(name, level=logging.INFO):
    """
    Helper to get a logger with consistent production standards.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger


class RedisLogHandler(logging.Handler):
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
            from django.core.cache import cache
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
