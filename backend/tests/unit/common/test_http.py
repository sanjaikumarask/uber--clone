import pytest
import httpx
from unittest.mock import patch, AsyncMock
from apps.common.http import get_async_client, close_async_client
import apps.common.http as http_module

@pytest.mark.asyncio
class TestHttp:
    async def test_get_async_client_creates_client(self):
        # Reset global state for test isolation
        http_module._async_client = None
        
        client1 = get_async_client()
        assert isinstance(client1, httpx.AsyncClient)
        
        client2 = get_async_client()
        assert client1 is client2  # Should be the same instance
        
        await close_async_client()
        assert http_module._async_client is None

    async def test_close_async_client_when_none(self):
        http_module._async_client = None
        # Should not raise any error
        await close_async_client()
        assert http_module._async_client is None
        
    @patch('httpx.AsyncClient.aclose', new_callable=AsyncMock)
    async def test_close_async_client_closes(self, mock_aclose):
        client = get_async_client()
        await close_async_client()
        mock_aclose.assert_called_once()
        assert http_module._async_client is None
