import asyncio
import logging
from functools import wraps
from traceback import format_exception
from typing import Any, Callable, Coroutine, Dict, Optional, Union

from starlette.concurrency import run_in_threadpool

__all__ = ["stop_task", "background_task"]

FuncT = Callable[[], None]
AsyncFuncT = Callable[[], Coroutine[Any, Any, None]]


future_dict: Dict[str, asyncio.Future] = {}


class Task(object):
    def __init__(
        self,
        func: Union[AsyncFuncT, FuncT],
        seconds: Optional[float] = None,
        key: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        max_retry: Optional[int] = None,
    ) -> None:
        self.func: Union[AsyncFuncT, FuncT] = func
        self.seconds: Optional[float] = seconds
        self.key: str = key or func.__name__
        self.logger: Optional[logging.Logger] = logger
        self.max_retry: Optional[int] = max_retry

    async def real_run_job(self) -> None:
        retry_cnt = 0
        while self.max_retry is None or retry_cnt < self.max_retry:
            try:
                if asyncio.iscoroutinefunction(self.func):
                    await func()  # type: ignore
                else:
                    await run_in_threadpool(self.func)
                break
            except asyncio.CancelledError:
                pass
            except Exception as e:
                format_e = "".join(format_exception(type(e), e, e.__traceback__))
                if self.logger is not None:
                    self.logger.error(format_e)
                else:
                    logging.error(format_e)
                retry_cnt += 1
            await asyncio.sleep(retry_cnt * retry_cnt)

    async def task_loop(self) -> None:
        while True:
            future: Optional[asyncio.Future] = future_dict.get(self.key, None)
            if future is not None:
                if future.cancelled():
                    future.cancel()
                elif not future.done():
                    await asyncio.sleep(1)
                    continue

            future = asyncio.ensure_future(self.real_run_job())
            future_dict[self.key] = future
            if self.seconds:
                await asyncio.sleep(self.seconds)
            else:
                break


def background_task(
    *,
    seconds: Optional[float] = None,
    key: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
    max_retry: Optional[int] = None,
) -> Callable[[Union[FuncT, AsyncFuncT]], AsyncFuncT]:
    """
    seconds: If seconds is not empty, the task will be executed every `n` seconds,
     otherwise the task will be executed only once
    key: task key, if key is empty, key is func name
    logger: python logging logger
    max_retry: If max_retry is not empty, the number of task cycles will be limited
    """

    def decorator(func: Union[AsyncFuncT, FuncT]) -> AsyncFuncT:
        @wraps(func)
        async def wrapped() -> None:
            task: Task = Task(func, seconds, key, logger, max_retry)
            asyncio.ensure_future(task.task_loop())

        return wrapped

    return decorator


def _stop_task(key: str, future: asyncio.Future) -> None:
    if not future.cancelled():
        future.cancel()
        logging.info(f"stop task:{key}")
    elif future.done():
        logging.warning(f"task:{key} already stop")
    else:
        logging.warning(f"{key} can't stop")


def stop_task(key: Optional[str] = None) -> None:
    if key:
        if key in future_dict:
            future = future_dict[key]
            _stop_task(key, future)
    else:
        for key, future in future_dict.items():
            _stop_task(key, future)
