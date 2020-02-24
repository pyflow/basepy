
from basepy.log import Logger, LoggerLevel, LogRecord
import pytest
import json
from basepy.mixins import ToJsonMixin

logger = Logger("basepy-test-log")


@pytest.mark.asyncio
async def test_log(capsys):
    logger.clear()
    await logger.info('hello')
    captured = capsys.readouterr()
    assert captured.out == ""
    logger.add('stdout')
    assert logger.handlers[0].levelno == LoggerLevel.DEBUG
    assert len(logger.handlers) == 1
    await logger.info('hello')
    captured = capsys.readouterr()
    assert captured.out.endswith("[hello]\n")
    logger.clear()

@pytest.mark.asyncio
async def test_log_level(capsys):
    logger.clear()
    logger.add('stdout', level="INFO")
    assert len(logger.handlers) == 1
    assert logger.handlers[0].levelno == LoggerLevel.INFO
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

class FooWithMixin(ToJsonMixin, object):
    def __init__(self):
        self.foo= 'foo_with_jsonmixin_foo_value'
        self.bar = {"bar_bar": {"sub_bar_bar": "subbarbar_with_jsonmixin_subbarbar_value"}}

@pytest.mark.asyncio
async def test_log_have_no_to_json(capsys):
    logger.clear()
    logger.add('stdout')
    await logger.info('hello', data="data", data2=Foo())
    captured = capsys.readouterr()
    assert captured.out == ''
    await logger.info('hello', data='foo_to_json', data2=FooToJson())
    captured = capsys.readouterr()
    #print(captured.out)
    assert captured.out.find('[data = "foo_to_json"]') > 1
    lr = LogRecord('record', "INFO", "Record Message", [], None, data="record_data", data2=FooWithMixin())
    data = lr.to_dict()
    assert isinstance(data['data']['data2'], str)
    assert data['data']['data2'].find('foo_with_jsonmixin_foo_value') > 1
    await logger.info('hello', data='foo_with_jsonmixin', data2=FooWithMixin())
    captured = capsys.readouterr()
    assert captured.out.find('foo_with_jsonmixin_foo_value') > 1
    logger.clear()
