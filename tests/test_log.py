
from basepy.log import Logger
import pytest

logger = Logger("basepy-test-log")

@pytest.mark.asyncio
async def test_log(capsys):
    await logger.info('hello')
    captured = capsys.readouterr()
    assert captured.out == ""
    logger.add('stdout')
    assert len(logger.handlers) == 1
    await logger.info('hello')
    captured = capsys.readouterr()
    assert captured.out.endswith("[hello]\n")

@pytest.mark.asyncio
async def test_log_2(capsys):
    logger.handlers = []
    logger.add('stdout')
    await logger.info('hello', data="data", data2={"h":1, "k":2, "x":[1, 2, 3]})
    captured = capsys.readouterr()
    assert captured.out.find('[data = "data"]') > 1
