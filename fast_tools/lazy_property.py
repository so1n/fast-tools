import asyncio
from concurrent import futures
from typing import Any, Callable, Optional, Type


class _BoundClass(object):
    pass


_bound_class: _BoundClass = _BoundClass()


class LazyProperty:
    """Cache field computing resources
    >>> class Demo:
    ...     @LazyProperty(is_class_func=True)
    ...     def value(self, value):
    ...         return value * value
    """

    def __init__(self, is_class_func: bool = False):
        self._is_class_func: bool = is_class_func

    def __call__(self, func: Callable) -> Callable:
        key: str = f"{self.__class__.__name__}_{id(func)}_future"
        if not asyncio.iscoroutinefunction(func):

            def wrapper(*args: Any, **kwargs: Any) -> Any:
                class_: Any = args[0] if self._is_class_func else _bound_class
                future: Optional[futures.Future] = getattr(class_, key, None)
                if not future:
                    future = futures.Future()
                    result: Any = func(*args, **kwargs)
                    future.set_result(result)
                    setattr(class_, key, future)
                    return result
                return future.result()

            return wrapper
        else:

            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                class_: Any = args[0] if self._is_class_func else _bound_class
                future: Optional[asyncio.Future] = getattr(class_, key, None)
                if not future:
                    future = asyncio.Future()
                    result: Any = await func(*args, **kwargs)
                    future.set_result(result)
                    setattr(class_, key, future)
                    return result
                return future.result()

            return async_wrapper


class LazyPropertyNoParam:
    def __init__(self, func: Callable):
        self.func: Callable = func
        self.cached_name: str = "cached" + func.__name__

    def __get__(self, obj: object, cls: Type[object]) -> Any:
        future: Optional["futures.Future"] = getattr(obj, self.cached_name, None)

        if future:
            return lambda: future.result()
        else:
            future = futures.Future()
            setattr(obj, self.cached_name, future)
            try:
                res: Any = self.func(obj)
                future.set_result(res)
                return lambda: res
            except Exception as e:
                future.set_exception(e)
                raise e


class LazyAsyncPropertyNoParam:
    def __init__(self, func: Callable):
        self.func: Callable = func
        self.cached_name: str = "cached_" + func.__name__

    def __get__(self, obj: object, cls: Type[object]) -> Any:
        future: Optional["asyncio.Future"] = getattr(obj, self.cached_name, None)

        if future:
            return lambda: future
        else:
            future = asyncio.Future()
            setattr(obj, self.cached_name, future)
            return lambda: self._execute_future(future, obj)

    async def _execute_future(self, future: asyncio.Future, obj: object) -> Any:
        try:
            res = await self.func(obj)
            future.set_result(res)
        except Exception as e:
            future.set_exception(e)
        return await future
