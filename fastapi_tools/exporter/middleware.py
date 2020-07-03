import time
from typing import Dict, List, Optional, Set

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app: ASGIApp,
            is_filter_url_path: bool = True,
            app_name: str = 'fastapi_tools',
            prefix: str = 'fastapi_tools',
            block_url_set: Optional[Set[str]] = None
    ) -> None:
        super().__init__(app)
        self._app_name: str = app_name
        self._url_dict: Dict[str,  Set] = {}
        self._is_filter_url_path: bool = is_filter_url_path
        self._block_url_set: set = block_url_set
        if self._is_filter_url_path:
            self._register_url()

        self.request_count: 'Counter' = Counter(
            f"{prefix}_requests_total",
            "Count of requests",
            ["app_name", "method", "url_path"]
        )
        self.response_count: 'Counter' = Counter(
            f"{prefix}_tool_responses_total",
            "Count of responses",
            ["app_name", "method", "url_path", "status_code"],
        )
        self.request_time: 'Histogram' = Histogram(
            f"{prefix}_tool_requests_time",
            "Histogram of requests time by url (in seconds) status:1 success status:0 fail",
            ["app_name", "method", "url_path", "status"],
        )
        self.exception_count: 'Counter' = Counter(
            f"{prefix}_tool_exceptions_total",
            "count of exceptions",
            ["app_name", "method", "url_path", "exception_type"],
        )
        self.request_in_progress: 'Gauge' = Gauge(
            f"{prefix}_tool_requests_in_progress",
            "Gauge of current requests",
            ["app_name", "method", "url_path"],
        )

    def _register_url(self):
        # TODO support query parameters
        # This type of url is currently not statistics
        # If match this type of url, it may reduce performance
        # if it does not match, it will generate a lot of metrics
        # example handle :https://fastapi.tiangolo.com/tutorial/query-params/#multiple-path-and-query-parameters
        new_app = self.app
        while True:
            if hasattr(new_app, 'app'):
                new_app = new_app.app
            else:
                break
        for route in new_app.routes:
            url: str = route.path
            if self._block_url_set and url in self._block_url_set:
                continue
            if url not in self._url_dict:
                self._url_dict[url] = route.methods
            else:
                # support cbv
                self._url_dict[url].update(route.methods)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method: str = request.method
        url_path: str = request.url.path
        if self._is_filter_url_path and url_path not in self._url_dict:
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
