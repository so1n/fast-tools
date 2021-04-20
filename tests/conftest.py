import asyncio
from typing import Any, Generator

import pytest
from pytest_mock import MockFixture


class AnyStringWith(str):
    def __eq__(self, other: Any) -> bool:
        return self in other


class StringNotIn(str):
    def __eq__(self, other: Any) -> bool:
        return self not in other


@pytest.fixture()
def fix_starlette_bug(mocker: MockFixture) -> Generator[None, None, None]:
    # fix staelette.testclient get_event_loop status is close
    def get_event_loop() -> asyncio.AbstractEventLoop:
        try:
            loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
        except RuntimeError as e:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    mocker.patch("asyncio.get_event_loop").return_value = get_event_loop()
    yield None
