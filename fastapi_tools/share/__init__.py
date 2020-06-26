import asyncio
from typing import Any, Callable, Dict, TypeVar, Optional

__all__ = ('Share', 'Token')
_Tp = TypeVar('_Tp')


class Token(object):
    def __init__(self, key: str, share: 'Share'):
        self._share: 'Share' = share
        self._key: str = key
        self._future: Optional[asyncio.Future] = None

    def can_do(self) -> bool:
        if not self._future:
            self._future = asyncio.Future()
            return True
        return False

    def cancel(self) -> bool:
        if self._future and not self._future.cancelled():
            self._future.cancel()
            return True
        return False

    async def await_done(self) -> Optional[Any]:
        if self._future and not self._future.done():
            await self._future
        return self._future.result()

    def set_result(self, result: Any) -> bool:
        if self._future and not self._future.done():
            if isinstance(result, Exception):
                self._future.set_exception(result)
            else:
                self._future.set_result(result)
            asyncio.ensure_future(self._share.delay_del_token(self._key))
            return True
        return False


class Share(object):
    def __init__(self, delay_clean_time: int = 1):
        self._future_dict: Dict[str, Token] = dict()
        self._delay_clean_time = delay_clean_time

    def get_token(self, key: str) -> Token:
        if key not in self._future_dict:
            token: 'Token' = Token(key, self)
            self._future_dict[key] = token
        return self._future_dict[key]

    def cancel(self):
        for key, token in self._future_dict.items():
            token.cancel()

    async def delay_del_token(self, key: str):
        await asyncio.sleep(self._delay_clean_time)

        if key in self._future_dict:
            del self._future_dict[key]
        else:
            raise KeyError(f'not found token:{key}')

    async def do(
        self,
        key: str,
        func: Callable,
        args: Optional[list] = None,
        kwargs: Optional[dict] = None
    ):
        args = args if args else []
        kwargs = kwargs if kwargs else {}
        token: Token = self.get_token(key)
        can_do = token.can_do()
        if can_do:
            try:
                result = await func(*args, **kwargs)
                token.set_result(result)
            except Exception as e:
                token.set_result(e)
                raise e
        return await token.await_done()

    def __str__(self):
        return str(self._future_dict)
