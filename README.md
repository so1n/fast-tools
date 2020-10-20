# fast-tools
`fast-tools` is a `FastApi/Starlette` toolset, Most of the tools can be used in FastApi/Starlette, a few tools only support `FastApi` which is divided into the lack of compatibility with `FastApi` 

Note: this is alpha quality code still, the API may change, and things may fall apart while you try it.

```python
# origin of name 
project_name = ('FastApi'[:2] + 'Starlette'[:2]).lower() + '-tools'
print(project_name)  # 'fast-tools'
```
[中文文档](https://github.com/so1n/fast-tools/blob/master/README_CH.md)
# Usage
## 0.base
- explanation: Some tool dependencies of `fast-tools` and can also be used alone
- applicable framework:`FastApi`,`Starlette`, more....
### 0.1.redis_helper
- explanation: It is used to encapsulate the conn pool of aioredis and encapsulate some common commands. 
```python
import aioredis
from fastapi import FastAPI
from fast_tools.base import RedisHelper


app: 'FastApi' = FastAPI()
redis_helper: 'RedisHelper' = RedisHelper()  # init object


@app.on_event("startup")
async def startup():
    # create redis conn pool and connect
    redis_helper.init(await aioredis.create_pool('redis://localhost', minsize=1, maxsize=10, encoding='utf-8'))

app.on_event("shutdown")
async def shutdown():
    # close redis conn pool
    await redis_helper.close()


@app.get("/")
async def root() -> dict:
    info = await redis_helper.redis_pool.info()
    return {"info": info}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
### 0.2.route_trie
Most of python's web framework routing lookups traverse the entire routing table. If the current url matches the registered url of the route, the lookup is successful. It can be found that the time complexity of the route lookup is O(n).
I guess the reason why the python web framework uses the traversal routing table is to support `/api/user/{user_id}` while keeping it simple.
It can be found that the time complexity of each route lookup is O(n). When the number of routes reaches a certain level, the matching time will becomes slower, but when we use middleware, if we need to check whether the route is matched, then It needs to be matched again, and this piece of ours can be controlled, so we need to optimize the routing matching speed here.

The fastest route matching speed is dict, but it cannot support urls similar to `/api/user/{user_id}`. Fortunately, the url matches the data structure of the trie, so the trie is used to refactor the route search, which can be as fast as possible Match the approximate area of the route, and then perform regular matching to check whether the route is correct.
```Python
from typing import (
    List,
    Optional
)
from fastapi import FastAPI
from starlette.routing import Route
from fast_tools.base import RouteTrie

app: 'FastAPI' = FastAPI()


@app.get("/")
async def root() -> dict:
    return {"Hello": "World"}


@app.get("/api/users/login")
async def user_login() -> str:
    return 'ok'


route_trie: RouteTrie = RouteTrie()  # init route trie
route_trie.insert_by_app(app)  # load route from app


def print_route(route_list: Optional[List[Route]]):
    """print route list
    """
    if route_list:
        for route in route_list:
            print(f'route:{route} url:{route.path}')
    else:
        print(f'route:{route_list} url: not found')

# Scope param is needed to match app routing, you can learn more from the exporter example
print_route(route_trie.search('/'))
print_route(route_trie.search('/api/users/login'))
```
[Simply compare the efficiency of the built-in route matching and trie matching](https://github.com/so1n/fast-tools/blob/master/example/route_trie_simple_benchmarks.py)
## 1.exporter
- explanation: A prometheus exporter middleware that can be used for `Starlette` and `FastAPI`, which can monitor the status of each URL, such as the number of connections, the number of responses, the number of requests, the number of errors, and the number of current requests. 
- applicable framework: `FastApi`,`Starlette`

### 1.1 install
pip install prometheus_client
### 1.2 Usage
```python
from typing import Optional

from fastapi import FastAPI
from fast_tools.exporter import PrometheusMiddleware, get_metrics
from fast_tools.base.route_trie import RouteTrie


app = FastAPI()
route_trie = RouteTrie()

app.add_middleware(
    PrometheusMiddleware,
    route_trie=route_trie,      # use route trie, speed up routing query
    block_url_set={"/metrics"}  # not monitor url: /metrics
)

app.add_route("/metrics", get_metrics)
```
### 1.3 example
[example](https://github.com/so1n/fastapi-tools/blob/master/example/exporter.py)
## 2.cbv
- explanation: At present, due to the changes of fastapi, fastapi does not yet support cbv mode, only [fastapi_utils](https://github.com/dmontagu/fastapi-utils/blob/master/fastapi_utils/cbv.py)
Provides cbv support, but I feel that it is not very convenient to use, so I reused its core code and made some modifications.You can use cbv like Starlette, and provide cbv_decorator to support other functions of fastapi.
- applicable framework: `FastApi`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'so1n'
__date__ = '2020-08'
from fastapi import FastAPI, Depends, Header, Query
from fast_tools.cbv import cbv_decorator, Cbv

app = FastAPI()


def get_user_agent(user_agent: str = Header("User-Agent")) -> str:
    return user_agent


class TestCbv(object):
    # Don't worry about the parent attribute. 
    # Every time the get or post method is called, a new object is actually created and passed in through self.
    # Different requests will not share the same object.
    host: str = Header('host')
    user_agent: str = Depends(get_user_agent)

    def __init__(self, test_default_id: int = Query(123)):
        """support __init__ method param"""
        self.test_default_id = test_default_id

    def _response(self):
        return {"message": "hello, world", "user_agent": self.user_agent, "host": self.host, "id": self.test_default_id}

    @cbv_decorator(status_code=203)   # only support fastapi.route.add_api_route keywords param
    def get(self):
        return self._response()

    def post(self):
        return self._response()


app.include_router(Cbv(TestCbv).router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
## 3.config
- explanation: config is an object that provides configuration files to be converted into python objects. config is based on `Pydantic` and Type Hints, so it can quickly convert or verify parameters without using a large amount of code.
- applicable framework: `FastApi`,`Starlette`
```python
from typing import List, Optional
from fast_tools.config import Config

from pydantic.fields import Json


class MyConfig(Config):
    DEBUG: bool
    HOST: str
    PORT: int

    REDIS_ADDRESS: str
    REDIS_PASS: Optional[str] = None  # Set the default value, if the configuration file does not have this value and does not set the default value, an error will be reported 

    MYSQL_DB_HOST: str
    MYSQL_DB_NAME: str
    MYSQL_DB_PASS: str
    MYSQL_DB_USER: str
    ES_HOST: Json[List]
    TEST_LIST_INT: Json[List]
    YML_ES_HOST: Optional[List[str]] = None
    YML_TEST_LIST_INT: Optional[List[int]] = None
```
config supports the following parameters:
- config_file: config file,Support ini and yml config files, f the value is empty, data is pulled from environment variables (but only a global dictionary is pulled), see [example](https://github.com/so1n/fast-tools/tree/master/example /config)
- group: group can specify a configuration group. When using ini and yml files, multiple group configurations are supported, such as dev configuration and test configuration. If you don't want to configure this option in the code, you can directly configure group=test in the environment variable.
- global_key: Specify that group as the global configuration. When using ini and yml files, multiple group configurations are supported, and there is also a global configuration, which can be shared by multiple groups (if the group does not have a corresponding configuration, it will be referenced to the global_key Configuration, if there is no reference) 

see [example](https://github.com/so1n/fastapi-tools/blob/master/example/config/__init__.py)
## 4.context
- explanation:Using the characteristics of `contextvars`, you can conveniently call what you need in the route, without the need to call like requests.app.state, and it can also support type hints to facilitate writing code.
- applicable framework: `FastApi`,`Starlette`

```python
import asyncio
import httpx
import uuid
from contextvars import (
    copy_context,
    Context
)
from functools import partial
from fastapi import (
    FastAPI,
    Request,
    Response
)
from fast_tools.context import (
    ContextBaseModel,
    ContextMiddleware,
    CustomHelper,
    HeaderHelper,
)

app = FastAPI()
client = httpx.AsyncClient()


class ContextModel(ContextBaseModel):
    # ContextBaseModel  save data to contextvars
    request_id: str = HeaderHelper(
        'X-Request-Id',
        default_func=lambda request: str(uuid.uuid4())
    )
    ip: str = HeaderHelper(
        'X-Real-IP',
        default_func=lambda request: request.client.host
    )
    user_agent: str = HeaderHelper('User-Agent')
    
    # CustomHelper is a encapsulation of Context calls, and data can be read in the current context (if you want to set data, you need to instantiate it first) 
    http_client: httpx.AsyncClient = CustomHelper('http_client')

    async def before_request(self, request: Request):
        """The method that will be called before the request is executed"""
        self.http_client = httpx.AsyncClient()

    async def after_response(self, request: Request, response: Response):
        """The method that will be called after the request is executed"""
        pass

    async def before_reset_context(self, request: Request, response: Response):
        """The method that will be called before the context is destroyed"""
        await self.http_client.aclose()

# ContextMiddleware is used to store data to ContextBaseModel before requesting, and to reset contextvars data before responding to data 
app.add_middleware(ContextMiddleware, context_model=ContextModel())


async def test_ensure_future():
    print(f'test_ensure_future {ContextModel.http_client}')


def test_run_in_executor():
    print(f'test_run_in_executor {ContextModel.http_client}')


def test_call_soon():
    print(f'test_call_soon {ContextModel.http_client}')


@app.get("/")
async def root():
    # Python will automatically copy the context 
    asyncio.ensure_future(test_ensure_future())
    loop: 'asyncio.get_event_loop()' = asyncio.get_event_loop()

    # Python will automatically copy the context 
    loop.call_soon(test_call_soon)

    # When opening another thread for processing, you need to copy the context yourself            
    ctx: Context = copy_context()
    await loop.run_in_executor(None, partial(ctx.run, test_run_in_executor))

    return {
        "message": ContextModel.to_dict(is_safe_return=True),  # Only return data that can be converted to json 
        "local_ip": (await ContextModel.http_client.get('http://icanhazip.com')).text
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
## 5.statsd_middleware
- explanation: The method of use is similar to exporter, but there is an additional `url_replace_handle` to handle url
- applicable framework: `FastApi`,`Starlette`
### 5.1install
pip install aiostatsd
```python
from typing import Optional

from fastapi import FastAPI
from fast_tools.statsd_middleware import StatsdClient, StatsdMiddleware
from fast_tools.base.route_trie import RouteTrie


app = FastAPI()
client = StatsdClient()
route_trie = RouteTrie()

app.add_middleware(
    StatsdMiddleware,
    client=client,
    route_trie=route_trie,
    url_replace_handle=lambda url: url.replace('/', '_'), # Metric naming does not support'/' symbol
    block_url_set={"/"}
)
app.on_event("shutdown")(client.close)


@app.on_event("startup")
async def startup_event():
    await client.connect()
    route_trie.insert_by_app(app)


@app.get("/")
async def root():
    return {"Hello": "World"}


@app.get("/api/users/{user_id}/items/{item_id}")
async def read_user_item(
    user_id: int, item_id: str, q: Optional[str] = None, short: bool = False
):
    """
    copy from:https://fastapi.tiangolo.com/tutorial/query-params/#multiple-path-and-query-parameters
    """
    item = {"item_id": item_id, "owner_id": user_id}
    if q:
        item.update({"q": q})
    if not short:
        item.update(
            {"description": "This is an amazing item that has a long description"}
        )
    return item


@app.get("/api/users/login")
async def user_login():
    return 'ok'


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
## 6.task
- explanation:The ideal architecture does not need to use `task`, so `task` is not recommended, but it may be used in the evolution of the architecture
- applicable framework: `FastApi`,`Starlette`
```python
import time
from fastapi import FastAPI
from fast_tools.task import background_task
from fast_tools.task import stop_task

app = FastAPI()

# call before start
@app.on_event("startup")
# Execute every 10 seconds
@background_task(seconds=10)
def test_task() -> None:
    print(f'test.....{int(time.time())}')

# stop
app.on_event("shutdown")(stop_task)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
## 7.cache
- explanation: Use the return type hint of the function to adaptively cache the corresponding response, and return the cached data when the next request and the cache time has not expired. 
- applicable framework: `FastApi`,`Starlette`
- PS: The reason for the return type prompt judgment logic is to reduce the number of judgments. When there is an IDE to write code, the return response will be the same as the return type prompt 
```python
import time

import aioredis
from fastapi import FastAPI
from starlette.responses import JSONResponse

from fast_tools.base import RedisHelper
from fast_tools.cache import (
    cache,
    cache_control
)


app = FastAPI()
redis_helper: 'RedisHelper' = RedisHelper()


@app.on_event("startup")
async def startup():
    redis_helper.init(await aioredis.create_pool('redis://localhost', minsize=1, maxsize=10, encoding='utf-8'))


@app.on_event("shutdown")
async def shutdown():
    if not redis_helper.closed:
        await redis_helper.close()


@app.get("/")
@cache(redis_helper, 60)
async def root() -> dict:
    """Read the dict data and send the corresponding response data according to the response (the default is JSONResponse)"""
    return {"timestamp": time.time()}


# adter_cache_response_listSupport the incoming function and execute it before returning the cached response. For details, see the usage method of the example
# cache_control Will add the cache time to the http header when returning the cached response
@app.get("/api/users/login")
@cache(redis_helper, 60, after_cache_response_list=[cache_control]) 
async def user_login() -> JSONResponse:
    """The response type cache does not cache the entire instance, but caches the main data in the instance, and re-splices it into a new respnose the next time it returns to the cache."""
    return JSONResponse({"timestamp": time.time()})


@app.get("api/null")
@cache(redis_helper, 60)
async def test_not_return_annotation():
    """Functions without return annotation will not be cached"""
    return JSONResponse({"timestamp": time.time()})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
## 8.limit
- explanation: Use common current-limiting algorithms to limit the flow of requests, and support different user groups with different flow-limiting rules. Support decorators as a single function or use middleware to limit the flow of requests that meet the URL rules. Backend supports memory-based Token bucket and redis-based token bucket, cell module, and window limit 
- applicable framework: `FastApi`,`Starlette`
```python
from typing import Optional, Tuple

import aioredis
from fastapi import FastAPI, Request
from fast_tools.base import RedisHelper
from fast_tools import limit


def limit_func(requests: Request) -> Tuple[str, str]:
    """limit needs to determine the current request key and group according to the function"""
    return requests.session['user'], requests.session['group']


app = FastAPI()
redis_helper: 'RedisHelper' = RedisHelper()


@app.on_event("startup")
async def startup():
    redis_helper.init(await aioredis.create_pool('redis://localhost', minsize=1, maxsize=10, encoding='utf-8'))

# For requests starting with /api, the admin group can request 10 times per second, while the user group can only request once per second 
app.add_middleware(
    limit.LimitMiddleware,
    func=limit_func,
    rule_dict={
        r"^/api": [limit.Rule(second=1, gen_token_num=10, group='admin'), limit.Rule(second=1, group='user')]
    }
)


# Each ip can only be requested once every 10 seconds 
@app.get("/")
@limit.limit(
    [limit.Rule(second=10, gen_token_num=1)],
    limit.backend.RedisFixedWindowBackend(redis_helper),
    limit_func=limit.func.client_ip
)
async def root():
    return {"Hello": "World"}


@app.get("/api/users/{user_id}/items/{item_id}")
async def read_user_item(
    user_id: int, item_id: str, q: Optional[str] = None, short: bool = False
):
    """
    copy from:https://fastapi.tiangolo.com/tutorial/query-params/#multiple-path-and-query-parameters
    """
    item = {"item_id": item_id, "owner_id": user_id}
    if q:
        item.update({"q": q})
    if not short:
        item.update(
            {"description": "This is an amazing item that has a long description"}
        )
    return item


@app.get("/api/users/login")
async def user_login():
    return 'ok'


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
## 9.share
- explanation: share is used to share the same time-consuming result in multiple coroutines in the same thread, see [example](https://github.com/so1n/fast-tools/blob/master/example/share.py) 
- applicable framework: `FastApi`,`Starlette`
