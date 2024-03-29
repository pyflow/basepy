
import time
import sys
import asyncio
import traceback
import os
import platform
import json
import pprint
from copy import copy
from basepy.asynclib import datagram
from basepy.common.log import LoggerLevel, LogRecord, BaseHandler

class StdoutHandler(BaseHandler):
    terminator = '\n'
    def __init__(self, stream=None, format=None, level="DEBUG", **kwargs):
        if stream is None:
            stream = sys.stdout
        self.stream = stream
        self.isatty = stream.isatty()
        self.format_str = "[{created}] [{hostname}.{process}] [{level}] [{name}] [{message}]"
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

    def emit_sync(self, record):
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
        extra_data = data.pop('data', None)
        msg = self.format_str.format(**data)
        if len(extra_data) > 0:
            if self.isatty:
                extra = '{}{}{}'.format(self.terminator, pprint.pformat(extra_data), self.terminator)
            else:
                extra = ' '.join(map(lambda x: "[{} = {}]".format(x[0], json.dumps(x[1])), extra_data.items()))
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
        self.tcp_socket = None
        self.udp_socket = None

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

    def _write_tcp_sync(self, data):
        if self.tcp_socket is None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                self.tcp_socket = s
        self.tcp_socket.sendall(data)

    def _write_udp_sync(self, data):
        if self.udp_socket is None:
            self.udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.udp_socket.sendto(data)

    def _write_sync(self, data):
        if self.connection_type.upper() == "TCP":
            self._write_tcp_sync(data)
        elif self.connection_type.upper() == "UDP":
            self._write_udp_sync(data)

    def emit_sync(self, record):
        try:
            msg = "{}{}".format(json.dumps(record.to_dict()), self.terminator)
            self._write_sync(msg.encode("utf-8"))
        except Exception:
            self.handle_error(record)


    def __repr__(self):
        return '<%s [%s:%s(%s)]>' % (self.__class__.__name__, self.host, self.port, self.level)


class AsyncLoggerEngine:
    handler_class_map = {
        'stdout': StdoutHandler,
        'socket': SocketHandler
    }
    def __init__(self, **kwargs):
        self.handlers = []
        self.dev_mode = True
        self.min_levelno = LoggerLevel.CRITICAL
        self.hostname = platform.node()

    @classmethod
    def register_handler(cls, name, handler_cls):
        if name not in cls.handler_class_map:
            cls.handler_class_map[name] = handler_cls


    async def init(self, config=None):
        if config:
            handlers = config['handlers']
            for handler in handlers:
                conf = config.get(handler, {}).to_dict()
                handler_type = conf.pop('handler_type', '')
                if handler_type not in self.handler_class_map:
                    continue
                self.add(handler_type, **conf)

    def add(self, handler, level="INFO", log_format=None, **kwargs):
        h_cls = self.handler_class_map.get(handler)
        if not h_cls:
            raise Exception('no handler class for {}'.format(handler))
        levelno = LoggerLevel.get_levelno(level)
        if levelno < self.min_levelno:
            self.min_levelno = levelno
        h = h_cls(format=log_format, level=level, **kwargs)
        self.handlers.append(h)

    def clear(self):
        self.handlers = []

    def _filter_handlers(self, level):
        levelno = LoggerLevel.get_levelno(level)
        handlers = list(filter(lambda x: levelno >= x.levelno, self.handlers))
        return handlers

    def log_sync(self, name, level, message, args, kwargs):
        handlers = self._filter_handlers(level)
        if len(handlers) == 0:
            return None
        exc_info = kwargs.pop('exc_info', None)
        record = LogRecord(name, level, message, args, exc_info, None, **kwargs)
        if len(self.handlers) > 0:
            for handler in self.handlers:
                handler.emit_sync(record)

    async def log(self, name, level, message, args, kwargs):
        handlers = self._filter_handlers(level)
        if len(handlers) == 0:
            return None
        exc_info = kwargs.pop('exc_info', None)
        record = LogRecord(name, level, message, args, exc_info, None, **kwargs)
        if len(self.handlers) > 0:
            for handler in self.handlers:
                await handler.emit(record)

class SyncLogger:
    def __init__(self, name="", engine=None, **kwargs):
        self.name = name
        self.engine = engine or AsyncLoggerEngine()
        self.kwargs = kwargs

    def add(self, handler, level="DEBUG", log_format=None, **kwargs):
        return self.engine.add(handler, level=level, log_format=log_format, **kwargs)


    def clear(self):
        return self.engine.clear()

    def sync(self):
        return self

    def bind(self, **kwargs):
        name = kwargs.pop('name', '') or self.name
        new_kwargs = copy(self.kwargs)
        new_kwargs.update(kwargs)
        return SyncLogger(name, self.engine, **new_kwargs)

    def log(self, level, message, args, kwargs):
        merged_args = copy(self.kwargs)
        merged_args.update(kwargs)
        self.engine.log_sync(self.name, level, message, args, merged_args)

    def debug(self, message, *args, **kwargs):
        if self.engine.dev_mode:
            self.log('DEBUG', message, args, kwargs)

    def info(self, message, *args, **kwargs):
        if self.engine.min_levelno > LoggerLevel.INFO: return
        self.log('INFO', message, args, kwargs)

    def warning(self, message, *args, **kwargs):
        if self.engine.min_levelno > LoggerLevel.WARNING: return
        self.log('WARNING', message, args, kwargs)

    def error(self, message, *args, **kwargs):
        if self.engine.min_levelno > LoggerLevel.ERROR: return
        exc_info = kwargs.pop('exc_info', None)
        if exc_info:
            kwargs['exc_info'] = sys.exc_info()
        self.log('ERROR', message, args, kwargs)

    def critical(self, message, *args, **kwargs):
        if self.engine.min_levelno > LoggerLevel.CRITICAL: return
        exc_info = kwargs.pop('exc_info', None)
        if exc_info:
            kwargs['exc_info'] = sys.exc_info()
        self.log('CRITICAL', message, args, kwargs)

    def exception(self, message, *args, **kwargs):
        kwargs.pop('exc_info', None)
        self.error(message, *args, exc_info=True, **kwargs)

class AsyncLogger(object):
    def __init__(self, name="", engine=None, **kwargs):
        self.name = name
        self.engine = engine or AsyncLoggerEngine()
        self.kwargs = kwargs
        self.inited = False

    async def init(self, config=None):
        if not self.inited:
            await self.engine.init(config)
            self.inited = True

    def add(self, handler, level="DEBUG", log_format=None, **kwargs):
        return self.engine.add(handler, level=level, log_format=log_format, **kwargs)

    def clear(self):
        return self.engine.clear()

    def sync(self):
        return SyncLogger(self.name, self.engine, **self.kwargs)

    def bind(self, **kwargs):
        name = kwargs.pop('name', '') or self.name
        new_kwargs = copy(self.kwargs)
        new_kwargs.update(kwargs)
        return AsyncLogger(name, self.engine, **new_kwargs)

    async def log(self, level, message, args, kwargs):
        merged_args = copy(self.kwargs)
        merged_args.update(kwargs)
        await self.engine.log(self.name, level, message, args, merged_args)

    async def debug(self, message, *args, **kwargs):
        if self.engine.dev_mode:
            await self.log('DEBUG', message, args, kwargs)

    async def info(self, message, *args, **kwargs):
        if self.engine.min_levelno > LoggerLevel.INFO: return
        await self.log('INFO', message, args, kwargs)

    async def warning(self, message, *args, **kwargs):
        if self.engine.min_levelno > LoggerLevel.WARNING: return
        await self.log('WARNING', message, args, kwargs)

    async def error(self, message, *args, **kwargs):
        if self.engine.min_levelno > LoggerLevel.ERROR: return
        exc_info = kwargs.pop('exc_info', None)
        if exc_info:
            kwargs['exc_info'] = sys.exc_info()
        await self.log('ERROR', message, args, kwargs)

    async def critical(self, message, *args, **kwargs):
        if self.engine.min_levelno > LoggerLevel.CRITICAL: return
        exc_info = kwargs.pop('exc_info', None)
        if exc_info:
            kwargs['exc_info'] = sys.exc_info()
        await self.log('CRITICAL', message, args, kwargs)

    async def exception(self, message, *args, **kwargs):
        kwargs.pop('exc_info', None)
        await self.error(message, *args, exc_info=True, **kwargs)

logger = AsyncLogger("root")