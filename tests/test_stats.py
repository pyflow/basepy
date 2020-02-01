import pytest
from basepy.stats import StatsdClient

@pytest.mark.asyncio
async def test_stats_1():
    client = StatsdClient(host='8.8.8.8')
    await client.init()
    await client.incr("test.hello")
    await client.decr("test.hello")
    await client.timing('test.api.ok', 100)
