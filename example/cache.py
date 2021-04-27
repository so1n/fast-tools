import time

import aioredis  # type: ignore
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse

from fast_tools.base import RedisHelper
from fast_tools.cache import cache, cache_control

app: "FastAPI" = FastAPI()
redis_helper: "RedisHelper" = RedisHelper()


async def get_key(request: Request) -> str:
    return request.query_params.get("uid")


@app.on_event("startup")
async def startup() -> None:
    redis_helper.init(await aioredis.create_pool("redis://localhost", minsize=1, maxsize=10, encoding="utf-8"))


@app.on_event("shutdown")
async def shutdown() -> None:
    if not redis_helper.closed:
        await redis_helper.close()


@app.get("/")
@cache(redis_helper, 60, after_cache_response_list=[cache_control])
async def root() -> dict:
    return {"timestamp": time.time()}


@app.get("/api/users/login")
@cache(redis_helper, 60, after_cache_response_list=[cache_control], get_key_func=get_key)
async def user_login(request: Request) -> JSONResponse:
    return JSONResponse({"timestamp": time.time()})


@app.get("/api/get_key_error")
@cache(redis_helper, 60, after_cache_response_list=[cache_control], get_key_func=get_key)
async def get_key_error() -> JSONResponse:
    return JSONResponse({"timestamp": time.time()})


@app.get("/api/null")
@cache(redis_helper, 60)
async def test_not_return_annotation():  # type: ignore
    return JSONResponse({"timestamp": time.time()})


if __name__ == "__main__":
    import uvicorn  # type: ignore

    uvicorn.run(app)
