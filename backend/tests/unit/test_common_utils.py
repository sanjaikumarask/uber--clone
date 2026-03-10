import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from apps.common.backpressure import RetryStrategy
from apps.common.chaos import ChaosMonkey
from apps.common.idempotency import (
    IdempotencyMiddleware,
    _safe_log,
    idempotent_task,
    idempotent_webhook,
)
from apps.common.logging import JSONFormatter
from apps.rides.services.otp import _generate_otp

# ─── _safe_log TESTS ──────────────────────────────────────────────────────────


def test_safe_log_strips_newline_to_space():
    """\n is replaced with a space (not removed entirely)."""
    result = _safe_log("bad\nvalue")
    assert "\n" not in result
    assert result == "bad value"  # newline -> space


def test_safe_log_strips_carriage_return_entirely():
    """\r is removed entirely (replaced with empty string)."""
    result = _safe_log("bad\rvalue")
    assert "\r" not in result
    assert result == "badvalue"  # CR -> empty string


def test_safe_log_mixed():
    """Mixed CR+LF: \r removed, \n replaced with space."""
    result = _safe_log("malicious\nline\rinjected")
    assert "\n" not in result
    assert "\r" not in result
    # \r stripped: "malicious\nlineinjected" -> \n->space -> "malicious lineinjected"
    assert result == "malicious lineinjected"


def test_safe_log_clean_string_unchanged():
    """A clean string should pass through unchanged."""
    assert _safe_log("hello world") == "hello world"


def test_safe_log_converts_non_string():
    """Non-string input should be converted to string safely."""
    assert _safe_log(42) == "42"
    assert _safe_log(None) == "None"


# ─── JSONFormatter TESTS ──────────────────────────────────────────────────────


def _make_log_record(msg: str, level: int = logging.INFO, module: str = "test_mod"):
    """Helper: builds a real logging.LogRecord (JSON-serializable)."""
    record = logging.LogRecord(
        name="test.logger",
        level=level,
        pathname="/app/test.py",
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    record.module = module
    return record


def test_json_formatter_sanitizes_newline_in_message():
    """Log injection via message should be stripped."""
    formatter = JSONFormatter()
    record = _make_log_record("Dangerous\nLine")
    with patch("apps.common.resilience.get_trace_id", return_value="trace-abc"):
        result = json.loads(formatter.format(record))
    assert "\n" not in result["message"]
    assert "Dangerous" in result["message"]


def test_json_formatter_contains_required_fields():
    """JSON log must have timestamp, level, module, message."""
    formatter = JSONFormatter()
    record = _make_log_record("hello")
    with patch("apps.common.resilience.get_trace_id", return_value="t-1"):
        result = json.loads(formatter.format(record))
    for field in ("timestamp", "level", "module", "message", "trace_id"):
        assert field in result, f"Missing field: {field}"


def test_json_formatter_is_error_flag():
    """is_error must be True only for ERROR and above."""
    formatter = JSONFormatter()
    with patch("apps.common.resilience.get_trace_id", return_value="t-1"):
        # INFO record — is_error = False
        info_record = _make_log_record("info msg", level=logging.INFO)
        result = json.loads(formatter.format(info_record))
        assert result["is_error"] is False

        # ERROR record — is_error = True
        err_record = _make_log_record("err msg", level=logging.ERROR)
        result = json.loads(formatter.format(err_record))
        assert result["is_error"] is True


# ─── IdempotencyMiddleware TESTS ──────────────────────────────────────────────


@patch("apps.common.idempotency.cache")
def test_idempotency_middleware_passes_through_get(mock_cache):
    """GET requests must bypass idempotency middleware completely."""
    get_response = MagicMock(return_value=MagicMock(status_code=200))
    mw = IdempotencyMiddleware(get_response)
    request = MagicMock()
    request.method = "GET"
    mw(request)
    get_response.assert_called_once_with(request)
    mock_cache.add.assert_not_called()


@patch("apps.common.idempotency.cache")
def test_idempotency_middleware_passes_through_no_key(mock_cache):
    """POST without idempotency key must pass through."""
    get_response = MagicMock(return_value=MagicMock(status_code=200))
    mw = IdempotencyMiddleware(get_response)
    request = MagicMock()
    request.method = "POST"
    request.headers = {}
    mw(request)
    get_response.assert_called_once_with(request)


@patch("apps.common.idempotency.cache")
def test_idempotency_middleware_replays_cached_response(mock_cache):
    """If a valid cached response exists, it must be replayed without calling view."""
    mock_cache.add.return_value = False
    mock_cache.get.return_value = {"status": 200, "data": {"ok": True}}
    get_response = MagicMock()
    mw = IdempotencyMiddleware(get_response)
    request = MagicMock()
    request.method = "POST"
    request.headers = {"X-Idempotency-Key": "token-abc"}
    request.user.is_authenticated = False
    response = mw(request)
    assert response.status_code == 200
    assert json.loads(response.content) == {"ok": True}
    get_response.assert_not_called()


@patch("apps.common.idempotency.cache")
def test_idempotency_middleware_returns_409_for_in_flight(mock_cache):
    """If the request is already in-flight, return 409."""
    mock_cache.add.return_value = False
    mock_cache.get.return_value = "IN_FLIGHT"
    get_response = MagicMock()
    mw = IdempotencyMiddleware(get_response)
    request = MagicMock()
    request.method = "POST"
    request.headers = {"X-Idempotency-Key": "token-xyz"}
    request.user.is_authenticated = False
    response = mw(request)
    assert response.status_code == 409


# ─── idempotent_task TESTS ────────────────────────────────────────────────────


@patch("apps.common.idempotency.cache")
def test_idempotent_task_first_call_executes(mock_cache):
    """First call with lock acquired and no done marker must execute."""
    mock_cache.add.return_value = True
    mock_cache.get.return_value = None
    work = MagicMock(return_value="done")
    decorated = idempotent_task(ttl=60)(work)
    result = decorated("arg1", key="val")
    assert result == "done"
    work.assert_called_once_with("arg1", key="val")


@patch("apps.common.idempotency.cache")
def test_idempotent_task_blocks_replay(mock_cache):
    """Second call with done marker must return None and skip execution."""
    mock_cache.add.return_value = True
    mock_cache.get.return_value = "1"  # Already done
    work = MagicMock(return_value="done")
    decorated = idempotent_task(ttl=60)(work)
    result = decorated("arg1")
    assert result is None
    work.assert_not_called()


@patch("apps.common.idempotency.cache")
def test_idempotent_task_blocks_concurrent(mock_cache):
    """If lock cannot be acquired (concurrent), must return None immediately."""
    mock_cache.add.return_value = False  # Lock already held
    work = MagicMock()
    decorated = idempotent_task(ttl=60)(work)
    result = decorated("arg1")
    assert result is None
    work.assert_not_called()


# ─── idempotent_webhook TESTS ─────────────────────────────────────────────────


@patch("apps.common.idempotency.cache")
def test_idempotent_webhook_drops_duplicate(mock_cache):
    """Already-processed event ID must be dropped with 200."""
    mock_cache.get.return_value = "1"
    view = MagicMock()
    decorated = idempotent_webhook("razorpay")(view)
    request = MagicMock()
    request.headers = {"X-Razorpay-Event-Id": "evt_dup"}
    response = decorated(request)
    assert response.status_code == 200
    assert json.loads(response.content) == {"status": "already_processed"}
    view.assert_not_called()


@patch("apps.common.idempotency.cache")
def test_idempotent_webhook_processes_new_event(mock_cache):
    """New event ID must be processed, and marked done."""
    mock_cache.get.return_value = None
    mock_cache.add.return_value = True
    inner_response = MagicMock()
    inner_response.status_code = 200
    view = MagicMock(return_value=inner_response)
    decorated = idempotent_webhook("razorpay")(view)
    request = MagicMock()
    request.headers = {"X-Razorpay-Event-Id": "evt_new"}
    response = decorated(request)
    assert response.status_code == 200
    view.assert_called_once()
    mock_cache.set.assert_called_once()


@patch("apps.common.idempotency.cache")
def test_idempotent_webhook_no_event_id_passes_through(mock_cache):
    """Webhook with no event ID header must pass through without caching."""
    inner_response = MagicMock()
    inner_response.status_code = 200
    view = MagicMock(return_value=inner_response)
    decorated = idempotent_webhook("razorpay")(view)
    request = MagicMock()
    request.headers = {}
    decorated(request)
    view.assert_called_once()
    mock_cache.get.assert_not_called()


# ─── RetryStrategy / BackpressureTESTS ───────────────────────────────────────


def test_retry_strategy_normal_jitter_within_range():
    delay = RetryStrategy.get_countdown("NORMAL", 1)
    assert isinstance(delay, float)
    assert 0 <= delay <= 30  # cap for NORMAL at attempt 1: min(600, 15 * 2^1) = 30


def test_retry_strategy_critical_priority():
    delay = RetryStrategy.get_countdown("CRITICAL", 0)
    assert isinstance(delay, float)
    assert 0 <= delay <= 2  # base 2s, attempt 0


def test_retry_strategy_max_retries_returns_minus_one():
    assert RetryStrategy.get_countdown("NORMAL", 10) == -1
    assert RetryStrategy.get_countdown("HIGH", 10) == -1


def test_retry_strategy_get_max_retries():
    assert RetryStrategy.get_max_retries("NORMAL") == 4
    assert RetryStrategy.get_max_retries("CRITICAL") == 10


# ─── OTP TESTS ────────────────────────────────────────────────────────────────


def test_otp_is_4_digit_string():
    otp = _generate_otp()
    assert isinstance(otp, str)
    assert len(otp) == 4
    assert otp.isdigit()


def test_otp_is_within_range():
    for _ in range(20):
        otp = int(_generate_otp())
        assert 0 <= otp <= 9999, f"OTP out of range: {otp}"


def test_otp_uses_secure_rng():
    """Multiple OTPs should not all be identical (randomness check)."""
    otps = {_generate_otp() for _ in range(10)}
    assert len(otps) > 1, "OTP generator appears deterministic"


# ─── ChaosMonkey TESTS ────────────────────────────────────────────────────────


@patch("apps.common.chaos.connection")
def test_chaos_db_slowdown_fires_at_probability_1(mock_conn):
    """At probability=1.0, pg_sleep must always be called."""
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    ChaosMonkey.simulate_db_slowdown(delay=0.01, probability=1.0)
    mock_cursor.execute.assert_called_once_with("SELECT pg_sleep(%s)", [0.01])


@patch("apps.common.chaos._cryptogen")
@patch("apps.common.chaos.connection")
def test_chaos_db_slowdown_skips_at_probability_0(mock_conn, mock_rng):
    """At probability=0.0, pg_sleep must never be called."""
    mock_rng.random.return_value = 0.5  # 0.5 > 0.0 so condition is False
    ChaosMonkey.simulate_db_slowdown(delay=1.0, probability=0.0)
    mock_conn.cursor.assert_not_called()


def test_chaos_redis_outage_raises():
    """At probability=1.0, a Redis ConnectionError must be raised."""
    with pytest.raises(Exception):
        ChaosMonkey.simulate_redis_outage(probability=1.0)
