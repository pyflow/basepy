
from basepy.common.log import  LoggerLevel, LogRecord
from basepy.asynclog import AsyncLogger
import pytest
import json
import asyncio
from basepy.mixins import ToDictMixin

logger = AsyncLogger("basepy-test-log")


@pytest.mark.asyncio
async def test_log(capsys):
    logger.clear()
    await logger.info('hello')
    captured = capsys.readouterr()
    assert captured.out == ""
    logger.add('stdout')
    assert logger.engine.handlers[0].levelno == LoggerLevel.DEBUG
    assert len(logger.engine.handlers) == 1
    await logger.info('hello')
    captured = capsys.readouterr()
    assert captured.out.endswith("[hello]\n")
    logger.clear()

@pytest.mark.asyncio
async def test_log_sync(capsys):
    logger = AsyncLogger("test_log_sync")
    logger.clear()
    logger.add('stdout')
    await logger.init()

    logger = logger.sync()
    logger.info('info')
    await asyncio.sleep(0.1)
    captured = capsys.readouterr()
    print(captured.out)
    assert captured.out.endswith("[info]\n")

    logger = logger.sync()
    logger.debug('debug')
    await asyncio.sleep(0.1)
    captured = capsys.readouterr()
    print(captured.out)
    assert captured.out.endswith("[debug]\n")

    logger = logger.sync()
    logger.warning('warning')
    await asyncio.sleep(0.1)
    captured = capsys.readouterr()
    assert captured.out.endswith("[warning]\n")

    logger = logger.sync()
    logger.critical('critical')
    await asyncio.sleep(0.1)
    captured = capsys.readouterr()
    assert captured.out.endswith("[critical]\n")

    logger = logger.sync()
    logger.error('error')
    await asyncio.sleep(0.1)
    captured = capsys.readouterr()
    assert captured.out.endswith("[error]\n")
    logger.clear()
    await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_log_level(capsys):
    logger.clear()
    logger.add('stdout', level="INFO")
    assert len(logger.engine.handlers) == 1
    assert logger.engine.handlers[0].levelno == LoggerLevel.INFO
    await logger.info('hello')
    captured = capsys.readouterr()
    assert captured.out.endswith("[hello]\n")
    await logger.debug('hello')
    captured = capsys.readouterr()
    assert captured.out == ""
    await logger.critical('critical')
    captured = capsys.readouterr()
    assert captured.out.endswith("[critical]\n")
    logger.clear()

@pytest.mark.asyncio
async def test_log_2(capsys):
    logger.clear()
    logger.add('stdout')
    await logger.info('hello', data="data", data2={"h":1, "k":2, "x":[1, 2, 3]})
    captured = capsys.readouterr()
    #print(captured.out)
    assert captured.out.find('[data = "data"]') > 1
    logger.clear()

@pytest.mark.asyncio
async def test_log_3():
    logger.clear()
    logger.add('socket', host='127.0.0.1', port=9000)
    await logger.info('hello', data="data", data2={"h":1, "k":2, "x":[1, 2, 3]})
    logger.clear()

class Foo:
    def __init__(self):
        self.value = 'foo object'

class FooToJson:
    def __init__(self):
        self.value = 'foo to_json'

    def to_json(self):
        return json.dumps({'class':type(self).__name__, 'value':self.value})

class FooWithMixin(ToDictMixin, object):
    def __init__(self):
        self.foo= 'foo_with_jsonmixin_foo_value'
        self.bar = {"bar_bar": {"sub_bar_bar": "subbarbar_with_jsonmixin_subbarbar_value"}}

@pytest.mark.asyncio
async def test_log_have_no_to_json(capsys):
    logger.clear()
    logger.add('stdout')
    await logger.info('hello', data="data", data2=Foo())
    captured = capsys.readouterr()
    assert captured.out.find('{"value": "foo object"}') > 1
    await logger.info('hello', data='foo_to_json', data2=FooToJson())
    captured = capsys.readouterr()
    #print(captured.out)
    assert captured.out.find('[data = "foo_to_json"]') > 1
    lr = LogRecord('record', "INFO", "Record Message", [], None, data="record_data", data2=FooWithMixin())
    data = lr.to_dict()
    assert isinstance(data['data']['data2'], dict)
    assert data['data']['data2']['foo'] ==  'foo_with_jsonmixin_foo_value'
    await logger.info('hello', data='foo_with_jsonmixin', data2=FooWithMixin())
    captured = capsys.readouterr()
    #print(captured.out)
    assert captured.out.find('foo_with_jsonmixin_foo_value') > 1
    logger.clear()
