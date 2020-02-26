import random
import socket
import time
from functools import wraps


__all__ = ['StatsdClient']

class StatsdClient(object):
    """A client for statsd."""

    def __init__(self, host='127.0.0.1', port=8125, prefix=None):
        """Create a new client."""
        self._addr = (host, port)
        self._sock = None
        self._prefix = prefix

    @property
    def sock(self):
        if not self._sock:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return self._sock

    def _after(self, data):
        self._send(data)

    def pipeline(self):
        return Pipeline(self)

    def timer(self, stat, rate=1):
        return Timer(self, stat, rate)

    def timing(self, stat, delta, rate=1):
        """Send new timing information. `delta` is in milliseconds."""
        data = self._prepare(stat, '%d|ms' % delta, rate)
        if data is not None:
            self._after(data)

    def incr(self, stat, count=1, rate=1):
        """Increment a stat by `count`."""
        data = self._prepare(stat, '%s|c' % count, rate)
        if data is not None:
            self._after(data)

    def decr(self, stat, count=1, rate=1):
        """Decrement a stat by `count`."""
        self.incr(stat, -count, rate)

    def gauge(self, stat, value, rate=1, delta=False):
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
            self._after(data)

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

    def _send(self, data):
        """Send data to statsd."""
        try:
            self.sock.sendto(data.encode('ascii'), self._addr)
        except socket.error:
            # No time for love, Dr. Jones!
            pass

