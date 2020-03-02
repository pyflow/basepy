import asyncio

import pytest

from basepy.asyncstatsd import StatsdClient


class MockStatsdClient(StatsdClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statsd_data = []

    async def _send(self, data):
        self.statsd_data.append(data)


@pytest.fixture
def statsd_client():
    host = '127.0.0.1'
    port = 8125
    prefix = 'test'

    yield MockStatsdClient(host, port, prefix)


@pytest.mark.asyncio
async def test_incr(statsd_client):
    await statsd_client.incr('request.number')
    assert statsd_client.statsd_data[0] == 'test.request.number:1|c'


@pytest.mark.asyncio
async def test_decr(statsd_client):
    await statsd_client.decr('request.number')
    assert statsd_client.statsd_data[0] == 'test.request.number:-1|c'


@pytest.mark.asyncio
async def test_timing(statsd_client):
    await statsd_client.timing('request.cost', 100)
    assert statsd_client.statsd_data[0] == 'test.request.cost:100|ms'


@pytest.mark.asyncio
async def test_gauge(statsd_client):
    await statsd_client.gauge('system.memory', 1000)
    assert statsd_client.statsd_data[0] == 'test.system.memory:1000|g'


@pytest.mark.asyncio
async def test_pipeline(statsd_client):
    async with statsd_client.pipeline() as pipeline:
        await pipeline.incr('request.number')
        await pipeline.decr('request.number')
        await pipeline.timing('request.cost', 100)
        await pipeline.gauge('system.memeory', 1000)
    res = (
        'test.request.number:1|c\n'
        'test.request.number:-1|c\n'
        'test.request.cost:100|ms\n'
        'test.system.memeory:1000|g'
    )
    assert statsd_client.statsd_data[0] == res


@pytest.mark.asyncio
async def test_timer(statsd_client):
    async with statsd_client.timer('request.cost'):
        await asyncio.sleep(0.1)
    assert statsd_client.statsd_data[0].endswith('|ms')
