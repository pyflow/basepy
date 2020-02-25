
import time
import sys
import asyncio
from asyncio import Queue
import traceback
import os
import platform
import json
from basepy.asynclib.fluent import AsyncFluentSender
from basepy.asynclib import datagram
from basepy.common.log import LoggerLevel, LogRecord, BaseHandler

class StdoutHandler(BaseHandler):
    terminator = '\n'
    def __init__(self, stream=None, format=None, level="DEBUG", **kwargs):
        if stream is None:
            stream = sys.stdout
        self.stream = stream
        self.format_str = "[{created}] [{hostname}.{process}] [{level}] [{message}]"
        self.level = level
        self.levelno = LoggerLevel.get_levelno(self.level, 0)


    def flush(self):
        if self.stream and hasattr(self.stream, "flush"):
            self.stream.flush()

    async def emit(self, record):
        try:
            msg = self.make_message(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handle_error(record)

    def make_message(self, record):
        data = record.to_dict()
        data['created'] = time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(data['created']))
        extra_data = data.pop('data')
        msg = self.format_str.format(**data)
        extra = ' '.join(map(lambda x: "[{} = {}]".format(x[0], json.dumps(x[1])), extra_data.items()))
        if extra:
            msg = ' '.join([msg, extra])
        return msg

    def __repr__(self):
        level = ""
        name = getattr(self.stream, 'name', '')
        name = str(name)
        if name:
            name += ' '
        return '<%s %s(%s)>' % (self.__class__.__name__, name, level)

class SocketHandler(BaseHandler):
    terminator = '\n'
    def __init__(self, host="127.0.0.1", port=514, connection_type="TCP", level="DEBUG", **kwargs):
        self.host = host
        self.port = port
        self.level = level
        if connection_type.upper() not in ("TCP", "UDP"):
            raise ValueError("connection_type must be one of ['TCP', 'UDP'].")
        self.connection_type = connection_type.upper()
        self.levelno = LoggerLevel.get_levelno(self.level, 0)
        self.tcp_writer = None
        self.udp_stream = None

    def flush(self):
        pass

    async def _write_tcp(self, data):
        if self.tcp_writer is None:
            _, writer = await asyncio.open_connection(self.host, self.port)
            self.tcp_writer = writer
        self.tcp_writer.write(data)
        await self.tcp_writer.drain()

    async def _write_udp(self, data):
        if self.udp_stream is None:
            writer = datagram.connect((self.host, self.port))
            self.udp_stream = writer
        await self.udp_stream.send(data)

    async def _write(self, data):
        if self.connection_type.upper() == "TCP":
            await self._write_tcp(data)
        elif self.connection_type.upper() == "UDP":
            await self._write_udp(data)

    async def emit(self, record):
        try:
            msg = "{}{}".format(json.dumps(record.to_dict()), self.terminator)
            await self._write(msg.encode("utf-8"))
        except Exception:
            self.handle_error(record)


    def __repr__(self):
        return '<%s [%s:%s(%s)]>' % (self.__class__.__name__, self.host, self.port, self.level)

class FluentHandler(BaseHandler):
    terminator = '\n'
    def __init__(self, tag, host="127.0.0.1", port=24224, level="DEBUG", **kwargs):
        self.tag = tag
        self.host = host
        self.port = port
        self.fluentsender = AsyncFluentSender(tag, host=host, port=port)
        self.level = level
        self.levelno = LoggerLevel.get_levelno(self.level, 0)

    def flush(self):
        pass

    async def emit(self, record):
        try:
            await self.fluentsender.emit(record.name, record.to_dict())
        except Exception:
            self.handle_error(record)


    def __repr__(self):
        return '<%s %s(%s)>' % (self.__class__.__name__, self.tag, self.level)

class AsyncLogger(object):
    handler_class_map = {
        'stdout': StdoutHandler,
        'socket': SocketHandler,
        'fluent': FluentHandler
    }
    def __init__(self, name="", **kwargs):
        self.name = name
        self.handlers = []
        self.queue = None
        self.queued_handlers = []
        self.dev_mode = True
        self.hostname = platform.node()

    async def init(self, config):
        await self.init_queue()
        handlers = config['handlers']
        for handler in handlers:
            conf = config.get(handler, {}).to_dict()
            handler_type = conf.pop('handler_type', '')
            if handler_type not in self.handler_class_map:
                continue
            self.add(handler_type, **conf)

    async def init_queue(self):
        self.queue = Queue()

    def add(self, handler, level="DEBUG", log_format=None, queue=False, **kwargs):
        h_cls = self.handler_class_map.get(handler)
        if not h_cls:
            raise Exception('no handler class for {}'.format(handler))
        h = h_cls(format=log_format, queue=queue, level=level, **kwargs)
        if queue:
            self.queued_handlers.append(h)
        else:
            self.handlers.append(h)

    def clear(self):
        self.handlers = []
        self.queued_handlers = []

    def _filter_handlers(self, level):
        levelno = LoggerLevel.get_levelno(level)
        handlers = list(filter(lambda x: levelno >= x.levelno, self.handlers))
        queued_handlers = list(filter(lambda x: levelno >= x.levelno, self.queued_handlers))
        return handlers, queued_handlers

    async def log(self, level, message, args, kwargs):
        handlers, queued_handlers = self._filter_handlers(level)
        if len(handlers) + len(queued_handlers) == 0:
            return None

        record = LogRecord(self.name, level, message, args, None, **kwargs)
        if len(self.handlers) > 0:
            for handler in self.handlers:
                await handler.emit(record)

        if len(self.queued_handlers) > 0:
            await self.queue.put(record)


    async def debug(self, message, *args, **kwargs):
        if self.dev_mode:
            await self.log('DEBUG', message, args, kwargs)

    async def info(self, message, *args, **kwargs):
        await self.log('INFO', message, args, kwargs)

    async def warning(self, message, *args, **kwargs):
        await self.log('WARNING', message, args, kwargs)

    async def error(self, message, *args, **kwargs):
        await self.log('ERROR', message, args, kwargs)

    async def critical(self, message, *args, **kwargs):
        await self.log('CRITICAL', message, args, kwargs)

    async def exception(self, message, *args, exc_info=True, **kwargs):
        await self.error(message, *args, exc_info=exc_info, **kwargs)

logger = AsyncLogger("root")