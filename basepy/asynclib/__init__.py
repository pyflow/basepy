
import asyncio

def wait_async(coro, *, debug=False):
    if not asyncio.iscoroutine(coro):
        raise ValueError("a coroutine was expected, got {!r}".format(coro))

    loop = asyncio.get_event_loop()
    if not loop:
        # should create loop for new thread?
        pass
    try:
        loop.set_debug(debug)
        return loop.run_until_complete(coro)
    except Exception as ex:
        raise(ex)
