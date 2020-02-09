import asyncio
import inspect
import threading
import time
import typing
import warnings
from functools import partial, wraps
from types import MappingProxyType
from typing import NamedTuple
from .log import logger


try:
    import contextvars

    def context_partial(func, *args, **kwargs):
        context = contextvars.copy_context()
        return partial(context.run, func, *args, **kwargs)

except ImportError:
    context_partial = partial


def run_in_executor(func, executor=None, args=(),
                    kwargs=MappingProxyType({})) -> asyncio.Future:

    loop = asyncio.get_event_loop()
    # noinspection PyTypeChecker
    return loop.run_in_executor(
        executor, context_partial(func, *args, **kwargs)
    )


async def _awaiter(future):
    try:
        result = await future
        return result
    except asyncio.CancelledError as e:
        if not future.done():
            future.set_exception(e)
        raise


def threaded(func):
    if asyncio.iscoroutinefunction(func):
        raise TypeError('Can not wrap coroutine')

    if inspect.isgeneratorfunction(func):
        raise TypeError('Can not wrap generator')

    @wraps(func)
    def wrap(*args, **kwargs):
        future = run_in_executor(func=func, args=args, kwargs=kwargs)
        result = _awaiter(future)
        return result

    return wrap


def run_in_new_thread(func, args=(), kwargs=MappingProxyType({}),
                      detouch=True, no_return=False) -> asyncio.Future:
    loop = asyncio.get_event_loop()
    future = loop.create_future()

    def set_result(result):
        if future.done() or loop.is_closed():
            return

        future.set_result(result)

    def set_exception(exc):
        if future.done() or loop.is_closed():
            return

        future.set_exception(exc)

    @wraps(func)
    def in_thread(target):
        try:
            loop.call_soon_threadsafe(
                set_result, target()
            )
        except Exception as exc:
            if loop.is_closed() and no_return:
                return

            elif loop.is_closed():
                logger.exception("Uncaught exception from separate thread")
                return

            loop.call_soon_threadsafe(set_exception, exc)

    thread = threading.Thread(
        target=in_thread, name=func.__name__,
        args=(
            context_partial(func, *args, **kwargs),
        ),
    )

    thread.daemon = detouch

    loop.call_soon_threadsafe(thread.start)
    return future


def threaded_separate(func, detouch=True):
    if isinstance(func, bool):
        return partial(threaded_separate, detouch=detouch)

    if asyncio.iscoroutinefunction(func):
        raise TypeError('Can not wrap coroutine')
    
    if inspect.isgeneratorfunction(func):
        raise TypeError('Can not wrap generator')

    @wraps(func)
    def wrap(*args, **kwargs):
        future = run_in_new_thread(
            func, args=args, kwargs=kwargs, detouch=detouch
        )

        return _awaiter(future)

    return wrap


class CoroutineWaiter:
    def __init__(self, loop: asyncio.AbstractEventLoop, coroutine_func,
                 *args, **kwargs):
        self.__func = partial(coroutine_func, *args, **kwargs)
        self.__loop = loop
        self.__event = threading.Event()
        self.__result = None
        self.__exception = None

    def _on_result(self, task: asyncio.Task):
        self.__exception = task.exception()
        if self.__exception is None:
            self.__result = task.result()
        self.__event.set()

    def _awaiter(self):
        task = self.__loop.create_task(self.__func())
        task.add_done_callback(self._on_result)

    def start(self):
        self.__loop.call_soon_threadsafe(self._awaiter)

    def wait(self):
        self.__event.wait()
        if self.__exception is not None:
            raise self.__exception
        return self.__result


def sync_wait_coroutine(loop, coro_func, *args, **kwargs):
    waiter = CoroutineWaiter(loop, coro_func, *args, **kwargs)
    waiter.start()
    return waiter.wait()