import asyncio
import gc
import os
import threading
import time
import weakref
from contextlib import suppress
from contextlib import contextmanager
from basepy.asynclib.timeout import timeout
from concurrent.futures import ThreadPoolExecutor
from basepy.asynclib.threaded import threaded, threaded_separate, sync_wait_coroutine

import pytest

try:
    import contextvars
except ImportError:
    contextvars = None


pytestmark = pytest.mark.asyncio

@pytest.fixture
def timer():
    @contextmanager
    def timer(expected_time=0, *, dispersion=0.5):
        expected_time = float(expected_time)
        dispersion_value = expected_time * dispersion

        now = time.monotonic()

        yield

        delta = time.monotonic() - now

        lower_bound = expected_time - dispersion_value
        upper_bound = expected_time + dispersion_value

        assert lower_bound < delta < upper_bound

    return timer

@pytest.fixture(params=(threaded, threaded_separate))
def threaded_decorator(request, executor):
    assert executor
    return request.param


@pytest.fixture
def executor():
    thread_pool = ThreadPoolExecutor(max_workers=8)
    loop = asyncio.get_event_loop()
    loop.set_default_executor(thread_pool)
    try:
        yield thread_pool
    finally:
        with suppress(Exception):
            thread_pool.shutdown(wait=True)

        thread_pool.shutdown(wait=True)


async def test_threaded(threaded_decorator, timer):
    sleep = threaded_decorator(time.sleep)

    @timeout(5)
    async def _test_threaded():
        with timer(1):
            await asyncio.gather(
                sleep(1),
                sleep(1),
                sleep(1),
                sleep(1),
                sleep(1)
            )
    await _test_threaded()


async def test_threaded_exc(threaded_decorator):
    @threaded_decorator
    def worker():
        raise Exception

    @timeout(1)
    async def _test_threaded_exc():
        number = 90

        done, _ = await asyncio.wait([asyncio.create_task(worker()) for _ in range(number)])

        for task in done:
            with pytest.raises(Exception):
                task.result()
    await _test_threaded_exc()


async def test_simple(threaded_decorator, timer):
    sleep = threaded_decorator(time.sleep)

    @timeout(2)
    async def _test_simple():
        with timer(1):
            await asyncio.gather(
                sleep(1),
                sleep(1),
                sleep(1),
                sleep(1),
            )
    await _test_simple()


@pytest.mark.skipif(contextvars is None, reason="no contextvars support")
async def test_context_vars(threaded_decorator):
    ctx_var = contextvars.ContextVar("test")

    @threaded_decorator
    def test(arg):
        value = ctx_var.get()
        assert value == arg * arg

    futures = []

    for i in range(8):
        ctx_var.set(i * i)
        futures.append(test(i))

    await asyncio.gather(*futures)


async def test_wait_coroutine_sync(threaded_decorator):
    loop = asyncio.get_event_loop()
    result = 0

    async def coro():
        nonlocal result
        await asyncio.sleep(1)
        result = 1

    @threaded_decorator
    def test():
        sync_wait_coroutine(loop, coro)

    await test()
    assert result == 1


async def test_wait_coroutine_sync_exc(threaded_decorator):
    loop = asyncio.get_event_loop()
    result = 0

    async def coro():
        nonlocal result
        await asyncio.sleep(1)
        result = 1
        raise RuntimeError("Test")

    @threaded_decorator
    def test():
        sync_wait_coroutine(loop, coro)

    with pytest.raises(RuntimeError):
        await test()

    assert result == 1