import time
from typing import Optional


class TokenBucket(object):

    def __init__(
            self,
            rate: int,
            token_num: Optional[int] = None,
            max_token: int = 100,
    ):
        self._rate: int = rate  # How many tokens are generated in one second
        self._token_num: int = token_num if token_num else max_token
        self._max_token: int = max_token
        self._timestamp: float = time.time()

    def can_consume(self, token_num: int = 1) -> bool:
        if token_num <= self._get_tokens():
            self._token_num -= token_num
            return True
        return False

    def expected_time(self, token_num=1) -> float:
        now_token_num: int = self._get_tokens()
        diff_token: int = now_token_num - token_num
        if diff_token > 0:
            return 0
        else:
            return abs(diff_token) / self._rate

    def _get_tokens(self) -> int:
        if self._token_num < self._max_token:
            now: float = time.time()
            diff_time: float = now - self._timestamp
            gen_token = int(diff_time * self._rate)
            self._timestamp = now - (diff_time - int(diff_time))
            self._token_num = min(self._max_token, self._token_num + gen_token)
        return self._token_num

    @property
    def token_num(self):
        return self._token_num


if __name__ == '__main__':
    token_bucket: TokenBucket = TokenBucket(1)
    print(token_bucket.token_num, token_bucket.expected_time(10))
    token_bucket.can_consume(100)
    print(token_bucket.token_num, token_bucket.expected_time(2))
