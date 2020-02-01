
import asyncio
from basepy.log import logger

logger.add("stdout")

async def main():
    await logger.info("hello")
    await logger.info("stuct", a=1, b=2, hello='world')


asyncio.run(main())



