import asyncio
from typing import Coroutine, List

import pytest

from example.share import delay_print
from fast_tools.share import Share

pytestmark = pytest.mark.asyncio
share: "Share" = Share()


class TestShare:
    async def test_do(self) -> None:
        task_list = [share.do("test_do", delay_print, args=[i]) for i in [1, 2, 3, 4, 5, 6, 7, 8, 9]]
        done, _ = await asyncio.wait(task_list)
        assert len({future.result() for future in done}) == 1

    async def test_wrapper_do(self) -> None:
        @share.wrapper_do()
        async def test_wrapper_do(num: int) -> int:
            return await delay_print(num)

        task_list = [test_wrapper_do(i) for i in [21, 22, 23, 24, 25, 26, 27, 28, 29]]
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

    async def test_cancel_in_aio(self) -> None:
        async def cancel_in_aio() -> None:
            await asyncio.sleep(0.1)
            share.cancel("test cancel msg")

        task_list: "List[Coroutine]" = [
            share.do("test_cancel", delay_print, args=[i]) for i in [11, 12, 13, 14, 15, 16, 17, 18, 19]
        ]
        task_list.append(cancel_in_aio())

        t_list = [asyncio.Task(t) for t in task_list]
        await asyncio.sleep(0.2)
        result = []
        for t in t_list:
            if t._coro.__name__ == "cancel_in_aio":  # type: ignore
                continue
            try:
                await t
            except asyncio.CancelledError as e:
                result.append(str(e))

        for i in result:
            assert i == "test cancel msg"

    async def test_share_exc(self) -> None:
        async def must_cancel_coro() -> None:
            await asyncio.sleep(0)
            raise asyncio.CancelledError("must cancel")

        task_list = [share.do("test_cancel", must_cancel_coro) for _ in range(10)]
        t_list = [asyncio.Task(t) for t in task_list]
        await asyncio.sleep(0.2)
        result = []
        for t in t_list:
            try:
                await t
                result.append(1)
            except asyncio.CancelledError:
                result.append(0)
        assert sum(result) == 0

    async def test_forget(self) -> None:
        task_list = [share.do("test_do", delay_print, args=[i]) for i in [1, 2, 3, 4, 5, 6, 7, 8, 9]]
        a_task = asyncio.Task(asyncio.wait(task_list))
        await asyncio.sleep(0.1)
        share.forget("test_do")
        task_list = [share.do("test_do", delay_print, args=[i]) for i in [11, 12, 13, 14, 15, 16, 17, 18, 19]]
        b_task = asyncio.Task(asyncio.wait(task_list))
        await asyncio.sleep(0.1)

        a_set = {future.result() for future in (await a_task)[0]}
        b_set = {future.result() for future in (await b_task)[0]}
        assert len(a_set) == 1 and len(b_set) == 1
        assert a_set.pop() != b_set.pop()
