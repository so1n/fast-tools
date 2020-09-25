"""
➜ curl 127.0.0.1:8000/api/test/900
46.60431654676259
➜ curl 127.0.0.1:8000/api/test/1
1.396694214876033
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, Match
from starlette.types import ASGIApp

from starlette.applications import Starlette

from fastapi_tools.base import RouteTrie


class TestMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app: ASGIApp,
            *,
            route_trie: RouteTrie = None,
    ) -> None:
        super().__init__(app)
        self._route_trie: RouteTrie = route_trie

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        url_path: str = request.url.path

        start_time: float = time.time()
        self._route_trie.search_by_scope(url_path, request.scope)
        route_trie_speed_time =  time.time() - start_time

        start_time: float = time.time()
        for route in request.app.routes:
            match, child_scope = route.matches(request.scope)
            if match == Match.FULL:
                break
        self_server_speed_time = time.time() - start_time
        return Response(content=str(self_server_speed_time/route_trie_speed_time))


async def homepage(request):
    return JSONResponse({'hello': 'world'})


route_trie = RouteTrie()


app = Starlette(
    routes=[Route(f'/api/test/{i}', homepage) for i in range(1000)],
)
app.add_middleware(TestMiddleware, route_trie=route_trie)


async def load_route_trie():
    route_trie.insert_by_app(app)

app.on_event("startup")(load_route_trie)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
