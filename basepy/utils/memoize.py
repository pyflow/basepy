import collections
import functools
try:
    import asyncio
except (ImportError, SyntaxError):
    asyncio = None

class memoized(object):
    '''Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    '''
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        if not isinstance(args, collections.Hashable):
         # uncacheable. a list, for instance.
         # better to not cache than blow up.
            return self.func(*args)
        if args in self.cache:
            return self.cache[args]
        else:
            value = self.func(*args)
            self.cache[args] = value
        return value

    def __repr__(self):
        '''Return the function's docstring.'''
        return self.func.__doc__

    def __get__(self, obj, objtype):
        '''Support instance methods.'''
        return functools.partial(self.__call__, obj)


_memoize_cache = {}

def memoize_factory(name, func):
    """
    Return a memoizing metaclass with the given name and key function.
    And yes that makes this a parametrized meta-metaclass, which is probably
    the most meta thing you've ever seen. If it isn't, both congratulations
    and sympathies are in order!
    """

    def call(cls, *args, **kwargs):
        key = func(cls, args, kwargs)
        try:
            return _memoize_cache[key]
        except KeyError:
            instance = type.__call__(cls, *args, **kwargs)
            _memoize_cache[key] = instance
            return instance

    mc = type(name, (type,), {'__call__': call})
    return mc


MemoizeMetaclass = memoize_factory("MemoizeMetaclass",
                                   lambda cls, args, kwargs: (cls, ) + args + tuple(kwargs.items()))


def with_metaclass(meta, base=object):
    """
    Create a base class with a metaclass. Compatible across Python 2 and Python
    3. Extension of the with_metaclass() found in the six module.
    """
    if not isinstance(base, tuple):
        basetuple = (base,)
    return meta("NewBase", basetuple, {})

def memoize_class(base=object):
    if not isinstance(base, tuple):
        basetuple = (base,)
    return MemoizeMetaclass("NewBase", basetuple, {})


# Some reading:
# http://bytes.com/topic/python/answers/40084-parameterized-metaclass-metametaclass
# http://www.acooke.org/cute/PythonMeta0.html
# http://www.python.org/dev/peps/pep-3115/
