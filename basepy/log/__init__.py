
import time
import sys
from asyncio import Queue
import traceback
import os
import platform
import json
from basepy.asynclib.async_fluent import AsyncFluentSender

_start_time = time.time()

class LoggerLevel:
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0
    name_level_map = {
        'CRITICAL': CRITICAL,
        'FATAL': CRITICAL,
        'ERROR': ERROR,
        'WARN': WARNING,
        'WARNING': WARNING,
        'INFO': INFO,
        'DEBUG': DEBUG,
        'NOTSET': NOTSET,
    }

    @classmethod
    def get_levelno(cls, name, default=0):
        return cls.name_level_map.get(name.strip().upper(), default)

class BaseHandler(object):
    def handle_error(self, record):
        if sys.stderr:  # see issue 13807
            t, v, tb = sys.exc_info()
            try:
                sys.stderr.write('--- Logging error ---\n')
                traceback.print_exception(t, v, tb, None, sys.stderr)
                sys.stderr.write('Call stack:\n')
                # Walk the stack frame up until we're out of logging,
                # so as to print the calling context.
                frame = tb.tb_frame
                if frame:
                    traceback.print_stack(frame, file=sys.stderr)
                try:
                    sys.stderr.write('Message: %r\n'
                                     'Arguments: %s\n' % (record.msg,
                                                          record.args))
                except Exception:
                    sys.stderr.write('Unable to print the message and arguments'
                                     ' - possible formatting error.\nUse the'
                                     ' traceback above to help find the error.\n'
                                    )
            except OSError: #pragma: no cover
                pass
            finally:
                del t, v, tb

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
            # issue 35046: merged two stream.writes into one.
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handle_error(record)

    def make_message(self, record):
        def format_obj(obj):
            try:
                return json.dumps(obj)
            except:
                return repr(obj)
        data = record.to_dict()
        data['created'] = time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(data['created']))
        msg = self.format_str.format(**data)
        extra = ' '.join(map(lambda x: "[{} = {}]".format(x[0], format_obj(x[1])), record.kwargs.items()))
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

class LogRecord(object):
    def __init__(self, name, level, 
                 msg, args, exc_info, sinfo=None, **kwargs):
        """
        Initialize a logging record with interesting information.
        """
        ct = time.time()
        self.name = name
        self.msg = msg
        self.args = args
        self.levelname = level
        self.levelno = LoggerLevel.get_levelno(level, 60)
        self.exc_info = exc_info
        self.exc_text = None      # used to cache the traceback text
        self.stack_info = sinfo
        self.hostname = platform.node()
        self.process = os.getpid()
        self.created = ct
        self.msecs = (ct - int(ct)) * 1000
        self.msecs_since_start = (self.created - _start_time) * 1000
        self.kwargs = kwargs

    def __repr__(self):
        return '<LogRecord: %s, %s, "%s">'%(self.name, self.levelname, self.msg)

    def get_message(self):
        msg = str(self.msg)
        if self.args:
            msg = msg % self.args
        return msg
    
    def to_dict(self):
        return dict(
            name = self.name,
            level = self.levelname,
            created = self.created,
            hostname = self.hostname,
            process = self.process,
            message = self.get_message(),
            data = self.kwargs
        )
    

class Logger(object):
    handler_class_map = {
        'stdout': StdoutHandler,
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

    def add(self, handler, level="DEBUG", format=None, queue=False, **kwargs):
        h_cls = self.handler_class_map.get(handler)
        if not h_cls:
            raise Exception('no handler class for {}'.format(handler))
        h = h_cls(format=format, queue=queue, level=level, **kwargs)
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

logger = Logger("root")