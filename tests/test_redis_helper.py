from typing import Any, Dict

import aioredis  # type: ignore
import pytest

from fast_tools.base import RedisHelper


pytestmark = pytest.mark.asyncio


class TestRedisHelper:
    async def test_redis_helper(self) -> None:
        redis: "RedisHelper" = RedisHelper()
        redis.init(
            await aioredis.create_pool("redis://localhost", minsize=1, maxsize=10, encoding="utf-8")
        )
        test_key: str = "test_key"
        test_value: str = "test_value"
        test_dict_value: Dict[str, Any] = {test_key: test_value}

        value = await redis.execute("set", test_key, test_value)
        assert value == "OK"

        value = await redis.execute("get", test_key)
        assert value == test_value
        value = await redis.pipeline(
            [("del", test_key), ("set", test_key, test_value), ("get", test_key), ("del", test_key)]
        )
        assert isinstance(value, list)
        await redis.set_dict(test_key, test_dict_value, 360)
        assert test_dict_value == await redis.get_dict(test_key)

        await redis.hmset_dict("test_key_a", {"test_a": 1, "test_b": 2})
        assert await redis.hget_dict("test_key_a", "test_a") == 1
        assert await redis.hmget_dict("test_key_a") == {"test_a": 1, "test_b": 2}
        await redis.close()
