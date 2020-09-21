from dataclasses import dataclass
from datetime import timedelta


@dataclass
class Rule(object):
    second: int = 0
    minute: int = 0
    hour: int = 0
    day: int = 0
    week: int = 0

    max_token: int = 100
    gen_token: int = 1

    def get_second(self) -> float:
        return timedelta(
            weeks=self.week,
            days=self.day,
            hours=self.hour,
            minutes=self.minute,
            seconds=self.second
        ).total_seconds()

    def get_token(self) -> int:
        return int(self.gen_token / self.get_second())
