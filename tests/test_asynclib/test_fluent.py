import pytest
from basepy.more.fluent import AsyncFluentSender

@pytest.mark.asyncio
async def test_fluent_1():
    sender = AsyncFluentSender('debug', 'localhost', '24224')
    await sender.emit("hello", {'key': "value"})
