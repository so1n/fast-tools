from abc import ABC
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.routing import Match
from starlette.types import ASGIApp

from .route_trie import RouteTrie
from .utils import NAMESPACE


_SEARCH_ROUTE_MIDDLEWARE_CONTEXT: ContextVar[Optional[str]] = ContextVar(
    f"{NAMESPACE}:search_route_middleware", default=None
)


class BaseSearchRouteMiddleware(BaseHTTPMiddleware, ABC):
    def __init__(
        self,
        app: ASGIApp,
        *,
        route_trie: Optional["RouteTrie"] = None,
    ) -> None:
        super().__init__(app)
        self._route_trie: Optional[RouteTrie] = route_trie

    def search_route_url(self, request: Request) -> str:
        url_path: str = _SEARCH_ROUTE_MIDDLEWARE_CONTEXT.get()
        if url_path:
            return url_path
        url_path: str = request.url.path

        if self._route_trie:
            route = self._route_trie.search_by_scope(url_path, request.scope)
            if route:
                url_path = route.path
        else:
            for route in request.app.routes:
                match, child_scope = route.matches(request.scope)
                if match == Match.FULL:
                    url_path = route.path
                    break
        _SEARCH_ROUTE_MIDDLEWARE_CONTEXT.set(url_path)
        return url_path
