import asyncio
import re
from typing import Awaitable, List, Optional, Tuple, Union

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
        rule_list: List[Tuple[str, Optional[RULE_FUNC_TYPE], List[Rule]]] = None,
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
        self._status_code: int = status_code
        self._enable_match_fail_pass: bool = enable_match_fail_pass

        self._rule_list: List[Tuple[re.Pattern[str], Optional[RULE_FUNC_TYPE], List[Rule]]] = (
            [(re.compile(pattern_str), limit_func, rule) for pattern_str, limit_func, rule in rule_list]
            if rule_list
            else []
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        async def _can_request_handle(_can_request: bool) -> Response:
            if _can_request:
                return await call_next(request)
            else:
                return Response(content=self._content, status_code=self._status_code)

        url_path: str = request.url.path
        for pattern, rule_func, rule_list in self._rule_list:
            if pattern.match(url_path):
                break
        else:
            return await _can_request_handle(self._enable_match_fail_pass)

        key: str = str(pattern)
        group: Optional[str] = None
        if rule_func is not None:
            if asyncio.iscoroutinefunction(rule_func):
                key, group = await rule_func(request)  # type: ignore
            else:
                key, group = rule_func(request)  # type: ignore

        for rule in rule_list:
            if rule.group == group:
                break
        else:
            return await _can_request_handle(self._enable_match_fail_pass)

        key = f"{group}:{key}"
        can_requests: Union[bool, Awaitable[bool]] = self._backend.can_next(key, rule)
        if asyncio.iscoroutine(can_requests):
            can_requests = await can_requests  # type: ignore

        return await _can_request_handle(can_requests)  # type: ignore
