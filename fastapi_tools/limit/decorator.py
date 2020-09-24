import asyncio
from functools import wraps
from typing import Any, Callable, Dict, Optional

from starlette.requests import Request
from starlette.responses import Response
from fastapi_tools.limit.rule import Rule
from fastapi_tools.limit.backend.base import BaseLimitBackend
from fastapi_tools.limit.backend.memory import TokenBucket


_cache_dict: Dict[str, Any] = {}


def limit(
        rule: Rule,
        backend: BaseLimitBackend = TokenBucket(),
        limit_func: Optional[Callable] = None,
        status_code: int = 429,
        content: str = 'This user has exceeded an allotted request count. Try again later.',
):
    def wrapper(func: Callable) -> Callable:
        @wraps(func)
        async def _limit(*args, **kwargs):
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg

            key: str = str(id(func))
            if limit_func is not None and request is not None:
                if asyncio.iscoroutinefunction(limit_func):
                    key = await limit_func(request)
                else:
                    key = limit_func(request)

            if backend.can_requests(key, rule):
                return await func(*args, **kwargs)
            else:
                return Response(content=content, status_code=status_code)
        return _limit
    return wrapper
