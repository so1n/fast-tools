from fastapi_tools.limit.rule import Rule


class BaseLimitBackend(object):

    def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        raise NotImplementedError

    def expected_time(self, key: str, rule: Rule, token_num=1) -> float:
        raise NotImplementedError
