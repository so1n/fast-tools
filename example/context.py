#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test fastapi_tools.context in fastapi
> curl 127.0.0.01:8000
{"message":{"X-Request-Id":"b76dc9c3-ce93-4200-8508-b829c6ec72d4","X-Real-IP":"127.0.0.1","User-Agent":"curl/7.52.1"}}
"""
__author__ = 'so1n'
__date__ = '2020-06'
import uuid
import httpx
from fastapi import FastAPI
from fastapi_tools.context import ContextMiddleware
from fastapi_tools.context import ContextBaseModel
from fastapi_tools.context import HeaderQuery
from fastapi_tools.context import CustomQuery

app = FastAPI()
client = httpx.AsyncClient()


class ContextModel(ContextBaseModel):
    request_id: str = HeaderQuery(
        'X-Request-Id',
        default_func=lambda x: str(uuid.uuid4())
    )
    ip: str = HeaderQuery(
        'X-Real-IP',
        default_func=lambda request: request.client.host
    )
    user_agent: str = HeaderQuery('User-Agent')
    http_client: httpx.AsyncClient = CustomQuery(client)


app.add_middleware(ContextMiddleware, context_model=ContextModel())


@app.get("/")
async def root():
    assert ContextModel.http_client == client
    return {
        "message": {
            key: value
            for key, value in ContextModel.to_dict().items()
            if not key.startswith('custom')
        }
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
