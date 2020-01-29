
# -*- coding: utf-8 -*-

import errno
import socket
import struct
import time
import traceback
import asyncio

import msgpack


class EventTime(msgpack.ExtType):
    def __new__(cls, timestamp):
        seconds = int(timestamp)
        nanoseconds = int(timestamp % 1 * 10 ** 9)
        return super(EventTime, cls).__new__(
            cls,
            code=0,
            data=struct.pack(">II", seconds, nanoseconds),
        )


class AsyncFluentSender(object):
    def __init__(self,
                 tag,
                 host='localhost',
                 port=24224,
                 bufmax=1 * 1024 * 1024,
                 timeout=3.0,
                 verbose=False,
                 buffer_overflow_handler=None,
                 nanosecond_precision=False,
                 msgpack_kwargs=None,
                 **kwargs):
        """
        :param kwargs: This kwargs argument is not used in __init__. This will be removed in the next major version.
        """
        self.tag = tag
        self.host = host
        self.port = port
        self.bufmax = bufmax
        self.timeout = timeout
        self.verbose = verbose
        self.buffer_overflow_handler = buffer_overflow_handler
        self.nanosecond_precision = nanosecond_precision
        self.msgpack_kwargs = {} if msgpack_kwargs is None else msgpack_kwargs

        self._reader = None
        self._writer = None
        self.pendings = None
        self._closed = False
        self._last_error = None

    async def emit(self, label, data):
        if self.nanosecond_precision:
            cur_time = EventTime(time.time())
        else:
            cur_time = int(time.time())
        return await self.emit_with_time(label, cur_time, data)

    async def emit_with_time(self, label, timestamp, data):
        if self.nanosecond_precision and isinstance(timestamp, float):
            timestamp = EventTime(timestamp)
        try:
            bytes_ = self._make_packet(label, timestamp, data)
        except Exception as e:
            print(traceback.format_exc())
            self.last_error = e
            bytes_ = self._make_packet(label, timestamp,
                                       {"level": "CRITICAL",
                                        "message": "Can't output to log",
                                        "traceback": traceback.format_exc()})
        return await self._send(bytes_)

    @property
    def last_error(self):
        return self._last_error

    @last_error.setter
    def last_error(self, err):
        self._last_error = err

    async def close(self):
        if self._closed:
            return
        self._closed = True
        if self.pendings:
            try:
                self._send_data(self.pendings)
            except Exception:
                self._call_buffer_overflow_handler(self.pendings)

        await self._close()
        self.pendings = None

    def _make_packet(self, label, timestamp, data):
        if label:
            tag = '.'.join((self.tag, label))
        else:
            tag = self.tag
        packet = (tag, timestamp, data)
        if self.verbose:
            print(packet)
            print(self.msgpack_kwargs)
        return msgpack.packb(packet, **self.msgpack_kwargs)

    async def _send(self, bytes_):
        if self._closed:
            return False
        return await self._send_internal(bytes_)

    async def _send_internal(self, bytes_):
        # buffering
        if self.pendings:
            self.pendings += bytes_
            bytes_ = self.pendings

        try:
            await self._reconnect()
            # send message
            self._writer.write(bytes_)
            await self._writer.drain()

            # send finished
            self.pendings = None

            return True
        except socket.error as e:
            self.last_error = e

            # close socket
            await self._close()

            # clear buffer if it exceeds max buffer size
            if self.pendings and (len(self.pendings) > self.bufmax):
                self._call_buffer_overflow_handler(self.pendings)
                self.pendings = None
            else:
                self.pendings = bytes_

            return False


    async def _reconnect(self):
        if not self._reader:
            try:
                if self.host.startswith('unix://'):
                    fut = asyncio.open_unix_connection(self.host[len('unix://'):])
                else:
                    fut = asyncio.open_connection(self.host, self.port)
                
                reader, writer = await asyncio.wait_for(fut, timeout = self.timeout)
                self._reader, self._writer = reader, writer
            except Exception as e:
                self._reader = None
                self._writer = None
                raise e

    def _call_buffer_overflow_handler(self, pending_events):
        try:
            if self.buffer_overflow_handler:
                self.buffer_overflow_handler(pending_events)
        except Exception as e:
            # User should care any exception in handler
            pass

    async def _close(self):
        try:
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
        finally:
            self._reader = None
            self._writer = None

    async def __enter__(self):
        return self

    async def __exit__(self, typ, value, traceback):
        try:
            await self.close()
        except Exception as e:  # pragma: no cover
            self.last_error = e