import time
from typing import AsyncGenerator, Dict

import aioredis  # type: ignore
import pytest

from fast_tools.base.redis_helper import Lock, LockError, RedisHelper, errors

pytestmark = pytest.mark.asyncio


@pytest.fixture()
async def redis_helper() -> AsyncGenerator[RedisHelper, None]:
    redis_helper: RedisHelper = RedisHelper()
    try:
        redis_helper.init(
            await aioredis.create_pool("redis://localhost", minsize=1, maxsize=10, encoding="utf-8"),
        )
        yield redis_helper
    except Exception:
        await redis_helper.close()


class TestRedisHelper:
    def test_not_call_init(self) -> None:
        with pytest.raises(ConnectionError) as e:
            RedisHelper().client
        assert e.value.args[0] == "Not init RedisHelper, please run RedisHelper.init"

    async def test_init(self) -> None:
        redis_helper: RedisHelper = RedisHelper()
        # init error pool
        with pytest.raises(ConnectionError) as e:
            redis_helper.init(None)  # type: ignore
        assert e.value.args[0] == "conn_pool is none"

        # init success
        redis_helper.init(
            await aioredis.create_pool("redis://localhost", minsize=1, maxsize=10, encoding="utf-8"), namespace="test"
        )
        assert redis_helper.namespace == "test"

        # repeat call
        with pytest.raises(ConnectionError) as e:
            redis_helper.init(
                await aioredis.create_pool("redis://localhost", minsize=1, maxsize=10, encoding="utf-8"),
            )
        assert e.value.args[0].startswith("Init error, RedisHelper already init")

        # close redis pool
        await redis_helper.close()
        assert redis_helper.closed()

        # reinitialize
        redis_helper.init(
            await aioredis.create_pool("redis://localhost", minsize=1, maxsize=10, encoding="utf-8"),
        )
        assert not redis_helper.closed()

    async def test_redis_dict(self, redis_helper: RedisHelper) -> None:
        test_dict: Dict[str, int] = {"a": 1, "b": 2, "c": 3}
        await redis_helper.set_dict("test", test_dict, 10)
        assert await redis_helper.get_dict("test") == test_dict
        assert await redis_helper.execute("ttl", "test") <= 10
        assert await redis_helper.del_key("test")

    async def test_del_key(self, redis_helper: RedisHelper) -> None:
        await redis_helper.execute("set", "test_key", "value")
        await redis_helper.del_key("test_key")
        assert await redis_helper.execute("get", "test_key") is None

        await redis_helper.execute("set", "test_key", "value")
        await redis_helper.del_key("test_key", 10)
        assert await redis_helper.execute("ttl", "test") <= 10
        assert await redis_helper.del_key("test_key")

    async def test_pipeline(self, redis_helper: RedisHelper) -> None:
        await redis_helper.pipeline([("set", "test_key", "value"), ("expire", "test_key", 10)])
        assert await redis_helper.execute("ttl", "test_key") <= 10
        await redis_helper.pipeline([("set", "test_key", "value"), ("del", "test_key")])
        assert not await redis_helper.execute("get", "test_key")

        with pytest.raises(errors.PipelineError) as e:
            await redis_helper.pipeline([("set", "test_key")])

        assert e.value.args[0].startswith("PipelineError errors:")

    async def test_hash(self, redis_helper: RedisHelper) -> None:
        assert not await redis_helper.hget_dict("test", "key1")
        test_dict: Dict[str, int] = {str(i): i for i in range(1000)}

        await redis_helper.hmset_dict("test", test_dict)
        assert await redis_helper.hget_dict("test", "1") == 1
        assert await redis_helper.hmget_dict("test") == test_dict
        assert await redis_helper.execute("del", "test")

        assert not await redis_helper.hmget_dict("test")

    async def test_execute(self) -> None:
        redis_helper: RedisHelper = RedisHelper()
        with pytest.raises(ConnectionError) as e:
            await redis_helper.execute("set", "test", "value")

        assert e.value.args[0] == "Not init RedisHelper, please run RedisHelper.init"

        redis_helper.init(
            await aioredis.create_pool("redis://localhost", minsize=1, maxsize=10, encoding="utf-8"),
        )
        await redis_helper.execute("set", "test", "value")
        with pytest.raises(errors.RedisError):
            await redis_helper.hmget_dict("test")

        await redis_helper.execute("del", "test")
        await redis_helper.close()

    async def test_lock(self, redis_helper: RedisHelper) -> None:
        lock_1: Lock = redis_helper.lock("test_key")
        lock_2: Lock = redis_helper.lock("test_key")
        await lock_1.acquire()

        assert not await lock_2.do_acquire(str(int(time.time()) + 10))

        assert await lock_1.locked()
        assert await lock_2.locked()

        with pytest.raises(LockError) as e:
            await lock_2.release()

        assert e.value.args[0] == "Cannot release an unlocked lock"

        with pytest.raises(LockError) as e:
            await lock_2.do_release(int(time.time()))

        assert e.value.args[0] == "Cannot release a lock that's no longer owned"

        assert not await lock_2.acquire(1)
        await lock_1.release()
        assert not await lock_1.locked()
