
import time
import sys
import traceback
import os
import platform
import json
from queue import Queue
from basepy.common.log import LoggerLevel, LogRecord, BaseHandler
from basepy.network.connection import BlockingConnectionPool
import inspect
from inspect import currentframe, getframeinfo
import socket

class StdoutHandler(BaseHandler):
    terminator = '\n'
    def __init__(self, stream=None, format=None, level="DEBUG", **kwargs):
        if stream is None:
            stream = sys.stdout
        self.stream = stream
        self.format_str = "[{created}] [{hostname}.{process}] [{level}] [{debuginfo}] [{message}]"
        self.level = level
        self.levelno = LoggerLevel.get_levelno(self.level, 0)


    def flush(self):
        if self.stream and hasattr(self.stream, "flush"):
            self.stream.flush()

    def emit(self, record):
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
        if connection_type.upper() in ['TCP', 'UNIXSOCKET']:
            self.tcp_pool = BlockingConnectionPool(max_connections=4, timeout=6, host=self.host,
                port=self.port)
            self.udp_socket = None
        elif connection_type.upper() in ['UDP']:
            self.tcp_pool = None
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


    def flush(self):
        pass

    def _write_tcp(self, data):
        conn = self.tcp_pool.get_connection()
        conn.write(data)


    def _write_udp(self, data):
        if len(data) > 65500:
            raise ValueError('data is to large for udp, {} must < 65500.'%(len(data)))
        self.udp_socket.sendto(data, (self.host, self.port))

    def _write(self, data):
        if self.connection_type.upper() == "TCP":
            self._write_tcp(data)
        elif self.connection_type.upper() == "UDP":
            self._write_udp(data)

    def emit(self, record):
        try:
            msg = "{}{}".format(json.dumps(record.to_dict()), self.terminator)
            self._write(msg.encode("utf-8"))
        except Exception:
            self.handle_error(record)


    def __repr__(self):
        return '<%s [%s:%s(%s)]>' % (self.__class__.__name__, self.host, self.port, self.level)


class Logger(object):
    handler_class_map = {
        'stdout': StdoutHandler,
        'socket': SocketHandler
    }
    def __init__(self, name="", **kwargs):
        self.name = name
        self.handlers = []
        self.queue = None
        self.queued_handlers = []
        self.dev_mode = True
        self.hostname = platform.node()

    def init(self, config):
        self.init_queue()
        handlers = config['handlers']
        for handler in handlers:
            conf = config.get(handler, {}).to_dict()
            handler_type = conf.pop('handler_type', '')
            if handler_type not in self.handler_class_map:
                continue
            self.add(handler_type, **conf)

    def init_queue(self):
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

    def get_debuginfo(self):
        current = inspect.currentframe()
        frames = inspect.getouterframes(current, 1)
        for frame in frames:
            if not frame.filename.endswith('/basepy/log/__init__.py'):
                return '{}:{}'.format(frame.filename, frame.lineno)
        return 'no-frameinfo'

    def log(self, level, message, args, kwargs):
        handlers, queued_handlers = self._filter_handlers(level)
        if len(handlers) + len(queued_handlers) == 0:
            return None

        debuginfo = self.get_debuginfo() if level=="DEBUG" else ":0"
        record = LogRecord(self.name, level, message, args, None, debuginfo=debuginfo, **kwargs)
        if len(self.handlers) > 0:
            for handler in self.handlers:
                handler.emit(record)

        if len(self.queued_handlers) > 0:
            self.queue.put(record)


    def debug(self, message, *args, **kwargs):
        if self.dev_mode:
            self.log('DEBUG', message, args, kwargs)

    def info(self, message, *args, **kwargs):
        self.log('INFO', message, args, kwargs)

    def warning(self, message, *args, **kwargs):
        self.log('WARNING', message, args, kwargs)

    def error(self, message, *args, **kwargs):
        self.log('ERROR', message, args, kwargs)

    def critical(self, message, *args, **kwargs):
        self.log('CRITICAL', message, args, kwargs)

    def exception(self, message, *args, exc_info=True, **kwargs):
        self.error(message, *args, exc_info=exc_info, **kwargs)

logger = Logger("root")