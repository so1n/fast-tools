import asyncio
from functools import wraps
from typing import Any, Awaitable, Callable, List, Optional, Union

from starlette.requests import Request
from starlette.responses import Response

from fast_tools.limit.backend.base import BaseLimitBackend
from fast_tools.limit.backend.memory import TokenBucket
from fast_tools.limit.rule import Rule
from fast_tools.limit.util import DEFAULT_CONTENT, DEFAULT_STATUS_CODE, RULE_FUNC_TYPE


def limit(
    rule_list: List[Rule],
    backend: BaseLimitBackend = TokenBucket(),
    limit_func: Optional[RULE_FUNC_TYPE] = None,
    status_code: int = DEFAULT_STATUS_CODE,
    content: str = DEFAULT_CONTENT,
    enable_match_fail_pass: bool = True,
) -> Callable:
    """
    rule_list: Rule obj list
    backend: Current limiting method
    limit_func: Get the current request key and group value
    status_code: fail response status code
    content: fail response content
    enable_match_fail_pass: if not match and `enable_match_fail_pass` is False,
     If the match fails, the flow is not limited
    """

    def wrapper(func: Callable) -> Callable:
        @wraps(func)
        async def _limit(*args: Any, **kwargs: Any) -> Any:
            # get request param
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # set default key, group
            key: str = str(id(func))
            group: Optional[str] = None

            # search key, group
            if limit_func is not None and request is not None:
                if asyncio.iscoroutinefunction(limit_func):
                    key, group = await limit_func(request)  # type: ignore
                else:
                    key, group = limit_func(request)  # type: ignore

            # match url rule
            for rule in rule_list:
                if rule.group == group:
                    break
            else:
                if enable_match_fail_pass:
                    return await func(*args, **kwargs)
                else:
                    return Response(content=content, status_code=status_code)
            can_requests: Union[bool, Awaitable[bool]] = backend.can_requests(key, rule)
            if asyncio.iscoroutine(can_requests):
                can_requests = await can_requests  # type: ignore
            if can_requests:
                return await func(*args, **kwargs)
            else:
                return Response(content=content, status_code=status_code)

        return _limit

    return wrapper
