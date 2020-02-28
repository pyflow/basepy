
from basepy.common.log import  LoggerLevel, LogRecord
from basepy.log import Logger
import pytest
import json
from basepy.mixins import ToDictMixin

logger = Logger("basepy-test-log")


def test_log(capsys):
    logger.clear()
    logger.info('hello')
    captured = capsys.readouterr()
    assert captured.out == ""
    logger.add('stdout')
    assert logger.handlers[0].levelno == LoggerLevel.DEBUG
    assert len(logger.handlers) == 1
    logger.debug('hello')
    captured = capsys.readouterr()
    print(captured.out)
    assert captured.out.endswith("[hello]\n")
    logger.clear()

def test_log_level(capsys):
    logger.clear()
    logger.add('stdout', level="INFO")
    assert len(logger.handlers) == 1
    assert logger.handlers[0].levelno == LoggerLevel.INFO
    logger.info('hello')
    captured = capsys.readouterr()
    assert captured.out.endswith("[hello]\n")
    logger.debug('hello')
    captured = capsys.readouterr()
    assert captured.out == ""
    logger.critical('critical')
    captured = capsys.readouterr()
    print(captured.out)
    assert captured.out.endswith("[critical]\n")
    logger.clear()

def test_log_2(capsys):
    logger.clear()
    logger.add('stdout')
    logger.info('hello', data="data", data2={"h":1, "k":2, "x":[1, 2, 3]})
    captured = capsys.readouterr()
    print(captured.out)
    assert captured.out.find('[data = "data"]') > 1
    logger.clear()

def test_log_3(capsys):
    logger.clear()
    logger.add('socket', host='127.0.0.1', port=9000)
    logger.info('hello', data="data", data2={"h":1, "k":2, "x":[1, 2, 3]})
    captured = capsys.readouterr()
    print(captured.out)
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

def test_log_have_no_to_json(capsys):
    logger.clear()
    logger.add('stdout')
    logger.info('hello', data="data", data2=Foo())
    captured = capsys.readouterr()
    assert captured.out.find('{"value": "foo object"}') > 1
    logger.info('hello', data='foo_to_json', data2=FooToJson())
    captured = capsys.readouterr()
    #print(captured.out)
    assert captured.out.find('[data = "foo_to_json"]') > 1
    lr = LogRecord('record', "INFO", "Record Message", [], None, data="record_data", data2=FooWithMixin())
    data = lr.to_dict()
    assert isinstance(data['data']['data2'], dict)
    assert data['data']['data2']['foo'] ==  'foo_with_jsonmixin_foo_value'
    logger.info('hello', data='foo_with_jsonmixin', data2=FooWithMixin())
    captured = capsys.readouterr()
    #print(captured.out)
    assert captured.out.find('foo_with_jsonmixin_foo_value') > 1
    logger.clear()
