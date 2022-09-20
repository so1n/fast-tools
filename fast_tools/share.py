import asyncio
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Union

__all__ = ("Share", "Token")
_Tp = TypeVar("_Tp")


class Token(object):
    """Result and status of managed actions"""

    def __init__(self, key: str):
        self._key: str = key
        self._future: Optional[asyncio.Future] = None

    def can_do(self) -> bool:
        """Determine whether there is a future, if not, create a new future and return true, otherwise return false"""
        if not self._future:
            self._future = asyncio.Future()
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

    async def await_done(self) -> Optional[Any]:
        """Wait for execution to end and return data"""
        if not self._future:
            raise RuntimeError(f"You should use Token<{self._key}>.can_do() before Token<{self._key}>.await_done()")
        if not self._future.done():
            await self._future
        return self._future.result()

    def set_result(self, result: Any) -> bool:
        """set data or exception"""
        if self._future and not self._future.done():
            if isinstance(result, Exception):
                self._future.set_exception(result)
            else:
                self._future.set_result(result)
            return True
        return False


class Share(object):
    def __init__(self) -> None:
        self._future_dict: Dict[str, Token] = dict()

    def _get_token(self, key: str) -> Token:
        """Get the token (if not, create a new one and return)"""
        if key not in self._future_dict:
            token: "Token" = Token(key)
            self._future_dict[key] = token
        return self._future_dict[key]

    def cancel(self, key: Optional[str] = None) -> None:
        """Cancel the execution of the specified action, if the key is empty, cancel all"""
        if not key:
            for _, token in self._future_dict.items():
                token.cancel()
        else:
            self._future_dict[key].cancel()

    async def _token_handle(
        self, key: str, func: Callable, args: Optional[Union[list, tuple]], kwargs: Optional[dict]
    ) -> Any:
        args = args or ()
        kwargs = kwargs or {}
        token: Token = self._get_token(key)
        try:
            if token.can_do():
                try:
                    token.set_result(await func(*args, **kwargs))
                except Exception as e:
                    token.set_result(e)
                    raise e
            return await token.await_done()
        finally:
            self._future_dict.pop(key, None)

    async def do(
        self, key: str, func: Callable, args: Optional[Union[list, tuple]] = None, kwargs: Optional[dict] = None
    ) -> Any:
        return await self._token_handle(key, func, args, kwargs)

    def wrapper_do(self, key: Optional[str] = None) -> Callable:
        def wrapper(func: Callable) -> Callable:
            key_name: str = func.__name__ + str(id(func)) if key is None else key

            @wraps(func)
            async def wrapper_func(*args: Any, **kwargs: Any) -> Any:
                real_key_name: str = key_name
                if args and args[0].__class__.__name__ in func.__qualname__:
                    real_key_name += f":{id(args[0])}"
                return await self._token_handle(real_key_name, func, args, kwargs)

            return wrapper_func

        return wrapper

    def __str__(self) -> str:
        return str(self._future_dict)
