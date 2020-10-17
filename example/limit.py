from typing import (
    Optional,
    Tuple
)

import aioredis
from fastapi import (
    FastAPI,
    Request
)
from fastapi_tools.base import RedisHelper
from fastapi_tools import limit


def limit_func(requests: Request) -> Tuple[str, str]:
    return requests.session['user'], requests.session['group']


app: 'FastAPI' = FastAPI()
redis_helper: 'RedisHelper' = RedisHelper()


@app.on_event("startup")
async def startup():
    redis_helper.init(await aioredis.create_pool('redis://localhost', minsize=1, maxsize=10, encoding='utf-8'))

app.add_middleware(
    limit.LimitMiddleware,
    func=limit_func,
    rule_dict={
        r"^/api": [limit.Rule(second=10, group='admin'), limit.Rule(second=10, group='user')]
    }
)


@app.get("/")
@limit.limit(
    [limit.Rule(second=10, gen_token_num=1)],
    limit.backend.RedisFixedWindowBackend(redis_helper),
    limit_func=limit.func.client_ip
)
async def root() -> dict:
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
async def user_login() -> str:
    return 'ok'


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
