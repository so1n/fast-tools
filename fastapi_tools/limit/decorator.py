import asyncio
from functools import wraps
from typing import Awaitable, Callable, Optional, Union

from starlette.requests import Request
from starlette.responses import Response
from fastapi_tools.limit.rule import Rule
from fastapi_tools.limit.backend.base import BaseLimitBackend
from fastapi_tools.limit.backend.memory import TokenBucket
from fastapi_tools.limit.util import (
    DEFAULT_CONTENT,
    DEFAULT_STATUS_CODE
)


def limit(
        rule: Rule,
        backend: BaseLimitBackend = TokenBucket(),
        limit_func: Optional[Callable] = None,
        status_code: int = DEFAULT_STATUS_CODE,
        content: str = DEFAULT_CONTENT,
):
    def wrapper(func: Callable) -> Callable:
        @wraps(func)
        async def _limit(*args, **kwargs):
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            key: str = str(id(func))
            if limit_func is not None and request is not None:
                if asyncio.iscoroutinefunction(limit_func):
                    key = await limit_func(request)
                else:
                    key = limit_func(request)

            can_requests: Union[bool, Awaitable[bool]] = backend.can_requests(key, rule)
            if asyncio.iscoroutine(can_requests):
                can_requests = await can_requests
            if can_requests:
                return await func(*args, **kwargs)
            else:
                return Response(content=content, status_code=status_code)
        return _limit
    return wrapper
