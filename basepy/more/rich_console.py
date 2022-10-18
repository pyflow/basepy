
import time
import sys
import json
from basepy.common.log import LoggerLevel, LogRecord, BaseHandler
from basepy.asynclog import AsyncLoggerEngine, logger

from rich.console import Console
from rich.text import Text
from rich.pretty import pprint
from rich.traceback import install



class RichConsoleHandler(BaseHandler):
    terminator = '\n'
    color_map = {
        'DEBUG': 'yellow',
        'INFO': 'cyan',
        'WARNING': 'magenta',
        'ERROR': 'red',
        'CRITICAL': 'red'
    }
    def __init__(self, stream=None, level="DEBUG", **kwargs):
        self.stream = sys.stdout
        self.console = Console(file=self.stream, log_time=False, log_path=False)
        self.isatty = self.stream.isatty()
        self.level = level
        self.levelno = LoggerLevel.get_levelno(self.level, 0)


    def flush(self):
        if self.stream and hasattr(self.stream, "flush"):
            self.stream.flush()

    def get_level_color(self, level):
        l = level.upper()
        return self.color_map.get(l, '')

    async def emit(self, record):
        try:
            data = record.to_dict()
            data['created'] = time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(data['created']))
            stream = self.stream
            level = data['level'].upper()
            if self.isatty:
                text = Text()
                text.append(data['created'][11:], style="green")
                text.append(' | ')
                text.append(level, style="bold " + self.get_level_color(level))
                text.append(' | ')
                text.append(data['message'], style=" " + self.get_level_color(level))
                self.console.log(text)
                if data['data']:
                    pprint(data['data'], console=self.console, max_depth=5)
            else:
                msg = json.dumps(data)
                stream.write('{}{}'.format(msg, self.terminator))

            self.flush()
        except Exception:
            self.handle_error(record)

    def __repr__(self):
        level = ""
        name = getattr(self.stream, 'name', '')
        name = str(name)
        if name:
            name += ' '
        return '<%s %s(%s)>' % (self.__class__.__name__, name, level)

def install_rich_console():
    AsyncLoggerEngine.register_handler('rich_console', RichConsoleHandler)
    logger.add('rich_console')
    install(show_locals=True)