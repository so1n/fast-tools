import asyncio
import re
from typing import Awaitable, Dict, List, Optional, Union

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from fast_tools.limit.backend.base import BaseLimitBackend
from fast_tools.limit.backend.memory import TokenBucket
from fast_tools.limit.rule import Rule
from fast_tools.limit.util import DEFAULT_CONTENT, DEFAULT_STATUS_CODE, RULE_FUNC_TYPE


class LimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        backend: BaseLimitBackend = TokenBucket(),
        status_code: int = DEFAULT_STATUS_CODE,
        content: str = DEFAULT_CONTENT,
        func: Optional[RULE_FUNC_TYPE] = None,
        rule_dict: Dict[str, Rule] = None,
        enable_match_fail_pass: bool = True
    ) -> None:
        """
        rule_dict: key: url re rule, value: rule obj list
        backend: Current limiting method
        limit_func: Get the current request key and group value
        status_code: fail response status code
        content: fail response content
        enable_match_fail_pass: if not match and `enable_match_fail_pass` is False,
         If the match fails, the flow is not limited
        """
        super().__init__(app)
        self._backend: BaseLimitBackend = backend
        self._content: str = content
        self._func: Optional[RULE_FUNC_TYPE] = func
        self._status_code: int = status_code
        self._enable_match_fail_pass: bool = enable_match_fail_pass

        self._rule_dict: Dict[re.Pattern[str], List[Rule]] = {
            re.compile(key): value for key, value in rule_dict.items()
        }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        url_path: str = request.url.path
        for pattern, rule_list in self._rule_dict.items():
            if pattern.match(url_path):
                break
        else:
            return await call_next(request)

        key: str = str(pattern)
        group: Optional[str] = None
        if self._func is not None:
            if asyncio.iscoroutinefunction(self._func):
                key, group = await self._func(request)
            else:
                key, group = self._func(request)

        for rule in rule_list:
            if rule.group == group:
                break
        else:
            if self._enable_match_fail_pass:
                return await call_next(request)
            else:
                return Response(content=self._content, status_code=self._status_code)

        can_requests: Union[bool, Awaitable[bool]] = self._backend.can_requests(key, rule)
        if asyncio.iscoroutine(can_requests):
            can_requests = await can_requests
        if can_requests:
            return await call_next(request)
        else:
            return Response(content=self._content, status_code=self._status_code)
