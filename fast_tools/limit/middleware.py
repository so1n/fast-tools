import asyncio
import re
from typing import Awaitable, Dict, List, Optional, Tuple, Union

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
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
        limit_func: Optional[RULE_FUNC_TYPE] = None,
        rule_list: List[Tuple[str, List[Rule]]] = None,
        enable_match_fail_pass: bool = True,
    ) -> None:
        """
        rule_list: [url re rule, [rule obj list]]
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
        self._func: Optional[RULE_FUNC_TYPE] = limit_func
        self._status_code: int = status_code
        self._enable_match_fail_pass: bool = enable_match_fail_pass

        self._rule_list: List[Tuple[re.Pattern[str], List[Rule]]] = (
            [(re.compile(key), value) for key, value in rule_list] if rule_list else []
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        url_path: str = request.url.path
        for pattern, rule_list in self._rule_list:
            if pattern.match(url_path):
                break
        else:
            if self._enable_match_fail_pass:
                return await call_next(request)
            else:
                return Response(content=self._content, status_code=self._status_code)

        key: str = str(pattern)
        group: Optional[str] = None
        if self._func is not None:
            if asyncio.iscoroutinefunction(self._func):
                key, group = await self._func(request)  # type: ignore
            else:
                key, group = self._func(request)  # type: ignore

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
            can_requests = await can_requests  # type: ignore
        if can_requests:
            return await call_next(request)
        else:
            return Response(content=self._content, status_code=self._status_code)
