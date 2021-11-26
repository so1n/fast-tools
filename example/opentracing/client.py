import asyncio
import time

import aiohttp
from jaeger_client import Config
from jaeger_client.tracer import Tracer
from opentracing_async_instrumentation.client_hooks import install_all_patches

config = Config(
    config={"sampler": {"type": "const", "param": 1}, "logging": True, "local_agent": {"reporting_host": "127.0.0.1"}},
    service_name="jaeger_opentracing_example",
)
tracer: Tracer = config.initialize_tracer()  # type: ignore
install_all_patches()
loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        async with session.get("http://127.0.0.1:8000/") as response:
            print(await response.text())

        async with session.get("http://127.0.0.1:8000/proxy_test") as response:
            print(await response.text())


loop.run_until_complete(main())
time.sleep(2)
tracer.close()
