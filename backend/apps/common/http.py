# apps/common/http.py
import httpx
import logging

logger = logging.getLogger(__name__)

# Global async client for connection pooling
# This should be used across all async consumers and services.
_async_client = None

def get_async_client():
    global _async_client
    if _async_client is None:
        # Production config: 
        # - 5s timeout to prevent hanging the event loop
        # - Higher pool limits for concurrent location pings
        _async_client = httpx.AsyncClient(
            timeout=httpx.Timeout(5.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
            headers={"User-Agent": "UberClone-Backend/1.0"}
        )
    return _async_client

async def close_async_client():
    global _async_client
    if _async_client:
        await _async_client.aclose()
        _async_client = None
