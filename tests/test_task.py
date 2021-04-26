import asyncio
import pytest
from fast_tools.task import background_task, stop_task


pytestmark = pytest.mark.asyncio


class TestTask:
    async def test_task(self) -> None:
        count: int = 0

        @background_task(seconds=0.2)
        async def _task() -> None:
            nonlocal count
            count += 1

        assert count == 0
        await _task()
        await asyncio.sleep(0.5)
        assert count >= 2
        stop_task()
        await asyncio.sleep(0.1)
