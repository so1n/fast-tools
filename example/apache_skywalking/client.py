import asyncio
import time

import aiohttp
from skywalking import agent, config

config.init(service_name="test client service", log_reporter_active=True)
loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        async with session.get("http://127.0.0.1:8000/") as response:
            print(await response.text())

        async with session.get("http://127.0.0.1:8000/proxy_test") as response:
            print(await response.text())


agent.start()
loop.run_until_complete(main())
time.sleep(2)
agent.stop()
