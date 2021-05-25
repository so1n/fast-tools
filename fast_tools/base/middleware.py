from abc import ABC
from contextvars import ContextVar
from typing import Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.routing import Match, Route
from starlette.types import ASGIApp

from .route_trie import RouteTrie  # type: ignore
from .utils import NAMESPACE  # type: ignore

_SEARCH_ROUTE_MIDDLEWARE_CONTEXT: ContextVar[str] = ContextVar(f"{NAMESPACE}:search_route_middleware", default="")


class BaseSearchRouteMiddleware(BaseHTTPMiddleware, ABC):
    def __init__(
        self,
        app: ASGIApp,
        *,
        route_trie: Optional["RouteTrie"] = None,
    ) -> None:
        super().__init__(app)
        self._route_trie: Optional[RouteTrie] = route_trie

    def search_route(self, request: Request) -> Optional[Route]:
        search_route: Optional[Route] = None
        if self._route_trie:
            search_route = self._route_trie.search_by_scope(request.url.path, request.scope)
        if not search_route:
            for route in request.app.routes:
                match, child_scope = route.matches(request.scope)
                if match == Match.FULL:
                    search_route = route
                    break
        return search_route

    def search_route_url(self, request: Request) -> Tuple[str, bool]:
        is_match: bool = False
        url_path: str = _SEARCH_ROUTE_MIDDLEWARE_CONTEXT.get()
        if url_path:
            return url_path, True
        else:
            url_path = request.url.path

        route: Optional[Route] = self.search_route(request)
        if route:
            url_path = route.path
            is_match = True

        _SEARCH_ROUTE_MIDDLEWARE_CONTEXT.set(url_path)
        return url_path, is_match
