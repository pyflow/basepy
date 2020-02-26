# basepy
Basic library for python 3.6+, includes:

* config loader
* structure logger
* program metrics (statsd)
* exception logger (via sentry)
* datastructures for asyncio

## log

Very simple and powerful log system, support structure log. It's not depends on python builtin `logging` module.

```python
import asyncio
from basepy.asynclog import logger

logger.add("stdout")

async def main():
    await logger.info("hello")
    await logger.info("stuct", a=1, b=2, hello='world')


asyncio.run(main())

```

And the code will generated.

```
[2020-02-01 11:42:07 +0800] [local.72267] [INFO] [hello]
[2020-02-01 11:42:07 +0800] [local.72267] [INFO] [stuct] [a = 1] [b = 2] [hello = "world"]
```

## config

Config module is easy and powerful settings configuration with following features.

1. keep secrets related in sperate file `.secrets.toml`
2. keep local config in sperate file `settings.local.toml` or `.secrets.local.toml`, the local settings will override the settings for the same key.

So, config files should looks like

```
application
├── .secrets.local.toml
├── .secrets.toml
├── settings.local.toml
└── settings.toml
```

The `.secrets.toml` should contains several keys, like

```toml
signing_secret = "local_a"
access_token = "local_b"
```

To access secrets in program, just use `settings.secrets`

```python
from basepy.config import settings

print(settings.secrets.signing_secret) # will print "local_a"

```

The `settings.toml` can contains very complex setting, for example

```toml
[log]
    handlers = ["stdout", "local_fluent"]

    [log.stdout]
    handler_type = "stdout"
    level = "debug"

    [log.local_fluent]
    handler_type = "fluent"
    host = "127.0.0.1"
    port = 24224
    tag = "basepy"
    level = "info"
```

To access normal setting, just use `settings.key`

```
from basepy.config import setting
print(setting.log.handlers)
```

## more
Please refer the docs directory.
