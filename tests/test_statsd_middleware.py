import asyncio
from typing import Tuple
from starlette.testclient import TestClient
from example.statsd_middleware import app


result_queue: asyncio.Queue = asyncio.Queue()


@app.on_event("startup")
async def udp_server() -> None:

    class ServerProtocol(asyncio.DatagramProtocol):
        def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
            result_queue.put_nowait(data)

    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    await loop.create_datagram_endpoint(lambda: ServerProtocol(), local_addr=("localhost", 8125))


class TestExporter:
    def test_exporter(self) -> None:
        with TestClient(app) as client:
            client.get("/")
            client.get("/not_found")
            client.get("/api/users/login")
            client.get("/api/users/123/items/abc")
            client.get("/api/users/456/items/def")

        import time
        time.sleep(1)
        server_body_str: str = ""
        while not result_queue.empty():
            server_body_str += result_queue.get_nowait().decode() + "\n"

        assert "not_found" not in server_body_str
        assert "_api_users_login" in server_body_str
        assert "_api_users_{user_id}_items_{item_id}" in server_body_str
        assert "/api/users/123/items/abc" not in server_body_str
        assert "/api/users/456/items/def" not in server_body_str
