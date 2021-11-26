import aiohttp
import uvicorn
from jaeger_client import Config as jaeger_config
from opentracing.scope_managers.contextvars import ContextVarsScopeManager
from opentracing_async_instrumentation.client_hooks import install_all_patches
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from fast_tools.opentracing import OpentracingMiddleware

app = Starlette()


@app.route("/")
async def root(request: Request) -> JSONResponse:
    return JSONResponse({"Hello": "World"})


@app.route("/proxy_test")
async def proxy_test(request: Request) -> PlainTextResponse:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://google.com") as response:
            return PlainTextResponse(await response.text())


opentracing_config = jaeger_config(
    config={
        "sampler": {"type": "const", "param": 1},
        "logging": False,
        "local_agent": {"reporting_host": "localhost"},
    },
    scope_manager=ContextVarsScopeManager(),
    service_name="fast-tools tracer example",
)
jaeger_tracer = opentracing_config.initialize_tracer()
install_all_patches()
app.add_middleware(OpentracingMiddleware, tracer=jaeger_tracer)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
