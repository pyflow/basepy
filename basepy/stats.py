import asyncio
import logging
import random
import time
from functools import wraps
from basepy.asynclib import async_datagram

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
        self._stream = await async_datagram.connect(self._addr)

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

        gauge是任意的一维标量值。gague值不会像其它类型会在flush的时候清零，
        而是保持原有值。statsd只会将flush区间内最后一个值发到后端。另外，
        如果数值前加符号，会与前一个值累加。

        例子:
            age:10|g    // age 为 10
            age:+1|g    // age 为 10 + 1 = 11
            age:-1|g    // age为 11 - 1 = 10
            age:5|g     // age为5,替代前一个值

        按照这种定义是无法直接设置负值的(负值前一定有负号，有符号就表示偏移)。
        一种设置负值的实现是: 先设置 0, 再设置负数。在这里我们不打算采用这种
        实现, 因为没法保证原子性。如果使用者真的想设置负值, 可能的一种方式
        如下所示:

            >>> stats_client = StatsClient()
            >>> with stats_client.pipeline() as pipeline:
            >>>     pipeline.gauge('test', 0)
            >>>     pipeline.gauge('test', -10)

        如果要使用这种方式, 请确保你使用的 statsd server 可以对这种情况原子性
        的处理。

        Parameters
        ----------
        delta: bool
            True 表示与前一个值相加, False 则会替换前面的值。默认为 False。
            如果 value 为负, 即使将 delta 设为 False, 在语义上仍然表示与前一个
            值累加。

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
