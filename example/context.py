#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test fast_tools.context in fastapi
> curl 127.0.0.01:8000
{"message":{"request_id":"3a2f245b-4703-40f1-94bb-36d2eac4d7a6","ip":"127.0.0.1","user_agent":"curl/7.64.0"},"local_ip":"***.***.95.210\n"}%
"""
__author__ = 'so1n'
__date__ = '2020-06'
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


app: FastAPI = FastAPI()


class ContextModel(ContextBaseModel):
    request_id: str = HeaderHelper(
        'X-Request-Id',
        default_func=lambda request: str(uuid.uuid4())
    )
    ip: str = HeaderHelper(
        'X-Real-IP',
        default_func=lambda request: request.client.host
    )
    user_agent: str = HeaderHelper('User-Agent')
    http_client: httpx.AsyncClient = CustomHelper('http_client')

    async def before_request(self, request: Request):
        self.http_client = httpx.AsyncClient()

    async def before_reset_context(self, request: Request, response: Response):
        await self.http_client.aclose()


app.add_middleware(ContextMiddleware, context_model=ContextModel())


async def test_ensure_future():
    print(f'test_ensure_future {ContextModel.http_client}')


def test_run_in_executor():
    print(f'test_run_in_executor {ContextModel.http_client}')


def test_call_soon():
    print(f'test_call_soon {ContextModel.http_client}')


@app.get("/")
async def root():
    asyncio.ensure_future(test_ensure_future())
    loop: 'asyncio.get_event_loop()' = asyncio.get_event_loop()

    loop.call_soon(test_call_soon)
    ctx: Context = copy_context()
    await loop.run_in_executor(None, partial(ctx.run, test_run_in_executor))
    return {
        "message": ContextModel.to_dict(is_safe_return=True),  # not return CustomQuery
        "local_ip": (await ContextModel.http_client.get('http://icanhazip.com')).text
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
