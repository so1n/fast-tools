from typing import Awaitable, Callable, Optional, Tuple, Union

from starlette.requests import Request

DEFAULT_STATUS_CODE: int = 429
DEFAULT_CONTENT: str = "This user has exceeded an allotted request count. Try again later."

RULE_FUNC_RETURN_TYPE = Tuple[str, Optional[str]]
RULE_FUNC_TYPE = Callable[[Request], Union[RULE_FUNC_RETURN_TYPE, Awaitable[RULE_FUNC_RETURN_TYPE]]]
