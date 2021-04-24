from typing import Optional, Tuple

import aioredis  # type: ignore
from fastapi import FastAPI, Request

from fast_tools import limit
from fast_tools.base import RedisHelper


def limit_by_user(requests: Request) -> Tuple[str, str]:
    return requests.query_params.get("uid"), requests.query_params.get("group")


def limit_path_and_ip(request: Request) -> Tuple[str, Optional[str]]:
    if "X-Real-IP" in request.headers:
        ip: str = request.headers["X-Real-IP"]
    else:
        ip = request.client.host
    return ip + request.url.path, None


def limit_by_group(request: Request) -> Tuple[str, Optional[str]]:
    if "X-Real-IP" in request.headers:
        ip: str = request.headers["X-Real-IP"]
    else:
        ip = request.client.host
    return ip, request.query_params.get("user")


app: "FastAPI" = FastAPI()
redis_helper: "RedisHelper" = RedisHelper()


@app.on_event("startup")
async def startup() -> None:
    redis_helper.init(await aioredis.create_pool("redis://localhost", minsize=1, maxsize=10, encoding="utf-8"))


app.add_middleware(
    limit.LimitMiddleware,
    limit_func=limit_by_user,
    rule_list=[
        (r"^/api/user", [
            limit.Rule(second=10, gen_token_num=1, init_token_num=1, group="user"),
            limit.Rule(second=10, gen_token_num=1, init_token_num=2, group="admin")]
         )
    ],
)


@app.get("/")
@limit.limit(
    [limit.Rule(second=1, gen_token_num=1, init_token_num=1, block_time=1)],
    limit.backend.RedisFixedWindowBackend(redis_helper),
    limit_func=limit_path_and_ip,
)
async def root(request: Request) -> dict:
    return {"Hello": "World"}


@app.get("/redis/token_bucket")
@limit.limit(
    [limit.Rule(second=1, gen_token_num=1, init_token_num=1, block_time=1)],
    limit.backend.RedisTokenBucketBackend(redis_helper),
    limit_func=limit_path_and_ip,
)
async def redis_token_bucket(request: Request) -> dict:
    return {"Hello": "World"}


@app.get("/redis/cell")
@limit.limit(
    [limit.Rule(second=1, gen_token_num=1, init_token_num=1, block_time=1, max_token_num=1)],
    limit.backend.RedisCellBackend(redis_helper),
    limit_func=limit_path_and_ip,
)
async def redis_cell(request: Request) -> dict:
    return {"Hello": "World"}


@app.get("/memory/token_bucket")
@limit.limit(
    [limit.Rule(second=1, gen_token_num=1, init_token_num=1, block_time=1)],
    limit.backend.TokenBucket(),
    limit_func=limit_path_and_ip,
)
async def memory_token_bucket(request: Request) -> dict:
    return {"Hello": "World"}


@app.get("/memory/thread_token_bucket")
@limit.limit(
    [limit.Rule(second=1, gen_token_num=1, init_token_num=1, block_time=1)],
    limit.backend.ThreadingTokenBucket(),
    limit_func=limit_path_and_ip,
)
async def memory_thread_token_bucket(request: Request) -> dict:
    return {"Hello": "World"}


@app.get("/decorator")
@limit.limit(
    [
        limit.Rule(second=1, gen_token_num=1, init_token_num=1, block_time=1, group="user1"),
        limit.Rule(second=1, gen_token_num=1, init_token_num=2, block_time=1, group="user2"),
    ],
    limit.backend.ThreadingTokenBucket(),
    limit_func=limit_by_group,
)
async def decorator(request: Request) -> dict:
    return {"Hello": "World"}


@app.get("/api/user/login")
async def user_login() -> dict:
    return {"Hello": "World"}


@app.get("/api/user/logout")
async def user_logout() -> dict:
    return {"Hello": "World"}


if __name__ == "__main__":
    import uvicorn  # type: ignore

    uvicorn.run(app)
