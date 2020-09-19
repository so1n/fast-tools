# fastapi-tools
一个fastapi的工具集,可以更方便的使用fastapi
# Usage
## 1.exporter
一个可用于 `Starlette` 和 `FastAPI`的prometheus exporter,可以监控各个url的状态`.

### 1.1 安装
pip install prometheus_client
### 1.2 使用
```python
from typing import Optional

from fastapi import FastAPI
from fastapi_tools.exporter import PrometheusMiddleware, get_metrics
from fastapi_tools.route_trie import RouteTrie


app = FastAPI()
route_trie = RouteTrie()

app.add_middleware(
    PrometheusMiddleware,
    route_trie=route_trie,      # 使用路由树, 对每个路由的查询速度会变快
    block_url_set={"/metrics"}  # 设置不监控的url: /metrics
)

app.add_route("/metrics", get_metrics)  # 添加metrics的相关url,方便prometheus获取数据
```
### 1.3 example
更多代码请看[example](https://github.com/so1n/fastapi-tools/blob/master/example/exporter.py)
## 2.cbv
由于fastapi的改动,目前尚未支持cbv模式,只有一个[工具](https://github.com/dmontagu/fastapi-utils/blob/master/fastapi_utils/cbv.py) 
提供了cbv的支持,而我的cbv复用了它的核心代码,并做出了一些修改,使他的使用更加方便,可以像`Starlette`使用cbv,同时提供`cbv_decorator`来支持fastapi的其他功能.
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
    # 不用担心父属性的问题,每次调用到get或者post的方法时,实际上是创建一个新的对象并通过self传进去,不同的请求并不会共享同一个对象
    host: str = Header('host')
    user_agent: str = Depends(get_user_agent)

    def __init__(self, test_default_id: int = Query(123)):
        """也可以通过init的方法引入, 但是这里也要赋值,不然没办法通过self调用"""
        self.test_default_id = test_default_id

    def _response(self):
        return {"message": "hello, world", "user_agent": self.user_agent, "host": self.host, "id": self.test_default_id}

    @cbv_decorator(status_code=203)   # 这里只支持add_api_route的关键参数
    def get(self):
        return self._response()

    def post(self):
        return self._response()


app.include_router(Cbv(TestCbv).router)  # 目前觉得最容易的调用方法了...

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
## 3.config
config提供一个从文件转换为python对象的配置. 基于`Pydantic`和Type Hints, config可以在不需要使用大量的代码量下实现快速转换或检验参数.
```python
from typing import List, Optional
from fastapi_tools.config import Config

from pydantic.fields import Json


class MyConfig(Config):
    DEBUG: bool
    HOST: str
    PORT: int

    REDIS_ADDRESS: str
    REDIS_PASS: Optional[str] = None  # 设置默认值,如果配置文件没有该值且不设置默认值,则会报错

    MYSQL_DB_HOST: str
    MYSQL_DB_NAME: str
    MYSQL_DB_PASS: str
    MYSQL_DB_USER: str
    ES_HOST: Json[List]
    TEST_LIST_INT: Json[List]
    YML_ES_HOST: Optional[List[str]] = None
    YML_TEST_LIST_INT: Optional[List[int]] = None

```
config支持如下参数:
    - config_file: 配置文件,支持ini和yml文件,如果没填写则从环境变量中拉取数据(不过只拉取了一个全局字典)
    - group: group可以指定一个配置分组.在使用ini和yml文件时,支持多个分组配置,如dev配置和test配置.如果你不想在代码中配置该选项,可以直接在环境变量中配置group=test
    - global_key: 指定那个分组为全局配置.在使用ini和yml文件时, 支持多个分组配置,同时也有一个全局配置, 该配置可以被多个分组共享(如果该分组没有对应的配置,则会引用到global_key的配置,如果有则不引用)

## 4.context
利用`contextvars`的特性,可以在路由中方便的调用自己需要的东西,而不需要像requests.app.state去调用,同时还可以支持type hints,方便写代码.
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
    # ContextBaseModel 用于保存数据到contextvars
    # HeaderQuery  用于提取header的数据,并存入ContextBaseModel中
    # CustomQuery  用于把实例存入ContextBaseModel中
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


# ContextMiddleware用于在请求前存储数据到ContextBaseModel,并在响应数据前reset contextvars的数据
app.add_middleware(ContextMiddleware, context_model=ContextModel())


@app.get("/")
async def root():
    assert ContextModel.http_client == client     # 验证是不是同一个实例
    return {
        "message": ContextModel.to_dict(is_safe_return=True)  # is_safe_return 为true时,不会返回实例相关的数据
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
## 5.route_trie
python的web框架为了支持`/api/user/{user_id}`的写法都是先遍历路由,并逐一检查是否符合正则规则,符合条件才返回路由.
不过我们的在web项目中url数量不多,平时很难发现这个路由匹配会降低响应速度.
但在实现一些需要得知url的中间件时,还需要再匹配一次,那效率就很慢了.
如果改为dict在进行路由匹配,虽然速度很快,但是却不支持上述所说的url,所以以前缀树重构了路由查找,可以尽快的匹配到路由的大致区域,再进行正则匹配,检查路由是否正确.
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
route_trie.insert_by_app(app)  # 读取app中的url加载到路由树里面


def print_route(route_list):
    if route_list:
        for route in route_list:
            print(f'route:{route} url:{route.path}')
    else:
        print(f'route:{route_list} url: not found')


# regex url should use scope param, can learn more in exporter example
# 普通的search类似于从dict中调用get 
# 在中间件中可以调用route_trie.search_by_scope
print_route(route_trie.search('/'))
print_route(route_trie.search('/api/users/login'))
```
## 6.statsd_middleware
使用方法类似于exporter, 不过多了个`url_replace_handle`来处理url
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
理想中的架构是不需要使用到`task`的,所以不推荐使用`task`,但在架构演进中可能会用到
```python
import time
from fastapi import FastAPI
from fastapi_tools.task import background_task
from fastapi_tools.task import stop_task

app = FastAPI()

# 启动前调用
@app.on_event("startup")
# 每10秒执行一次
@background_task(seconds=10)
def test_task() -> None:
    print(f'test.....{int(time.time())}')

# 停止调用
app.on_event("shutdown")(stop_task)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```