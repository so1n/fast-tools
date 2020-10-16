import abc
from contextvars import ContextVar, Token, copy_context
from typing import Any, Callable, Dict, Optional, Type

from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


_fastapi_tools_context: ContextVar[Dict[str, Any]] = ContextVar("fastapi_tools_context", default={})


class BaseContextQuery(metaclass=abc.ABCMeta):
    _set: set = set()

    def __init__(self, key: str):
        self._key: key = key
        cls: 'Type[BaseContextQuery]' = self.__class__
        key: str = f'{cls.__name__}:{key}'
        if key in cls._set:
            # key must be globally unique
            raise RuntimeError(f'key:{key} already exists')
        cls._set.add(key)

    def __get__(self, instance: 'ContextBaseModel', owner: 'Type[ContextBaseModel]'):
        ctx_dict: dict = _fastapi_tools_context.get()
        return ctx_dict[self._key]

    def __set__(self, instance: 'ContextBaseModel', request: Request):
        raise NotImplementedError

    def _set_cache(self, instance: 'ContextBaseModel', value: Any):
        instance.cache_dict[self._key] = value


class HeaderQuery(BaseContextQuery):
    def __init__(self, key: str, default_func: Optional[Callable] = None):
        self._default_func: Optional[Callable] = default_func
        super().__init__(key)

    def __set__(self, instance: 'ContextBaseModel', request: Request):
        headers: Headers = request.headers
        if self._key != self._key.lower():
            value: Any = headers.get(self._key) or headers.get(self._key.lower())
        else:
            value: Any = headers.get(self._key)

        if not value and self._default_func is not None:
            value: Any = self._default_func(request)
        # TODO check type hint
        self._set_cache(instance, value)


class CustomQuery(BaseContextQuery):
    def __init__(self, value: Any):
        self._value: Any = None
        super().__init__('custom:' + str(id(value)))

    def __set__(self, instance: 'ContextBaseModel', request: Request):
        self._set_cache(instance, self._value)


class ContextBaseModel(object):
    def __init__(self):
        self._cache_dict: dict = {}

    @staticmethod
    def exists() -> bool:
        return _fastapi_tools_context in copy_context()

    def _set_context(self, request: Request) -> Token:
        self._cache_dict: dict = {}
        for key in self.__annotations__.keys():
            setattr(self, key, request)
        return _fastapi_tools_context.set(self._cache_dict)

    @staticmethod
    def to_dict(is_safe_return: bool = False) -> Dict[str, Any]:
        context_dict: Dict[str, Any] = _fastapi_tools_context.get()
        if context_dict and is_safe_return:
            return {
                key: value
                for key, value in context_dict.items()
                if not key.startswith('custom')  # CustomQuery key name custom:****
            }
        return context_dict

    @property
    def cache_dict(self):
        return self._cache_dict


class ContextMiddleware(BaseHTTPMiddleware):

    def __init__(self, context_model: Type[ContextBaseModel], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_model: Type[ContextBaseModel] = context_model

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        context_model: ContextBaseModel = self.context_model()
        context_token: Token = context_model._set_context(request)
        try:
            response = await call_next(request)
            return response
        finally:
            _fastapi_tools_context.reset(context_token)

