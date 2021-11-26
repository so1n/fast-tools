from typing import Optional

from opentracing import InvalidCarrierException, SpanContextCorruptedException
from opentracing.ext import tags
from opentracing.propagation import Format
from opentracing.span import SpanContext
from opentracing.tracer import Tracer
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from fast_tools.base import NAMESPACE


class OpentracingMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        tracer: Tracer,
        component: str = NAMESPACE,
    ) -> None:
        super(OpentracingMiddleware, self).__init__(app)
        self._component: str = component
        self._tracer: Tracer = tracer

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        span_ctx: Optional[SpanContext] = None

        try:
            span_ctx = self._tracer.extract(Format.HTTP_HEADERS, request.headers)
        except (InvalidCarrierException, SpanContextCorruptedException):
            pass

        with self._tracer.start_active_span(
            str(request.scope["path"]), child_of=span_ctx, finish_on_close=True
        ) as scope:
            scope.span.set_tag(tags.COMPONENT, self._component)
            scope.span.set_tag(tags.SPAN_KIND, tags.SERVICE)
            scope.span.set_tag(tags.HTTP_METHOD, request.method)
            scope.span.set_tag(tags.HTTP_URL, str(request.url))

            response = await call_next(request)

            scope.span.set_tag("status_code", response.status_code)
            scope.span.set_tag(tags.ERROR, response.status_code >= 400)
        return response
