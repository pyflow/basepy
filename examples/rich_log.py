
import asyncio
from basepy.asynclog import logger
from basepy.more.rich_console import install_rich_console

install_rich_console()

async def main():
    await logger.debug("this is debug message", scope="debug")
    await logger.info("this is info message", scope="info")
    await logger.info("hello")
    await logger.info("stuct", a=1, b=2, hello='world')
    await logger.warning("warning", a=1, b=2, hello='world')


asyncio.run(main())
