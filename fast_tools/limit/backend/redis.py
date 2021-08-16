import time
from abc import ABC
from typing import Any, Awaitable, Callable, Coroutine, List, Optional, Union

from fast_tools.base.redis_helper import RedisHelper
from fast_tools.limit.backend.base import BaseLimitBackend
from fast_tools.limit.rule import Rule


class BaseRedisBackend(BaseLimitBackend, ABC):
    def __init__(self, backend: "RedisHelper"):
        self._backend: "RedisHelper" = backend

    async def _block_time_handle(self, key: str, rule: Rule, func: Callable[..., Awaitable[bool]]) -> bool:
        block_time_key: str = f"{key}:block_time"
        bucket_block_time: Optional[int] = rule.block_time

        if bucket_block_time is not None and await self._backend.exists(block_time_key):
            return False

        can_next: bool = await func()
        if not can_next and bucket_block_time is not None:
            await self._backend.client.set(block_time_key, bucket_block_time, expire=bucket_block_time)

        return can_next


class RedisFixedWindowBackend(BaseRedisBackend):
    def can_next(self, key: str, rule: Rule, token_num: int = 1) -> Union[bool, Coroutine[Any, Any, bool]]:
        key = f"{self._backend.namespace}:{key}"

        async def _can_next() -> bool:
            """
            In the current time(rule.get_second()) window,
             whether the existing value(access_num) exceeds the maximum value(rule.gen_token_num)
            """
            access_num: int = await self._backend.client.incr(key)
            if access_num == 1:
                await self._backend.client.expire(key, rule.total_second)

            can_next: bool = not (access_num > rule.gen_token_num)
            return can_next

        return self._block_time_handle(key, rule, _can_next)

    def expected_time(self, key: str, rule: Rule) -> Union[float, Coroutine[Any, Any, float]]:
        key = f"{self._backend.namespace}:{key}"

        async def _expected_time() -> float:
            block_time_key: str = key + ":block_time"
            block_time = await self._backend.client.get(block_time_key)
            if block_time:
                return await self._backend.client.ttl(block_time_key)

            token_num_str: Optional[str] = await self._backend.client.get(key)
            if token_num_str is None:
                return 0
            else:
                if int(token_num_str) < rule.gen_token_num:
                    return 0
            return await self._backend.client.ttl(key)

        return _expected_time()


class RedisCellBackend(BaseRedisBackend):
    """
    use redis-cell module
    learn more:https://github.com/brandur/redis-cell

    input: CL.THROTTLE user123 15 30 60 1
        # param  |  desc
        # user123 key
        # 15 maxburst
        # 30 token
        # 60 seconds
        # 1 apply 1token
    output:
        1) (integer) 0        # is allowed
        2) (integer) 16       # total bucket num
        3) (integer) 15       # the remaining limit of the key.
        4) (integer) -1       # the number of seconds until the user should retry,
                              #   and always -1 if the action was allowed.
        5) (integer) 2        # The number of seconds until the limit will reset to its maximum capacity
    """

    async def _call_cell(self, key: str, rule: Rule, token_num: int = 1) -> List[int]:
        result: List[int] = await self._backend.execute(
            "CL.THROTTLE", key, rule.max_token_num - 1, rule.gen_token_num, int(rule.total_second), token_num
        )
        return result

    async def can_next(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        key = f"{self._backend.namespace}:{key}"

        async def _can_next() -> bool:
            result: List[int] = await self._call_cell(key, rule, token_num)
            can_next: bool = not bool(result[0])
            await self._backend.client.expire(key, rule.total_second)
            return can_next

        return await self._block_time_handle(key, rule, _can_next)

    async def expected_time(self, key: str, rule: Rule) -> float:
        key = f"{self._backend.namespace}:{key}"

        block_time_key: str = key + ":block_time"
        block_time = await self._backend.client.get(block_time_key)
        if block_time:
            return await self._backend.client.ttl(block_time_key)

        result: List[int] = await self._call_cell(key, rule, 0)
        if result[2]:
            return 0
        else:
            return result[4] / rule.gen_token_num


class RedisTokenBucketBackend(BaseRedisBackend):
    _lua_script = """
local key = KEYS[1]
local current_time = tonumber(ARGV[1])
local interval_per_token = tonumber(ARGV[2])
local max_token = tonumber(ARGV[3])
local init_token = tonumber(ARGV[4])
local tokens
local bucket = redis.call("hmget", key, "last_time", "last_token")
local last_time= bucket[1]
local last_token = bucket[2]
if last_time == false or last_token == false then
    tokens = init_token
    redis.call('hset', key, 'last_time', current_time)
else
    local this_interval = current_time - tonumber(last_time)
    if this_interval > 1 then
        local tokens_to_add = math.floor(this_interval * interval_per_token)
        tokens = math.min(last_token + tokens_to_add, max_token)
        redis.call('hset', key, 'last_time', current_time)
    else
        tokens = tonumber(last_token)
    end
end
if tokens < 1 then
    redis.call('hset', key, 'last_token', tokens)
    return -1
else
    tokens = tokens - 1
    redis.call('hset', key, 'last_token', tokens)
    return tokens
end
    """

    async def can_next(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        key = f"{self._backend.namespace}:{key}"

        async def _can_next() -> bool:
            now_token: int = await self._backend.client.eval(
                self._lua_script, keys=[key], args=[time.time(), rule.rate, rule.max_token_num, rule.init_token_num]
            )
            await self._backend.client.expire(key, rule.total_second)
            return now_token >= 0

        return await self._block_time_handle(key, rule, _can_next)

    async def expected_time(self, key: str, rule: Rule) -> float:
        key = f"{self._backend.namespace}:{key}"

        block_time_key: str = key + ":block_time"
        block_time = await self._backend.client.get(block_time_key)
        if block_time:
            return await self._backend.client.ttl(block_time_key)
        last_time_str: Optional[str] = await self._backend.client.hget(key, "last_time")
        last_token_str: Optional[str] = await self._backend.client.hget(key, "last_token")
        if last_time_str is None or last_token_str is None:
            return 0
        if int(last_token_str) > 0:
            return 0
        diff_time: float = time.time() - float(last_time_str)
        if diff_time > 0:
            return (rule.total_second - diff_time) / rule.gen_token_num
        return 0
