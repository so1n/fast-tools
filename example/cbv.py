#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'so1n'
__date__ = '2020-08'
from fastapi import FastAPI, Header
from fastapi_tools.cbv import cbv_decorator, Cbv

app = FastAPI()


class TestCbv(Cbv):

    @cbv_decorator(status_code=203)
    def get(self, user_agent: str = Header("User_Agent")):
        return {"message": "hello, world", "user_agent": user_agent}

    def post(self):
        return {"message": "hello, world"}


app.include_router(TestCbv().router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
