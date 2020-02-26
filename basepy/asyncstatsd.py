import asyncio
import random
import time
from functools import wraps
from basepy.asynclib import datagram

__all__ = ['StatsdClient']

class StatsdClient(object):
    """A client for statsd."""

    def __init__(self, host='127.0.0.1', port=8125, prefix=None, loop=None):
        """Create a new client."""
        self._addr = (host, port)
        self._prefix = prefix
        self._loop = loop or asyncio.get_event_loop()
        self._stream = None

    async def init(self):
        self._stream = await datagram.connect(self._addr)

    async def timing(self, stat, delta, rate=1):
        """Send new timing information. `delta` is in milliseconds."""
        data = self._prepare(stat, '%d|ms' % delta, rate)
        if data is not None:
            await self._send(data)

    async def incr(self, stat, count=1, rate=1):
        """Increment a stat by `count`."""
        data = self._prepare(stat, '%s|c' % count, rate)
        if data is not None:
            await self._send(data)

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
            await self._send(data)

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
