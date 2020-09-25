import aioredis
import asyncio
from fastapi_tools.base import RedisHelper


async def test_redis_helper():
    redis: 'RedisHelper' = RedisHelper(
        await aioredis.create_pool('redis://localhost', minsize=1, maxsize=10, encoding='utf-8')
    )
    test_key: str = 'test_key'
    test_value: str = 'test_value'

    value = await redis.execute('set', test_key, test_value)
    print(value)
    assert value == 'OK'

    value = await redis.execute('get', test_key)
    assert value == test_value
    value = await redis.pipeline([
        ('del', test_key),
        ('set', test_key, test_value),
        ('get', test_key),
        ('del', test_key)
    ])
    print(value)
    assert isinstance(value, list)


asyncio.run(test_redis_helper())
