import asyncio
from concurrent import futures
from typing import Any, Callable, Optional, Type


class _BoundClass(object):
    pass


class LazyProperty:
    """Cache field computing resources
    >>> class Demo:
    ...     @LazyProperty()
    ...     def value(self, value):
    ...         return value * value
    """

    def __call__(self, func: Callable) -> Callable:
        key: str = f"{self.__class__.__name__}_{id(func)}_future"
        _bound_class: _BoundClass = _BoundClass()
        if not asyncio.iscoroutinefunction(func):

            def wrapper(*args: Any, **kwargs: Any) -> Any:
                if args and args[0].__class__.__name__ in func.__qualname__:
                    class_: Any = args[0]
                else:
                    class_ = _bound_class
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
                if args and args[0].__class__.__name__ in func.__qualname__:
                    class_: Any = args[0]
                else:
                    class_ = _bound_class
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
