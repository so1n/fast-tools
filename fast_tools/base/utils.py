import asyncio
from typing import Any, Coroutine, List, Optional, Set, Union

NAMESPACE: str = "fast-tools"


async def as_first_completed(
    future_list: List[Union[Coroutine, asyncio.Future]], *, timeout: Optional[int] = None
) -> None:
    for future in future_list:
        if not (asyncio.isfuture(future) or asyncio.iscoroutine(future)):
            raise TypeError(f"expect a list of futures, not {type(future).__name__}")
    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    todo_future_set: Set[asyncio.Future] = {asyncio.ensure_future(f, loop=loop) for f in set(future_list)}
    done_queue: asyncio.Queue = asyncio.Queue(loop=loop)
    timeout_handle = None

    def _on_timeout() -> None:
        for f in todo_future_set:
            f.remove_done_callback(_on_completion)
            done_queue.put_nowait(None)  # Queue a dummy value for _wait_for_one().
        todo_future_set.clear()  # Can't do todo.remove(f) in the loop.

    def _on_completion(f: asyncio.Future) -> None:
        if not todo_future_set:
            return  # _on_timeout() was here first.
        todo_future_set.remove(f)
        done_queue.put_nowait(f)
        if not todo_future_set and timeout_handle is not None:
            timeout_handle.cancel()

    async def _wait_for_one() -> Any:
        f = await done_queue.get()
        if f is None:
            # Dummy value from _on_timeout().
            raise asyncio.TimeoutError
        return f.result()  # May raise f.exception().

    for f in todo_future_set:
        f.add_done_callback(_on_completion)
    if todo_future_set and timeout is not None:
        timeout_handle = loop.call_later(timeout, _on_timeout)

    try:
        return await _wait_for_one()
    finally:
        for f in todo_future_set:
            if f.cancelled():
                f.cancel()
            if timeout_handle and timeout_handle.cancelled():
                timeout_handle.cancel()
