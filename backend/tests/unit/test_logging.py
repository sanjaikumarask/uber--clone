import json
import logging as stdlib_logging
from unittest.mock import MagicMock, patch
import pytest

# ─── _safe_log ────────────────────────────────────────────────────────────────

def test_safe_log_strips_newlines():
    from apps.common.logging import _safe_log
    result = _safe_log("line1\nline2\r\ninjection")
    assert "\n" not in result
    assert "\r" not in result
    assert "line1" in result
    assert "injection" in result


def test_safe_log_converts_to_string():
    from apps.common.logging import _safe_log
    result = _safe_log(12345)
    assert result == "12345"


# ─── JSONFormatter._mask_sensitive_data ───────────────────────────────────────

def test_mask_sensitive_data_flat_dict():
    from apps.common.logging import JSONFormatter
    formatter = JSONFormatter()
    data = {"password": "secret", "user": "alice"}
    result = formatter._mask_sensitive_data(data)
    assert result["password"] == "********"
    assert result["user"] == "alice"


def test_mask_sensitive_data_nested():
    from apps.common.logging import JSONFormatter
    formatter = JSONFormatter()
    data = {"auth": {"token": "tok123", "name": "bob"}}
    result = formatter._mask_sensitive_data(data)
    assert result["auth"]["token"] == "********"
    assert result["auth"]["name"] == "bob"


def test_mask_sensitive_data_list():
    from apps.common.logging import JSONFormatter
    formatter = JSONFormatter()
    data = [{"signature": "sig_xyz"}, {"safe": "value"}]
    result = formatter._mask_sensitive_data(data)
    assert result[0]["signature"] == "********"
    assert result[1]["safe"] == "value"


def test_mask_sensitive_data_plain_value():
    from apps.common.logging import JSONFormatter
    formatter = JSONFormatter()
    assert formatter._mask_sensitive_data("hello") == "hello"
    assert formatter._mask_sensitive_data(42) == 42


def test_mask_api_key_and_credential():
    from apps.common.logging import JSONFormatter
    formatter = JSONFormatter()
    data = {"api_key": "key123", "credential": "cred456"}
    result = formatter._mask_sensitive_data(data)
    assert result["api_key"] == "********"
    assert result["credential"] == "********"


# ─── JSONFormatter.format ─────────────────────────────────────────────────────

def test_json_formatter_format_output():
    from apps.common.logging import JSONFormatter
    formatter = JSONFormatter()

    record = stdlib_logging.LogRecord(
        name="test",
        level=stdlib_logging.WARNING,
        pathname="/app/views.py",
        lineno=1,
        msg="test message",
        args=(),
        exc_info=None,
    )
    # Patch attributes that format() expects
    record.levelname = "WARNING"
    record.module = "views"
    record.process = 123
    record.threadName = "MainThread"

    with patch("apps.common.resilience.get_trace_id", return_value="trace-123"):
        output = formatter.format(record)

    data = json.loads(output)
    assert data["level"] == "WARNING"
    assert data["message"] == "test message"
    assert data["trace_id"] == "trace-123"
    assert data["is_error"] is False


def test_json_formatter_marks_errors():
    from apps.common.logging import JSONFormatter
    formatter = JSONFormatter()

    record = stdlib_logging.LogRecord(
        name="test",
        level=stdlib_logging.ERROR,
        pathname="/app/errors.py",
        lineno=10,
        msg="error occurred",
        args=(),
        exc_info=None,
    )
    record.levelname = "ERROR"
    record.module = "errors"
    record.process = 123
    record.threadName = "MainThread"

    with patch("apps.common.resilience.get_trace_id", return_value="t-err"):
        output = formatter.format(record)

    data = json.loads(output)
    assert data["is_error"] is True
    assert data["level"] == "ERROR"


# ─── RedisLogHandler ─────────────────────────────────────────────────────────

def test_redis_log_handler_constants():
    from apps.common.logging import RedisLogHandler
    assert RedisLogHandler.REDIS_KEY == "system:observability:logs"
    assert RedisLogHandler.MAX_LOGS == 2000


def test_redis_log_handler_emit_calls_redis():
    from apps.common.logging import RedisLogHandler
    handler = RedisLogHandler()
    
    # We need a proper record for the formatter
    record = stdlib_logging.LogRecord("test", stdlib_logging.INFO, "file.py", 1, "msg", (), None)
    record.levelname = "INFO"
    record.module = "test"
    record.process = 1
    record.threadName = "Main"
    
    json_output = '{"level":"INFO","message":"msg"}'

    mock_r = MagicMock()

    with patch.object(handler, "format", return_value=json_output):
        with patch("redis.Redis.from_url", return_value=mock_r):
            with patch("django.conf.settings") as mock_settings:
                mock_settings.REDIS_URL = "redis://localhost"
                handler.emit(record)

    mock_r.lpush.assert_called_once_with(RedisLogHandler.REDIS_KEY, json_output)
    mock_r.ltrim.assert_called_once_with(RedisLogHandler.REDIS_KEY, 0, RedisLogHandler.MAX_LOGS - 1)


def test_redis_log_handler_emit_handles_error_gracefully():
    from apps.common.logging import RedisLogHandler
    handler = RedisLogHandler()
    record = MagicMock()

    with patch.object(handler, "format", side_effect=Exception("boom")):
        with patch.object(handler, "handleError") as mock_handle:
            handler.emit(record)
            mock_handle.assert_called_once_with(record)
