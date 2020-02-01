import pytest
from basepy.asynclib.async_fluent import AsyncFluentSender

@pytest.mark.asyncio
async def test_async_fluent_1():
    sender = AsyncFluentSender('debug', 'localhost', '24224')
    await sender.emit("hello", {'key': "value"})
