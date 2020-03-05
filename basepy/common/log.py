import time
import sys
import traceback
import platform
import os
from inspect import currentframe, getframeinfo
from basepy.mixins import ToDictMixin

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
        self.debuginfo = kwargs.pop('debuginfo', '')
        self.kwargs = kwargs

    def __repr__(self):
        return '<LogRecord: %s, %s, "%s">'%(self.name, self.levelname, self.msg)

    def get_message(self):
        msg = str(self.msg)
        if self.args:
            msg = msg % self.args
        if self.exc_info:
            if isinstance(self.exc_info, Exception):
                exc_str = '<{}>: {}'.format(type(self.exc_info).__name__, str(self.exc_info))
            elif isinstance(self.exc_info, (tuple, list)):
                exc_str = ''.join(traceback.format_exception(*self.exc_info))
            else:
                exc_str = str(self.exc_info)
            msg = '{}\n{}\n'.format(msg, exc_str)
        return msg

    def to_dict(self):
        def format_obj(obj):
            # if isinstance(obj, str):
            #     return obj
            try:
                if hasattr(obj, "to_dict"):
                    return obj.to_dict()
                return ToDictMixin.dump_obj(obj)
            except:
                raise Exception('Object can not covert to json dict or not have `to_dict` method.')
        data = dict([(k, format_obj(v)) for k, v in self.kwargs.items()])
        return dict(
            name = self.name,
            level = self.levelname,
            created = self.created,
            hostname = self.hostname,
            process = self.process,
            debuginfo = self.debuginfo,
            message = self.get_message(),
            data = data
        )
