from datetime import datetime
import time

from basepy.cache import memoized


# timing function execution time
def timeit(func):
    def inner(*args, **kwargs):
        time_1 = datetime.now()
        rv = func(*args, **kwargs)
        time_2 = datetime.now()
        return rv, (time_2-time_1).total_seconds()
    return inner


# not caching function
def some_function(n):
    """Return the nth fibonacci number."""
    time.sleep(1)
    return n*2


@memoized
def some_function_2(n):
    """Return the nth fibonacci number."""
    time.sleep(2)
    return n*2


def test_memorized():
    func1 = timeit(some_function)
    func2 = timeit(some_function_2)
    _, t = func1(100)
    assert t >= 1.0
    _, t = func2(1002)
    assert t >= 1.0
    _, t = func2(1002)
    assert t <= 0.5
