import asyncio
import aioredis  # type: ignore
import time
import pytest
from requests import Response
from starlette.testclient import TestClient

from example.cache import app
from fast_tools.base.redis_helper import RedisHelper
from .conftest import AnyStringWith  # type: ignore


pytestmark = pytest.mark.asyncio


class TestCache:
    def test_cache(self) -> None:
        async def clear() -> None:
            redis_helper: RedisHelper = RedisHelper()
            redis_helper.init(await aioredis.create_pool("redis://localhost", minsize=1, maxsize=10, encoding="utf-8"))
            await redis_helper.client.delete("fast-tools:root:():{}")
            await redis_helper.client.delete("fast-tools:user_login:123")
            await redis_helper.client.delete("fast-tools:user_login:1234")
            await redis_helper.close()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(clear())

        with TestClient(app) as client:
            index_1_response: Response = client.get("/")
            time.sleep(0.1)
            index_2_response: Response = client.get("/")
            assert index_1_response.json() == index_2_response.json()
            assert "cache-control" not in index_1_response.headers
            assert index_2_response.headers["cache-control"].startswith("max-age")

            login_1_response: Response = client.get("/api/users/login?uid=123")
            time.sleep(0.1)
            login_2_response: Response = client.get("/api/users/login?uid=123")
            time.sleep(0.1)
            login_3_response: Response = client.get("/api/users/login?uid=1234")
            assert login_1_response.json() == login_2_response.json()
            assert login_1_response.json() != login_3_response.json()
            assert "cache-control" not in login_1_response.headers
            assert login_2_response.headers["cache-control"].startswith("max-age")
            assert "cache-control" not in login_3_response.headers

            null_1_response: Response = client.get("/api/null")
            time.sleep(0.1)
            null_2_response: Response = client.get("/api/null")
            assert null_1_response.json() != null_2_response.json()
            assert "cache-control" not in null_1_response.headers
            assert "cache-control" not in null_2_response.headers

            with pytest.raises(ValueError) as e:
                client.get("/api/get_key_error")
            assert e.value.args[0] == "Can not found request param"
