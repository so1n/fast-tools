import asyncio
import pytest
from fast_tools.base import utils

pytestmark = pytest.mark.asyncio


class TestUtil:
    async def test_util(self) -> None:
        await utils.as_first_completed([asyncio.sleep(1), asyncio.sleep(2)])

        with pytest.raises(TypeError) as e:
            await utils.as_first_completed([asyncio.sleep(1), utils])  # type: ignore

        e.value.args[0].startswith("expect a list of futures")

        with pytest.raises(asyncio.TimeoutError):
            await utils.as_first_completed([asyncio.sleep(5), asyncio.sleep(50)], timeout=1)
