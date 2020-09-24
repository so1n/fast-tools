import time
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional
from fastapi_tools.limit.rule import Rule
from .base import BaseLimitBackend


@dataclass
class Bucket(object):
    rate: int
    token_num: int
    max_token: int
    timestamp: float
    block_time: Optional[float] = None


class TokenBucket(BaseLimitBackend):

    def __init__(
            self,
            token_num: Optional[int] = None,
            block_time: Optional[int] = None,
            max_token: int = 100
    ):
        self._token_num: int = token_num if token_num else max_token
        self._max_token: int = max_token
        self._block_time: Optional[int] = block_time
        self._cache_dict: Dict[str, 'Bucket'] = {}

    def _gen_bucket(self, rule: Rule) -> 'Bucket':
        bucket_kwargs: Dict[str, Any] = {
            'token_num': self._token_num,
            'max_token': self._max_token,
            'block_time': self._block_time
        }
        bucket_kwargs.update(rule.gen_kwargs())
        return Bucket(**bucket_kwargs)

    def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        bucket: 'Bucket' = self._cache_dict.get(key, self._gen_bucket(rule))
        now_timestamp: float = time.time()
        if bucket.block_time and bucket.block_time and (now_timestamp - bucket.block_time) > bucket.block_time:
            return False

        result: bool = False
        if token_num <= self._get_tokens(bucket):
            bucket.token_num -= token_num
            result = True
        bucket.block_time = now_timestamp
        self._cache_dict[key] = bucket
        return result

    def expected_time(self, key: str, rule: Rule, token_num=1) -> float:
        bucket: 'Bucket' = self._cache_dict.get(key, self._gen_bucket(rule))
        now_token_num: int = self._get_tokens(bucket)
        diff_token: int = now_token_num - token_num

        self._cache_dict[key] = bucket
        if diff_token > 0:
            return 0
        else:
            return abs(diff_token) / bucket.rate

    @staticmethod
    def _get_tokens(bucket: 'Bucket') -> int:
        if bucket.token_num < bucket.max_token:
            now: float = time.time()
            diff_time: float = now - bucket.timestamp
            gen_token = int(diff_time * bucket.rate)
            bucket.timestamp = now - (diff_time - int(diff_time))
            bucket.token_num = min(bucket.max_token, bucket.token_num + gen_token)
        return bucket.token_num

    def get_token_num(self, key: str) -> int:
        return self._cache_dict[key].token_num


class ThreadingTokenBucket(BaseLimitBackend):

    def __init__(
            self,
            token_num: Optional[int] = None,
            block_time: Optional[int] = None,
            max_token: int = 100
    ):
        super().__init__(token_num, block_time, max_token)
        self._lock = threading.Lock()

    def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        with self._lock:
            return super().can_requests(key, rule, token_num)

    def expected_time(self, key: str, rule: Rule, token_num=1) -> float:
        with self._lock:
            return super().expected_time(key, rule, token_num)


if __name__ == '__main__':
    token_bucket: TokenBucket = TokenBucket(1)
    test_rule: Rule = Rule(second=1, token_num=50, max_token=100)
    test_key: str = 'test'
    print(token_bucket.expected_time(test_key, test_rule))
    print(token_bucket.get_token_num(test_key))
    token_bucket.can_requests(test_key, test_rule)
    print(token_bucket.expected_time(test_key, test_rule))
    print(token_bucket.get_token_num(test_key))
