# fastapi-tools
A collection of tools available for FastApi. Easy to use FastApi(part can be used for starlette)
[中文](https://github.com/so1n/fastapi-tools/blob/master/README_CH.md)

# Usage
## 1.exporter
Prometheus exporter for `Starlette` and `FastAPI`.

### 1.1 install
pip install prometheus_client
### 1.2 Usage
```python
from typing import Optional

from fastapi import FastAPI
from fastapi_tools.exporter import PrometheusMiddleware, get_metrics
from fastapi_tools.route_trie import RouteTrie


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
Due to fastapi changes, cbv is not currently supported, only one[tool](https://github.com/dmontagu/fastapi-utils/blob/master/fastapi_utils/cbv.py) provides cbv support.
My cbv reuses its core code and make some change.can use cbv like `Starlette` and `cbv_decorator` can support fastapi feat.
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'so1n'
__date__ = '2020-08'
from fastapi import FastAPI, Depends, Header, Query
from fastapi_tools.cbv import cbv_decorator, Cbv

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

## 4.context
Using the characteristics of `contextvars`, you can conveniently call what you need in the route, without the need to call like requests.app.state, and it can also support type hints to facilitate writing code.
```python
__author__ = 'so1n'
__date__ = '2020-06'
import uuid
import httpx
from fastapi import FastAPI
from fastapi_tools.context import ContextBaseModel
from fastapi_tools.context import ContextMiddleware
from fastapi_tools.context import CustomQuery
from fastapi_tools.context import HeaderQuery

app = FastAPI()
client = httpx.AsyncClient()


class ContextModel(ContextBaseModel):
    # ContextBaseModel  save data to contextvars
    # HeaderQuery  extract data from header and set to ContextBaseModel
    # CustomQuery  Used to store the instance in ContextBaseModel
    request_id: str = HeaderQuery(
        'X-Request-Id',
        default_func=lambda request: str(uuid.uuid4())
    )
    ip: str = HeaderQuery(
        'X-Real-IP',
        default_func=lambda request: request.client.host
    )
    user_agent: str = HeaderQuery('User-Agent')
    http_client: httpx.AsyncClient = CustomQuery(client)


# ContextMiddleware is used to store data to ContextBaseModel before requesting, and to reset contextvars data before responding to data 
app.add_middleware(ContextMiddleware, context_model=ContextModel())


@app.get("/")
async def root():
    assert ContextModel.http_client == client     # Verify that the same instance
    return {
        "message": ContextModel.to_dict(is_safe_return=True)  # is_safe_return 为true时,不会返回实例相关的数据
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
## 5.route_trie
Python's web framework uses traversal matching to implement route lookup. If you match again when implementing middleware, the efficiency will be very slow.
The prefix tree reconstructs the route search, which can quickly find the route in the middleware and improve the query speed
```Python
from fastapi import FastAPI
from fastapi_tools.route_trie import RouteTrie

app = FastAPI()


@app.get("/")
async def root():
    return {"Hello": "World"}


@app.get("/api/users/login")
async def user_login():
    return 'ok'


route_trie: RouteTrie = RouteTrie()
route_trie.insert_by_app(app)  # Extract the url in the app and load it into the routing tree 


def print_route(route_list):
    if route_list:
        for route in route_list:
            print(f'route:{route} url:{route.path}')
    else:
        print(f'route:{route_list} url: not found')


# regex url should use scope param, can learn more in exporter example
# The search method is similar to calling get from a dict
# can call route_trie.search_by_scope in the middleware 
print_route(route_trie.search('/'))
print_route(route_trie.search('/api/users/login'))
```
## 6.statsd_middleware
The method of use is similar to exporter, but there is an additional `url_replace_handle` to handle url
### 6.1安装
pip install aiostatsd
```python
from typing import Optional

from fastapi import FastAPI
from fastapi_tools.statsd_middleware import StatsdClient, StatsdMiddleware
from fastapi_tools.route_trie import RouteTrie


app = FastAPI()
client = StatsdClient()
route_trie = RouteTrie()

app.add_middleware(
    StatsdMiddleware,
    client=client,
    route_trie=route_trie,
    url_replace_handle=lambda url: url.replace('/', '_'),
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
## 7.task
The ideal architecture does not need to use `task`, so `task` is not recommended, but it may be used in the evolution of the architecture
```python
import time
from fastapi import FastAPI
from fastapi_tools.task import background_task
from fastapi_tools.task import stop_task

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