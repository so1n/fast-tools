import aiohttp
import uvicorn
from skywalking import agent, config
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from fast_tools.apache_skywalking import SkywalkingMiddleware

config.init(service_name="test server service", log_reporter_active=True)
app = Starlette()


@app.route("/")
async def root(request: Request) -> JSONResponse:
    return JSONResponse({"Hello": "World"})


@app.route("/proxy_test")
async def proxy_test(request: Request) -> PlainTextResponse:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://google.com") as response:
            return PlainTextResponse(await response.text())


app.add_middleware(SkywalkingMiddleware)


if __name__ == "__main__":
    agent.start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
    agent.stop()
