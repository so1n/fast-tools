import re
from typing import Any, Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from fastapi_tools.limit.rule import Rule
from fastapi_tools.limit.token_bucket import TokenBucket


class LimitMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app: ASGIApp,
            *,
            rule_dict: Dict[str, Rule] = None
    ) -> None:
        super().__init__(app)
        self._cache_dict: Dict[re.Pattern[str, Any]] = {}
        self._rule_dict: Dict[re.Pattern[str], Rule] = {re.compile(key): value for key, value in rule_dict.items()}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        url_path: str = request.url.path
        for pattern, rules in self._rule_dict.items():
            if pattern.match(url_path):
                break
        else:
            return await call_next(request)

        token_bucket: Optional[TokenBucket] = self._cache_dict.get(pattern, None)
        if token_bucket is None:
            token_bucket = TokenBucket(rules.get_token(), max_token=rules.max_token)
            self._cache_dict[pattern] = token_bucket

        if token_bucket.can_consume():
            return await call_next(request)
        else:
            return Response(status_code=429)
