#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test fast_tools.context in fastapi
> curl 127.0.0.01:8000
{"message":{"request_id":"3a2f245b-4703-40f1-94bb-36d2eac4d7a6","ip":"127.0.0.1","user_agent":"curl/7.64.0"},"local_ip":"***.***.95.210\n"}%
"""
__author__ = "so1n"
__date__ = "2020-06"
import asyncio
import uuid
from contextvars import Context, copy_context
from functools import partial
from typing import Set, Optional

import httpx
from fastapi import FastAPI, Request, Response

from fast_tools.context import ContextBaseModel, ContextMiddleware, HeaderHelper

app: FastAPI = FastAPI()
check_set: Set[int] = set()


class ContextModel(ContextBaseModel):
    http_client: httpx.AsyncClient
    request_id: str = HeaderHelper.i("X-Request-Id", default_func=lambda request: str(uuid.uuid4()))
    ip: str = HeaderHelper.i("X-Real-IP", default_func=lambda request: request.client.host)
    user_agent: str = HeaderHelper.i("User-Agent")

    async def before_request(self, request: Request) -> None:
        self.http_client = httpx.AsyncClient()
        check_set.add(id(self.http_client))

    async def before_reset_context(self, request: Request, response: Optional[Response]) -> None:
        await self.http_client.aclose()


context_model: ContextModel = ContextModel()
app.add_middleware(ContextMiddleware, context_model=context_model)


async def test_ensure_future() -> None:
    assert id(context_model.http_client) in check_set


def test_run_in_executor() -> None:
    assert id(context_model.http_client) in check_set


def test_call_soon() -> None:
    assert id(context_model.http_client) in check_set


@app.get("/")
async def root() -> dict:
    asyncio.ensure_future(test_ensure_future())
    loop: "asyncio.AbstractEventLoop" = asyncio.get_event_loop()

    loop.call_soon(test_call_soon)
    ctx: Context = copy_context()
    await loop.run_in_executor(None, partial(ctx.run, test_run_in_executor))  # type: ignore
    return {
        "message": context_model.to_dict(is_safe_return=True),  # not return CustomQuery
        "client_id": id(context_model.http_client),
    }


if __name__ == "__main__":
    import uvicorn  # type: ignore

    uvicorn.run(app)
