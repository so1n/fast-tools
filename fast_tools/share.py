import asyncio
import random
from functools import wraps
from typing import Any, Callable, Coroutine, Dict, Generic, Optional, Tuple, TypeVar, Union

from typing_extensions import ParamSpec

__all__ = ("Share", "Token")
_Tp = TypeVar("_Tp")


class Token(Generic[_Tp]):
    """Result and status of managed actions"""

    def __init__(self, key: Any):
        self.is_forget = False
        self._key: Any = key
        self._future: Optional[asyncio.Future[_Tp]] = None

    def can_do(self) -> bool:
        """Determine whether there is a future, if not, create a new future and return true, otherwise return false"""
        if not self._future:
            self._future = asyncio.Future()
            return True
        if self.is_forget:
            self.is_forget = False
            return True
        return False

    def is_done(self) -> bool:
        """Determine whether the execution is completed"""
        return self._future is not None and self._future.done()

    def cancel(self) -> bool:
        """Cancel the execution of the current action"""
        if self._future is not None and not self._future.done():
            if self._future.cancelled():
                self._future.cancel()
            else:
                self.set_result(asyncio.CancelledError())
            return True
        return False

    async def await_done(self) -> _Tp:
        """Wait for execution to end and return data"""
        if not self._future:
            raise RuntimeError(f"You should use Token<{self._key}>.can_do() before Token<{self._key}>.await_done()")
        if not self._future.done():
            await self._future
        return self._future.result()

    def set_result(self, result: Union[_Tp, Exception]) -> bool:
        """set data or exception"""
        if self._future and not self._future.done():
            if isinstance(result, Exception):
                self._future.set_exception(result)
            else:
                self._future.set_result(result)
            return True
        return False


_ShareKeyType = Union[Tuple[Any, ...], str]
P = ParamSpec("P")
R_T = TypeVar("R_T")


class Share(object):
    def __init__(self, rate: Optional[Tuple[int, int]] = None) -> None:
        if rate and rate[0] > rate[1]:
            raise ValueError(f"rate[0] should less than rate[1], but {rate[0]} > {rate[1]}")
        self._rate: Optional[Tuple[int, int]] = rate
        self._token_dict: Dict[_ShareKeyType, Token] = dict()

    def _get_token(self, key: _ShareKeyType) -> Token:
        """Get the token (if not, create a new one and return)"""
        if key not in self._token_dict:
            self._token_dict[key] = Token(key)
        return self._token_dict[key]

    def cancel(self, key: Optional[_ShareKeyType] = None) -> None:
        """Cancel the execution of the specified action, if the key is empty, cancel all"""
        if not key:
            for token in self._token_dict.values():
                token.cancel()
        else:
            self._token_dict[key].cancel()

    def forget(self, key: _ShareKeyType, force: bool = True) -> None:
        if key not in self._token_dict:
            raise KeyError(f"Token {key} not found")
        token = self._token_dict[key]
        if self._token_dict[key].is_done():
            raise RuntimeError(f"{token} is done")
        if force:
            self._token_dict.pop(key, None)
        else:
            token.is_forget = True

    async def _do_handle(
        self, key: _ShareKeyType, func: Callable[P, Coroutine[Any, Any, R_T]], args: P.args, kwargs: P.args
    ) -> R_T:
        token: Token = self._get_token(key)
        try:
            can_do = token.can_do()
            if not can_do and self._rate:
                can_do = random.randint(self._rate[0], self._rate[1]) == self._rate[0]
            if can_do:
                try:
                    # It doesn't matter if you have multiple requests,
                    # Token will ensure that only one request is executed
                    token.set_result(await func(*(args or ()), **(kwargs or {})))
                except Exception as e:
                    token.set_result(e)
            return await token.await_done()
        finally:
            self._token_dict.pop(key, None)

    def do(
        self,
        key: _ShareKeyType,
        func: Callable[P, Coroutine[Any, Any, R_T]],
        args: P.args = None,
        kwargs: P.kwargs = None,
    ) -> Coroutine[Any, Any, R_T]:
        return self._do_handle(key, func, args, kwargs)

    def wrapper_do(
        self, key: Optional[str] = None, only_include_class_param: bool = True, include_param: bool = False
    ) -> Callable:
        if only_include_class_param and include_param:
            raise ValueError("only_include_class_param and include_param can't be True at the same time")

        def wrapper(func: Callable[P, Coroutine[Any, Any, R_T]]) -> Callable[P, Coroutine[Any, Any, R_T]]:
            key_name: str = func.__qualname__ if key is None else key

            @wraps(func)
            async def wrapper_func(*args: P.args, **kwargs: P.kwargs) -> R_T:
                if include_param:
                    real_key: Tuple[Any, ...] = (key_name, tuple(args), tuple(kwargs.values()))
                else:
                    if only_include_class_param and args and args[0].__class__.__name__ in func.__qualname__:
                        real_key = (key_name + f":{id(args[0])}",)
                    else:
                        real_key = (key_name,)
                return await self._do_handle(real_key, func, args, kwargs)

            return wrapper_func

        return wrapper

    def __str__(self) -> str:
        return str(self._token_dict)
