import time
from typing import Callable, List, Optional, Set

from aio_statsd import StatsdClient  # type: ignore
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from fast_tools.base import NAMESPACE, BaseSearchRouteMiddleware, RouteTrie


class StatsdMiddleware(BaseSearchRouteMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        client: StatsdClient,
        app_name: str = NAMESPACE,
        prefix: str = NAMESPACE,
        route_trie: Optional["RouteTrie"] = None,
        url_replace_handle: Optional[Callable] = None,
        block_url_set: Optional[Set[str]] = None,
    ) -> None:
        super().__init__(app, route_trie=route_trie)
        self._block_url_set: Set[str] = block_url_set or set()
        self._client: StatsdClient = client
        self._metric = ""
        self._url_replace_handle = url_replace_handle

        self._metric = self._join_metric(self._metric, [prefix])
        self._metric = self._join_metric(self._metric, [app_name])

    @staticmethod
    def _join_metric(metric: str, column_list: List[str]) -> str:
        for column in column_list:
            if not column.endswith("."):
                metric += column + "."
            else:
                metric += column
        return metric

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method: str = request.method
        url_path, is_match = self.search_route_url(request)

        if url_path in self._block_url_set or not is_match:
            return await call_next(request)

        if self._url_replace_handle:
            url_path = self._url_replace_handle(url_path)
        metric: str = self._join_metric(self._metric, [method, url_path])
        self._client.gauge(self._join_metric(metric, ["request_in_progress"]), 1)
        self._client.gauge(self._join_metric(metric, ["request_count"]), 1)

        status_code: int = 500
        start_time: float = time.time()
        request_result: str = "fail"
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            request_result = "success"
            return response
        except Exception as e:
            self._client.gauge(self._join_metric(metric, ["exception", type(e).__name__]), 1)
            raise e
        finally:
            self._client.timer(self._join_metric(metric, [request_result, "request_time"]), time.time() - start_time)
            self._client.gauge(self._join_metric(metric, [str(status_code), "response_count"]), 1)
            self._client.gauge(self._join_metric(metric, [str(status_code), "response_count"]), 1)
            self._client.gauge(self._join_metric(metric, ["request_in_progress"]), -1)
            self._client.gauge(self._join_metric(metric, ["request_in_progress"]), -1)
