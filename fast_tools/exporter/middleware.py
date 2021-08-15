import time
from typing import Optional, Set

from prometheus_client import Counter, Gauge, Histogram  # type: ignore
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from fast_tools.base import NAMESPACE, BaseSearchRouteMiddleware, RouteTrie


class PrometheusMiddleware(BaseSearchRouteMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        app_name: str = NAMESPACE.replace("-", "_"),
        prefix: str = NAMESPACE.replace("-", "_"),
        route_trie: Optional["RouteTrie"] = None,
        block_url_set: Optional[Set[str]] = None,
    ) -> None:
        super().__init__(app, route_trie=route_trie)
        self._app_name: str = app_name
        self._block_url_set = block_url_set or set()

        self.request_count: "Counter" = Counter(
            f"{prefix}_requests_total", "Count of requests", ["app_name", "method", "url_path"]
        )
        self.response_count: "Counter" = Counter(
            f"{prefix}_responses_total",
            "Count of responses",
            ["app_name", "method", "url_path", "status_code"],
        )
        self.request_time: "Histogram" = Histogram(
            f"{prefix}_requests_time",
            "Histogram of requests time by url",
            ["app_name", "method", "url_path"],
        )
        self.exception_count: "Counter" = Counter(
            f"{prefix}_exceptions_total",
            "count of exceptions",
            ["app_name", "method", "url_path", "exception_type"],
        )
        self.request_in_progress: "Gauge" = Gauge(
            f"{prefix}_requests_in_progress",
            "Gauge of current requests",
            ["app_name", "method", "url_path"],
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        url_path, is_match = self.search_route_url(request)

        if url_path in self._block_url_set or not is_match:
            return await call_next(request)

        label_list: list = [self._app_name, request.method, url_path]
        self.request_in_progress.labels(*label_list).inc()
        self.request_count.labels(*label_list).inc()

        status_code: int = 500
        start_time: float = time.time()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            self.exception_count.labels(*label_list, type(e).__name__).inc()
            raise e
        finally:
            self.request_time.labels(*label_list).observe(time.time() - start_time)

            self.response_count.labels(*label_list, status_code).inc()
            self.request_in_progress.labels(*label_list).dec()

        return response
