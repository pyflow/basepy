import asyncio
import random
import time

from basepy.asynclib import datagram

__all__ = ['StatsdClient']


class StatsdClient(object):
    """A client for statsd."""

    def __init__(self, host='127.0.0.1', port=8125, prefix=None, loop=None):
        """Create a new client."""
        self._prefix = prefix
        self._loop = loop or asyncio.get_event_loop()
        self._stream = datagram.DatagramAutoClient(host, port)

    async def init(self):
        await self._stream.init()

    def pipeline(self):
        return Pipeline(self)

    def timer(self, stat, rate=1):
        return Timer(self, stat, rate)

    async def timing(self, stat, delta, rate=1):
        """Send new timing information. `delta` is in milliseconds."""
        data = self._prepare(stat, '%d|ms' % delta, rate)
        if data is not None:
            await self._after(data)

    async def incr(self, stat, count=1, rate=1):
        """Increment a stat by `count`."""
        data = self._prepare(stat, '%s|c' % count, rate)
        if data is not None:
            await self._after(data)

    async def decr(self, stat, count=1, rate=1):
        """Decrement a stat by `count`."""
        await self.incr(stat, -count, rate)

    async def gauge(self, stat, value, rate=1, delta=False):
        """Set a gauge value.
            age:10|g    // age is 10
            age:+1|g    // age is 10 + 1 = 11
            age:-1|g    // age is 11 - 1 = 10
            age:5|g     // age is 5

        """
        if delta:
            value = '%+g|g' % value
        else:
            value = '%g|g' % value
        data = self._prepare(stat, value, rate)
        if data is not None:
            await self._after(data)

    def _prepare(self, stat, value, rate=1):
        if rate < 1:
            if random.random() < rate:
                value = '%s|@%s' % (value, rate)
            else:
                return

        if self._prefix:
            stat = '%s.%s' % (self._prefix, stat)

        data = '%s:%s' % (stat, value)
        return data

    async def _send(self, data):
        """Send data to statsd."""
        await self._stream.send(data.encode('ascii'))

    async def _after(self, data):
        await self._send(data)


class Timer(object):
    """A context manager/decorator for statsd.timing()."""

    def __init__(self, client, stat, rate=1):
        self.client = client
        self.stat = stat
        self.rate = rate
        self.ms = None

    async def __aenter__(self):
        self.start = time.time()
        return self

    async def __aexit__(self, typ, value, tb):
        dt = time.time() - self.start
        self.ms = int(round(1000 * dt))  # Convert to ms.
        await self.client.timing(self.stat, self.ms, self.rate)


class Pipeline(StatsdClient):
    def __init__(self, client):
        self._client = client
        self._prefix = client._prefix
        self._stats = []

    async def _after(self, data):
        self._stats.append(data)

    async def __aenter__(self):
        return self

    async def __aexit__(self, typ, value, tb):
        await self.send()

    async def send(self):
        # Use pop(0) to preserve the order of the stats.
        data = self._stats.pop(0)
        while self._stats:
            stat = self._stats.pop(0)
            if len(stat) + len(data) + 1 >= 512:
                await self._client._send(data)
                data = stat
            else:
                data += '\n' + stat
        if data:
            await self._client._send(data)
