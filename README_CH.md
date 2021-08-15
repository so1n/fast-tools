# fast-tools
`fast-tools`是一个`FastApi/Starlette`的库合集, 大部分库都可用于FastApi/Starlette, 少部库只支持`FastApi`是为了兼容`FastApi`的不足

```python
# 名字由来
project_name = ('FastApi'[:2] + 'Starlette'[:2]).lower() + '-tools'
print(project_name)  # 'fast-tools'
```
# Usage
## 0.base
- 说明:`fast-tools`的一些工具的依赖,也可单独使用
- 适用框架:`FastApi`,`Starlette`, more....
### 0.1.redis_helper
- 说明: 用于对aioredis的conn pool封装,以及对一些常用命令进行封装.
```python
import aioredis
from fastapi import FastAPI

from fast_tools.base import RedisHelper

app: 'FastApi' = FastAPI()
redis_helper: 'RedisHelper' = RedisHelper()  # 初始化对象


@app.on_event("startup")
async def startup():
    # 创建redis连接池并链接
    redis_helper.init(await aioredis.create_pool('redis://localhost', minsize=1, maxsize=10, encoding='utf-8'))

app.on_event("shutdown")
async def shutdown():
    # 关闭redis连接池
    await redis_helper.close()


@app.get("/")
async def root() -> dict:
    info = await redis_helper.client.info()
    return {"info": info}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
### 0.2.route_trie
通过RouteTrie可以快速的查找路由,同时内置了Contextvars,同一个请求中只查找一次, 极大的优化了查询速度.
python的大多数web框架的路由查找都是遍历整个路由表,如果当前url与路由的注册url正则匹配则查找成功.不过Web框架查找路由都是用遍历路由表的方法,
猜测之所以用遍历路由表的方法,一个是为了实现简单,还有就是为了支持`/api/user/{user_id}`的写法.
可以发现通过遍历路由表来查找路由的时间复杂度是O(n), 当路由数量达到一定的程度后,匹配时间就变慢了, 特别是在使用中间件且需要查找路由时, 还会再查找一次,效率就会变得很低, 所以需要优化,
然而最快路由匹配速度是dict,但是无法支持类似于`/api/user/{user_id}`的写法,只能另寻他路,好在url天生跟前缀树匹配,所以使用前缀树重构了路由查找,可以尽快的匹配到路由的大致区域,再进行正则匹配,检查路由是否正确.
```Python
from typing import List, Optional

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


route_trie: RouteTrie = RouteTrie()  # 初始化路由树数据结构
route_trie.insert_by_app(app)  # 读取app的路由


def print_route(route_list: Optional[List[Route]]):
    """打印路由"""
    if route_list:
        for route in route_list:
            print(f'route:{route} url:{route.path}')
    else:
        print(f'route:{route_list} url: not found')

# 匹配app路由需要用到scope param, 可以从exporter的例子了解更多
print_route(route_trie.search('/'))
print_route(route_trie.search('/api/users/login'))
```
[简单的对比自带的路由匹配与前缀树匹配效率差](https://github.com/so1n/fast-tools/blob/master/example/route_trie_simple_benchmarks.py)
## 1.exporter
- 说明: 一个可用于 `Starlette` 和 `FastAPI`的prometheus exporter中间件,可以监控各个url的状态`, 如连接次数,响应次数,请求时间,错误次数,当前请求数.
- 适用框架: `FastApi`,`Starlette`
### 1.1 安装
`pip install prometheus_client` or `pip install fast_tools[prometheus]` or `poetry install -E prometheus`
### 1.2 使用
```python
from fastapi import FastAPI

from fast_tools.base.route_trie import RouteTrie
from fast_tools.exporter import PrometheusMiddleware, get_metrics

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
更多代码请看[example](https://github.com/so1n/fast-tools/blob/master/example/exporter.py)
## 2.cbv
- 说明:由于fastapi的改动,目前尚未支持cbv模式,只有[fastapi_utils](https://github.com/dmontagu/fastapi-utils/blob/master/fastapi_utils/cbv.py)
提供了cbv的支持, 但觉得使用起来不是很方便,所以复用了它的核心代码,并做出了一些修改,可以像`Starlette`使用cbv,同时提供`cbv_decorator`来支持fastapi的其他功能.
- 适用框架: `FastApi`
```python
from fastapi import Depends, FastAPI, Header, Query

from fast_tools.cbv import Cbv, cbv_decorator

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
        """get请求调用的方法"""
        return self._response()

    def post(self):
        """post请求调用的方法"""
        return self._response()


app.include_router(Cbv(TestCbv, url='/').router)  # 目前觉得最容易的调用方法了...

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
## 3.config

### 3.1 安装
`pip install pydantic` or `pip install fast_tools[pydantic]` or `poetry install -E pydantic`
### 3.2 使用
- 说明:config提供一个把配置文件转换为python对象的功能. 由于config基于`Pydantic`和Type Hints, config可以在不需要使用大量的代码量下实现快速转换或检验参数.
- 适用框架: `FastApi`,`Starlette`
config支持如下参数:
- config_file: 配置文件,支持ini和yml文件,如果没填写则从环境变量中拉取数据, 具体可以见[example](https://github.com/so1n/fast-tools/tree/master/example/config)
- group: group可以指定一个配置分组.在使用ini和yml文件时,支持多个分组配置,如dev配置和test配置.如果参数为空,则会从环境变量中拉取值(如配置了group=test)
- global_key: 指定哪个分组为全局配置(默认key为group).在使用ini和yml文件时, 支持多个分组配置,同时也有一个全局配置, 该配置可以被多个分组共享(如果该分组没有对应的配置,则会引用到global_key的配置,如果有则不引用)
```python
from typing import List, Optional

from pydantic.fields import Json

from fast_tools.config import Config


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

MyConfig('./example.yml', group='dev')  # 读取当前目录的example.yaml文件,并读取dev的值
```
具体使用方法见[example](https://github.com/so1n/fastapi-tools/blob/master/example/config/__init__.py)
## 4.context
- 说明:context利用`contextvars`的特性,调用者可以像flask一样在路由中方便的调用自己需要的东西,而不需要像requests.app.state去调用.
而且利用`contextvars`还可以支持type hints,方便重构和编写工程化代码,不过直接使用`contextvars`会写很多代码,并且十分麻烦.通过context把`contextvars`的使用方法封装起来,调用者只需要引入context.ContextMiddleware和context.ContextBaseModel即可,快速的在框架中使用contextvars.
**备注: 继承ContextBaseModel的类在使用时可以不实例化,但防止覆盖父属性的值,最好是先实例化再使用**

- 适用框架: `FastApi`,`Starlette`

```python
import asyncio
import uuid
from contextvars import Context, copy_context
from functools import partial

import httpx
from fastapi import FastAPI, Request, Response

from fast_tools.context import ContextBaseModel, ContextMiddleware, CustomHelper, HeaderHelper

app: FastAPI = FastAPI()


class ContextModel(ContextBaseModel):
    """对contextvars的封装,需要继承ContextBaseModel,并添加到中间件中"""

    # HeaderHelper是一个获取header数据并放置到context中,如果获取不到对应的数据,则会从default_func的返回值获取
    request_id: str = HeaderHelper(
        'X-Request-Id',
        default_func=lambda request: str(uuid.uuid4())
    )
    ip: str = HeaderHelper(
        'X-Real-IP',
        default_func=lambda request: request.client.host
    )
    user_agent: str = HeaderHelper('User-Agent')

    # CustomHelper是对Context调用的封装,需要自己设置一个key, 在当前上下文中可以读取数据(如果要设置数据,需要先实例化)
    http_client: httpx.AsyncClient = CustomHelper('http_client')

    async def before_request(self, request: Request):
        """执行请求之前会调用的方法"""
        self.http_client = httpx.AsyncClient()

    async def after_response(self, request: Request, response: Response):
        """执行响应成功之后会调用的方法"""
        pass

    async def before_reset_context(self, request: Request, response: Response):
        """上下文被销毁前之前会调用的方法"""
        await self.http_client.aclose()


#　需要依赖中间件来维护上下文变量,如果其他中间件需要调用到上下文,则需要把该中间件前置
context_model: ContextModel = ContextModel()
app.add_middleware(ContextMiddleware, context_model=context_model)


async def test_ensure_future():
    print(f'test_ensure_future {context_model.http_client}')


def test_run_in_executor():
    print(f'test_run_in_executor {context_model.http_client}')


def test_call_soon():
    print(f'test_call_soon {context_model.http_client}')


@app.get("/")
async def root():
    # python会自动copy 上下文
    asyncio.ensure_future(test_ensure_future())
    loop: 'asyncio.get_event_loop()' = asyncio.get_event_loop()

    # python会自动copy 上下文
    loop.call_soon(test_call_soon)

    # 另开线程处理时,需要自己copy上下文
    ctx: Context = copy_context()
    await loop.run_in_executor(None, partial(ctx.run, test_run_in_executor))

    return {
        "message": context_model.to_dict(is_safe_return=True),  # 只返回可以被转换为json的数据
        "local_ip": (await context_model.http_client.get('http://icanhazip.com')).text
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
## 5.statsd_middleware
- 说明:用于把监控数据发送到`StatsD`的中间件,使用方法类似于exporter, 不过多了个`url_replace_handle`来处理url中一些不符合metric的符号
- 适用框架: `FastApi`,`Starlette`
### 5.1安装
`pip install aio_statsd` or `pip install fast_tools[statsd]` or `poetry install -E statsd`
### 5.2使用
```python
from typing import Optional

from fastapi import FastAPI

from fast_tools.base.route_trie import RouteTrie
from fast_tools.statsd_middleware import StatsdClient, StatsdMiddleware

app = FastAPI()
client = StatsdClient()
route_trie = RouteTrie()

app.add_middleware(
    StatsdMiddleware,
    client=client,
    route_trie=route_trie,
    url_replace_handle=lambda url: url.replace('/', '_'),  # metric命名不支持'/'符号
    block_url_set={"/"}
)
app.on_event("shutdown")(client.close)


@app.on_event("startup")
async def startup_event():
    await client.connect()  # 需要先连接
    route_trie.insert_by_app(app)


@app.get("/")
async def root():
    return {"Hello": "World"}


@app.get("/api/users/{user_id}/items/{item_id}")
async def read_user_item(user_id: int, item_id: str, q: Optional[str] = None, short: bool = False):
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
- 说明:理想中的架构是不需要使用到`task`的,所以不推荐使用`task`,但在架构初期中可能会用到...
- 适用框架: `FastApi`,`Starlette`
```python
import time

from fastapi import FastAPI

from fast_tools.task import background_task, stop_task

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
## 7.cache
- 说明: 利用函数的return type hint, 自适应的缓存对应的响应,并在下次请求且缓存时间未过期时,返回缓存数据.
- 适用框架: `FastApi`,`Starlette`
- PS: 之所以使用return type hint判断,而不是根据数据进行判断,是可以减少判断次数,有IDE编写代码时,返回响应会跟return type hint一样
```python
import time

import aioredis
from fastapi import FastAPI
from starlette.responses import JSONResponse

from fast_tools.base import RedisHelper
from fast_tools.cache import cache, cache_control

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
    """读取dict数据,并按照respnose发送对应的响应数据(默认为JSONResponse)"""
    return {"timestamp": time.time()}


# adter_cache_response_list支持传入函数,并在返回缓存响应前执行他
# cache_control会在返回缓存响应时,在http头添加缓存时间
@app.get("/api/users/login")
@cache(redis_helper, 60, after_cache_response_list=[cache_control])
async def user_login() -> JSONResponse:
    """response类型的缓存并不会缓存整个实例,而是缓存实例里的主要数据,并再下次返回缓存时重新拼接成新的respnose"""
    return JSONResponse({"timestamp": time.time()})


@app.get("api/null")
@cache(redis_helper, 60)
async def test_not_return_annotation():
    """没有标注return annotation的函数不给予缓存"""
    return JSONResponse({"timestamp": time.time()})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
```
## 8.limit
- 说明: 利用常见的限流算法对请求进行限流,并支持每个分组都能拥有自己的不同的限流规则(默认规则组为None,全部url都会被限流).支持装饰器为单一函数或者使用中间件对符合url规则的请求进行限流.backend支持基于内存的令牌桶以及基于redis的令牌桶,cell模块,和窗口限流
- 适用框架: `FastApi`,`Starlette`
- API说明:
    - Rule:
        - Rule会根据时间参数获取周期时长(单位:s), 时间相关的参数有:second, minute, hour, day, week,如second=1, minute=1时,秒数为61
        - max_token_num: 最大的token数,当使用令牌桶时,最大的令牌数量为max_token_num
        - gen_token_num: 每个周期生成的令牌数量
        - init_token_num: 初始化时的token数量, 不能大于max_token_num
        - group: 当前规则应用的组,如果不配置则默认为None组
        - block_time: 当出现不可请求时, 会有block_time秒内无法访问(即使当前有令牌存在)
    - limit(装饰器函数):
        - rule_list: 存放`Rule`规则的列表
        - backend: 可选的限流模式,自带基于内存的令牌桶,基于redis的滑动窗口,令牌桶和redis-cell
        - limit_func: 该函数用于告诉当前请求的key和group为什么,如果组不确定应该返回`None`
        - status_code: 返回被限流响应的状态码
        - content: 返回被限流响应的内容
        - enable_match_fail_pass: 如果为True时, 即使匹配失败,也会允许访问
    - LimitMiddleware:
        - app: 略
        - rule_list: 存放`Rule`规则的列表, `['*', [rule, rule]]`, 中间件的规则列表稍微有点不同,第一个指为url的正则匹配表达式,第二个值是`Rule`规则数组
        - backend: 可选的限流模式,自带基于内存的令牌桶,基于redis的滑动窗口,令牌桶和redis-cell
        - limit_func: 该函数用于告诉当前请求的key和group为什么,如果组不确定应该返回`None`
        - status_code: 返回被限流响应的状态码
        - content: 返回被限流响应的内容
        - enable_match_fail_pass: 如果为True时, 即使匹配失败,也会允许访问
```python
from typing import Optional, Tuple

import aioredis
from fastapi import FastAPI, Request

from fast_tools import limit
from fast_tools.base import RedisHelper


def limit_func(requests: Request) -> Tuple[str, str]:
    """limit需要根据函数来判断当前的请求key和所在的组"""
    return requests.session['user'], requests.session['group']


app = FastAPI()
redis_helper: 'RedisHelper' = RedisHelper()


@app.on_event("startup")
async def startup():
    redis_helper.init(await aioredis.create_pool('redis://localhost', minsize=1, maxsize=10, encoding='utf-8'))

# 以/api开头的请求, admin组每秒可以请求10次,而user组每秒只可以请求一次
app.add_middleware(
    limit.LimitMiddleware,
    func=limit_func,
    rule_list=[
        # 匹配到url后,会根据不同的group执行不同的限制频率
        (r"^/api", [limit.Rule(second=1, gen_token_num=10, group='admin'), limit.Rule(second=1, group='user')])
    ]
)


# 每个ip每10秒只可以请求1次
@app.get("/")
@limit.limit(
    [limit.Rule(second=10, gen_token_num=1)],
    limit.backend.RedisFixedWindowBackend(redis_helper),
    limit_func=limit.func.client_ip
)
async def root():
    return {"Hello": "World"}


@app.get("/api/users/{user_id}/items/{item_id}")
async def read_user_item(user_id: int, item_id: str, q: Optional[str] = None, short: bool = False):
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
- 说明: share用于在同个线程的多个协程中分享同个耗时结果,具体见[example](https://github.com/so1n/fast-tools/blob/master/example/share.py)
- 适用框架: `FastApi`,`Starlette`
