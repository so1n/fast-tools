from skywalking import Component, Layer, config
from skywalking.trace.carrier import Carrier
from skywalking.trace.context import NoopContext, get_context
from skywalking.trace.span import NoopSpan
from skywalking.trace.tags import TagHttpMethod, TagHttpParams, TagHttpStatusCode, TagHttpURL
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class SkywalkingMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        super(SkywalkingMiddleware, self).__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        carrier: Carrier = Carrier()
        for item in carrier:
            if item.key in request.headers:
                item.val = request.headers[item.key]

        for item in carrier:
            if item.key.capitalize() in request.headers:
                item.val = request.headers[item.key.capitalize()]

        span = (
            NoopSpan(NoopContext())
            if config.ignore_http_method_check(request.method)
            else get_context().new_entry_span(op=request.scope["path"], carrier=carrier)
        )

        with span:
            span.layer = Layer.Http
            span.component = Component.Unknown
            span.peer = f"{request.client.host}:{request.client.port}"
            span.tag(TagHttpMethod(request.method))
            span.tag(TagHttpURL(str(request.url)))
            span.tag(TagHttpParams(request.query_params))
            response = await call_next(request)
            span.tag(TagHttpStatusCode(response.status_code))
            span.error_occurred = response.status_code >= 400
        return response
