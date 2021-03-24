#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "so1n"
__date__ = "2020-08"
from fastapi import Depends, FastAPI, Header, Query

from fast_tools.cbv import Cbv, cbv_decorator

app: FastAPI = FastAPI()


def get_user_agent(user_agent: str = Header("User-Agent")) -> str:
    return user_agent


class TestCbv(object):
    host: str = Header("host")
    user_agent: str = Depends(get_user_agent)

    def __init__(self, test_default_id: int = Query(123)):
        self.test_default_id = test_default_id

    def _response(self) -> dict:
        return {"message": "hello, world", "user_agent": self.user_agent, "host": self.host, "id": self.test_default_id}

    @cbv_decorator(status_code=203)
    def get(self) -> dict:
        return self._response()

    def post(self) -> dict:
        return self._response()


app.include_router(Cbv(TestCbv).router)

if __name__ == "__main__":
    import uvicorn  # type: ignore

    uvicorn.run(app)
