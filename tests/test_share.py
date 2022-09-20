import asyncio
from typing import Coroutine, List

import pytest

from example.share import delay_print
from fast_tools.share import Share

pytestmark = pytest.mark.asyncio
share: "Share" = Share()


class TestShare:
    async def test_do(self) -> None:
        task_list: "List[Coroutine]" = [share.do("test_do", delay_print, args=[i]) for i in [1, 2, 3, 4, 5, 6, 7, 8, 9]]
        done, _ = await asyncio.wait(task_list)
        assert len({future.result() for future in done}) == 1

    async def test_wrapper_do(self) -> None:
        @share.wrapper_do()
        async def test_wrapper_do(num: int) -> int:
            return await delay_print(num)

        task_list: "List[Coroutine]" = [test_wrapper_do(i) for i in [21, 22, 23, 24, 25, 26, 27, 28, 29]]
        done, _ = await asyncio.wait(task_list)
        assert len({future.result() for future in done}) == 1

    async def test_class_wrapper_do(self) -> None:
        class TestClassWrapperDo(object):
            @share.wrapper_do()
            async def delay_print(self, num: int) -> int:
                return await delay_print(num)

        test_class_wrapper_do_1: "TestClassWrapperDo" = TestClassWrapperDo()
        test_class_wrapper_do_2: "TestClassWrapperDo" = TestClassWrapperDo()

        task_list: "List[Coroutine]" = [
            test_class_wrapper_do_1.delay_print(i) for i in [21, 22, 23, 24, 25, 26, 27, 28, 29]
        ]
        task_list.extend(test_class_wrapper_do_2.delay_print(i) for i in [11, 12, 13, 14, 15, 16, 17, 18, 19])
        done, _ = await asyncio.wait(task_list)
        assert len({future.result() for future in done}) == 2

    async def test_cancel(self) -> None:
        async def cancel() -> None:
            await asyncio.sleep(0.1)
            share.cancel("test_cancel")

        task_list: "List[Coroutine]" = [
            share.do("test_cancel", delay_print, args=[i]) for i in [11, 12, 13, 14, 15, 16, 17, 18, 19]
        ]
        task_list.append(cancel())

        with pytest.raises(asyncio.CancelledError):
            done, _ = await asyncio.wait(task_list)
            for future in done:
                future.result()
