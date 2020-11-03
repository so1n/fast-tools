import time
from typing import Optional, Set

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from fast_tools.base import RouteTrie


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        app_name: str = "fast_tools",
        prefix: str = "fast_tools",
        route_trie: Optional["RouteTrie"] = None,
        block_url_set: Optional[Set[str]] = None,
    ) -> None:
        super().__init__(app)
        self._app_name: str = app_name
        self._block_url_set = block_url_set
        self._route_trie: Optional[RouteTrie] = route_trie

        self.request_count: "Counter" = Counter(
            f"{prefix}_requests_total", "Count of requests", ["app_name", "method", "url_path"]
        )
        self.response_count: "Counter" = Counter(
            f"{prefix}_tool_responses_total",
            "Count of responses",
            ["app_name", "method", "url_path", "status_code"],
        )
        self.request_time: "Histogram" = Histogram(
            f"{prefix}_tool_requests_time",
            "Histogram of requests time by url (in seconds) status:1 success status:0 fail",
            ["app_name", "method", "url_path", "status"],
        )
        self.exception_count: "Counter" = Counter(
            f"{prefix}_tool_exceptions_total",
            "count of exceptions",
            ["app_name", "method", "url_path", "exception_type"],
        )
        self.request_in_progress: "Gauge" = Gauge(
            f"{prefix}_tool_requests_in_progress",
            "Gauge of current requests",
            ["app_name", "method", "url_path"],
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method: str = request.method
        url_path: str = request.url.path

        if self._route_trie:
            route = self._route_trie.search_by_scope(url_path, request.scope)
            if not route:
                return await call_next(request)
            else:
                url_path = route.path

        if url_path in self._block_url_set:
            return await call_next(request)

        label_list: list = [self._app_name, method, url_path]
        self.request_in_progress.labels(*label_list).inc()
        self.request_count.labels(*label_list).inc()

        status_code = 500
        start_time = time.time()
        request_result = 0
        try:
            response = await call_next(request)
            status_code = response.status_code
            request_result = 1
        except Exception as e:
            self.exception_count.labels(*label_list, type(e).__name__).inc()
            raise e
        finally:
            self.request_time.labels(*label_list, request_result).observe(time.time() - start_time)

            self.response_count.labels(*label_list, status_code).inc()
            self.request_in_progress.labels(*label_list).dec()

        return response
