# apps/common/resilience.py
import time
import logging
import functools
import threading
from typing import Callable, Any
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ─── 1. CIRCUIT BREAKER ──────────────────────────────────────────────────────

class CircuitBreakerError(Exception):
    """Raised when the circuit is OPEN."""
    pass

class CircuitBreaker:
    """
    Stateful Circuit Breaker for External APIs (Razorpay, Google Maps).
    
    States:
        CLOSED: Normal operation. Requests pass through.
        OPEN:   API failing. Requests blocked immediately for `reset_timeout`.
        HALF_OPEN: Testing if API recovered. 1 trial request allowed.
    """
    
    def __init__(self, name: str, threshold: int = 5, reset_timeout: int = 60):
        self.name = name
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.state_key = f"circuit:{name}:state"
        self.fail_key = f"circuit:{name}:failures"

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            state = cache.get(self.state_key, "CLOSED")
            
            if state == "OPEN":
                # Check if timeout expired to transition to HALF_OPEN
                if not cache.get(f"{self.state_key}:timer"):
                    state = "HALF_OPEN"
                    cache.set(self.state_key, "HALF_OPEN")
                else:
                    logger.warning(f"[Resilience] Circuit {self.name} is OPEN. Rejecting request.")
                    raise CircuitBreakerError(f"Circuit {self.name} is OPEN")

            try:
                result = func(*args, **kwargs)
                
                # Success: Close circuit if it was HALF_OPEN or reset failure count if CLOSED
                if state == "HALF_OPEN":
                    logger.info(f"[Resilience] Circuit {self.name} recovered. Closing.")
                    self._close()
                else:
                    cache.delete(self.fail_key)
                
                return result

            except Exception as e:
                # Failure: Increment count and potentially open circuit
                if state == "HALF_OPEN":
                    logger.error(f"[Resilience] Circuit {self.name} failed trial. Re-opening.")
                    self._open()
                else:
                    failures = cache.incr(self.fail_key, 1) if cache.get(self.fail_key) else cache.set(self.fail_key, 1) or 1
                    if failures >= self.threshold:
                        logger.critical(f"[Resilience] Circuit {self.name} threshold reached ({failures}). Opening.")
                        self._open()
                
                raise e

        return wrapper

    def _open(self):
        cache.set(self.state_key, "OPEN", timeout=self.reset_timeout * 2)
        cache.set(f"{self.state_key}:timer", "1", timeout=self.reset_timeout)

    def _close(self):
        cache.set(self.state_key, "CLOSED")
        cache.delete(self.fail_key)
        cache.delete(f"{self.state_key}:timer")


# ─── 2. DISTRIBUTED TRACING (Correlation ID) ─────────────────────────────────

import uuid

_thread_locals = threading.local()

def get_trace_id() -> str:
    """Returns current trace_id from thread locals or generates a new one."""
    if not hasattr(_thread_locals, "trace_id"):
        _thread_locals.trace_id = str(uuid.uuid4())
    return _thread_locals.trace_id

def set_trace_id(trace_id: str):
    _thread_locals.trace_id = trace_id

class TracingMiddleware:
    """
    Middleware to inject/extract X-Trace-ID from HTTP headers.
    Ensures observability across API -> Celery -> DB.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        set_trace_id(trace_id)
        
        response = self.get_response(request)
        response["X-Trace-ID"] = trace_id
        return response

from celery.signals import before_task_publish, task_prerun

@before_task_publish.connect
def on_task_publish(sender=None, headers=None, body=None, **kwargs):
    """Injects current Trace ID into outgoing Celery task headers."""
    if headers:
        headers["x_trace_id"] = get_trace_id()

@task_prerun.connect
def on_task_prerun(sender=None, task_id=None, task=None, *args, **kwargs):
    """Extracts Trace ID from Celery task headers and sets it in local thread."""
    if task and hasattr(task.request, "x_trace_id"):
        set_trace_id(task.request.x_trace_id)
    elif task and task.request.headers and "x_trace_id" in task.request.headers:
        set_trace_id(task.request.headers["x_trace_id"])
    else:
        # Fallback to task_id if no trace_id exists
        set_trace_id(f"task:{task_id}")
