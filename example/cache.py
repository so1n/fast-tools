import time
from typing import Optional

import aioredis
from fastapi import FastAPI
from starlette.responses import JSONResponse

from fastapi_tools.base import RedisHelper
from fastapi_tools.cache import (
    cache,
    cache_control
)


app = FastAPI()
redis_helper: 'RedisHelper' = RedisHelper()


@app.on_event("startup")
async def startup():
    redis_helper.reload(await aioredis.create_pool('redis://localhost', minsize=1, maxsize=10, encoding='utf-8'))


@app.on_event("shutdown")
async def shutdown():
    if not redis_helper.closed:
        await redis_helper.close()


@app.get("/")
@cache(redis_helper, 60)
async def root() -> dict:
    return {"timestamp": time.time()}


@app.get("/api/users/login")
@cache(redis_helper, 60, after_cache_response_list=[cache_control])
async def user_login() -> JSONResponse:
    return JSONResponse({"timestamp": time.time()})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
