import asyncio
import time

import aioredis  # type: ignore
import pytest
from requests import Response  # type: ignore
from starlette.testclient import TestClient

from example.limit import app
from fast_tools.base.redis_helper import RedisHelper
from fast_tools.limit.backend import RedisCellBackend, RedisFixedWindowBackend, RedisTokenBucketBackend, TokenBucket
from fast_tools.limit.rule import Rule

from .conftest import AnyStringWith  # type: ignore


@pytest.fixture(scope="class", autouse=True)
def clear() -> None:
    async def _clear() -> None:
        redis_helper: RedisHelper = RedisHelper()
        redis_helper.init(await aioredis.create_pool("redis://localhost", minsize=1, maxsize=10, encoding="utf-8"))
        delete_key_list = []
        async for key in redis_helper.client.iscan(match="fast-tool*"):
            delete_key_list.append(key)

        if delete_key_list:
            await redis_helper.client.delete("fake", *delete_key_list)

        await redis_helper.close()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_clear())


class TestLimit:
    @staticmethod
    def _test_backend_helper(url: str) -> None:
        with TestClient(app) as client:
            response: Response = client.get(url)
            assert response.json() == {"Hello": "World"}
            response = client.get(url)
            assert response.status_code == 429
            assert response.text == "This user has exceeded an allotted request count. Try again later."
            time.sleep(0.9)
            response = client.get(url)
            assert response.status_code == 429
            time.sleep(0.5)
            response = client.get(url)
            assert response.json() == {"Hello": "World"}

    def test_redis_fixed_window(self) -> None:
        self._test_backend_helper("/")

    def test_redis_token_bucket(self) -> None:
        self._test_backend_helper("/redis/token_bucket")

    def test_redis_cell(self) -> None:
        self._test_backend_helper("/redis/cell")

    def test_memory_token_bucket(self) -> None:
        self._test_backend_helper("/memory/token_bucket")

    def test_memory_thread_token_bucket(self) -> None:
        self._test_backend_helper("/memory/thread_token_bucket")

    def test_decorator(self) -> None:
        with TestClient(app) as client:
            for _ in range(10):
                response: Response = client.get("/decorator")
                assert response.json() == {"Hello": "World"}

            response = client.get("/decorator?user=user1")
            assert response.json() == {"Hello": "World"}
            response = client.get("/decorator?user=user1")
            assert response.status_code == 429

            for _ in range(2):
                response = client.get("/decorator?user=user2")
                assert response.json() == {"Hello": "World"}
            response = client.get("/decorator?user=user2")
            assert response.status_code == 429

    def test_middleware(self) -> None:
        with TestClient(app) as client:
            for _ in range(10):
                response: Response = client.get("/api/user/login")
                assert response.json() == {"Hello": "World"}

            response = client.get("/api/user/login?uid=123&group=user")
            assert response.status_code == 200
            response = client.get("/api/user/logout?uid=123&group=user")
            assert response.status_code == 429

            response = client.get("/api/user/login?uid=123&group=admin")
            assert response.status_code == 200
            response = client.get("/api/user/logout?uid=123&group=admin")
            assert response.status_code == 200
            response = client.get("/api/user/login?uid=123&group=admin")
            assert response.status_code == 429

    def test_expected_time(self) -> None:
        async def _test() -> None:
            rule: Rule = Rule(second=10, gen_token_num=1, block_time=20, max_token_num=1)
            token_bucket: TokenBucket = TokenBucket()
            token_bucket.can_next("test_memory_token_bucket", rule=rule)
            assert token_bucket.expected_time("test_memory_token_bucket", rule=rule) == 10
            token_bucket.can_next("test_memory_token_bucket", rule=rule)
            assert 19 <= token_bucket.expected_time("test_memory_token_bucket", rule=rule) <= 20

            redis_helper: RedisHelper = RedisHelper()
            redis_helper.init(await aioredis.create_pool("redis://localhost", minsize=1, maxsize=10, encoding="utf-8"))
            redis_fixed_window_backend: RedisFixedWindowBackend = RedisFixedWindowBackend(redis_helper)
            await redis_fixed_window_backend.can_next("test_fixed_window", rule=rule)  # type: ignore
            assert await redis_fixed_window_backend.expected_time("test_fixed_window", rule=rule) == 10  # type: ignore
            await redis_fixed_window_backend.can_next("test_fixed_window", rule=rule)  # type: ignore
            assert await redis_fixed_window_backend.expected_time("test_fixed_window", rule=rule) == 20  # type: ignore
            redis_token_bucket_backend: RedisTokenBucketBackend = RedisTokenBucketBackend(redis_helper)
            await redis_token_bucket_backend.can_next("test_token_bucket", rule=rule)  # type: ignore
            assert (
                9 <= await redis_token_bucket_backend.expected_time("test_token_bucket", rule=rule) <= 10
            )  # type: ignore
            await redis_token_bucket_backend.can_next("test_token_bucket", rule=rule)  # type: ignore
            assert await redis_fixed_window_backend.expected_time("test_token_bucket", rule=rule) == 20  # type: ignore
            redis_cell_backend: RedisCellBackend = RedisCellBackend(redis_helper)
            await redis_cell_backend.can_next("test_redis_cell", rule=rule)  # type: ignore
            assert 9 <= await redis_cell_backend.expected_time("test_redis_cell", rule=rule) <= 10  # type: ignore
            await redis_cell_backend.can_next("test_redis_cell", rule=rule)  # type: ignore
            assert await redis_cell_backend.expected_time("test_redis_cell", rule=rule) == 20  # type: ignore
            await redis_helper.close()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(_test())
