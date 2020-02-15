
from basepy.log import Logger, LoggerLevel
import pytest

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
    assert captured.out.find('[data = "data"]') > 1
    logger.clear()
