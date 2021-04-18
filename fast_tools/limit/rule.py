from datetime import timedelta
from typing import Optional


class Rule(object):
    def __init__(
        self,
        # gen_second param
        second: int = 0,
        minute: int = 0,
        hour: int = 0,
        day: int = 0,
        week: int = 0,
        # token config
        max_token_num: int = 100,  # Maximum number of tokens per bucket
        gen_token_num: int = 1,  # The number of tokens generated per unit time
        init_token_num: Optional[int] = None,  # The initial number of tokens in the bucket
        group: Optional[str] = None,
        block_time: Optional[int] = None,
    ):
        self.week: int = week
        self.day: int = day
        self.hour: int = hour
        self.minute: int = minute
        self.second: int = second

        self.gen_token_num: int = gen_token_num
        self.max_token_num: int = max_token_num

        self.group: Optional[str] = group
        self.block_time: Optional[int] = block_time

        if not init_token_num or init_token_num > self.max_token_num:
            self.init_token_num: int = self.max_token_num
        else:
            self.init_token_num = init_token_num

        # How long does it take to generate token
        self.total_second: float = timedelta(
            weeks=self.week, days=self.day, hours=self.hour, minutes=self.minute, seconds=self.second
        ).total_seconds()

        # total_second: 60 gen_token: 1  = 1 req/m
        # total_second: 1  gen_token: 1000 = 1000 req/s = 1 req/ms
        self.rate: float = self.gen_token_num / self.total_second
