import logging
from abc import ABC
from typing import Dict, List, Optional

from fastapi_tools.base.redis_helper import RedisHelper
from fastapi_tools.limit.backend.base import BaseLimitBackend
from fastapi_tools.limit.rule import Rule


class BaseRedisBackend(BaseLimitBackend, ABC):

    def __init__(
            self,
            backend: 'RedisHelper',
            token_num: Optional[int] = None,
            block_time: Optional[int] = None,
            max_token: int = 100
    ):
        self._token_num: int = token_num if token_num else max_token
        self._max_token: int = max_token
        self._block_time: Optional[int] = block_time
        self._backend: 'RedisHelper' = backend


class FixedWindowBackend(BaseRedisBackend):
    async def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        block_time_key: str = key + ':block_time'
        block_time = await self._backend.redis_pool.get(block_time_key)
        if block_time:
            return False
        access_num: int = await self._backend.redis_pool.incr(key)
        if access_num == 1:
            await self._backend.redis_pool.expire(key, rule.gen_rate())

        max_token: int = rule.max_token if rule.max_token else self._max_token
        can_requests: bool = not access_num > max_token
        if not can_requests:
            bucket_block_time: int = rule.block_time if rule.block_time else self._block_time
            await self._backend.redis_pool.set(block_time_key, bucket_block_time, expire=bucket_block_time)
        return can_requests

    async def expected_time(self, key: str, rule: Rule, token_num=1) -> float:
        block_time_key: str = key + ':block_time'
        block_time = await self._backend.redis_pool.get(block_time_key)
        if block_time:
            return await self._backend.redis_pool.ttl(block_time_key)

        result = await self._backend.redis_pool.get(key)
        if result is None:
            return 0

        max_token: int = rule.max_token if rule.max_token else self._max_token
        if result < max_token:
            return 0
        return await self._backend.redis_pool.ttl(key)


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
        max_token: int = rule.max_token if rule.max_token else self._max_token
        bucket_token_num: int = rule.token_num if rule.token_num else self._token_num
        result: List[int] = await self._backend.execute(
            'CL.THROTTLE', key, max_token, bucket_token_num, rule.gen_token, rule.gen_second(), token_num
        )
        return result

    async def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        block_time_key: str = key + ':block_time'
        block_time = await self._backend.redis_pool.get(block_time_key)
        if block_time:
            return False
        result: List[int] = await self._call_cell(key, rule, token_num)
        can_requests: bool = bool(result[0])
        if not can_requests:
            bucket_block_time: int = rule.block_time if rule.block_time else self._block_time
            await self._backend.redis_pool.set(block_time_key, bucket_block_time, expire=bucket_block_time)
        return can_requests

    async def expected_time(self, key: str, rule: Rule, token_num=0) -> float:

        if token_num:
            logging.warning(
                f'Sorry, {self.__class__.__name__}.expected_time not support token_num > 0, token_num will be set 0'
            )
        result: List[int] = await self._call_cell(key, rule, 0)
        return float(max(result[3], 0))
