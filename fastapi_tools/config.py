import os
import typing
from collections.abc import MutableMapping
from typing import Any, Dict, NoReturn, Type

from pydantic import (
    BaseModel,
    create_model
)


__all__ = ['Config']


class EnvironError(Exception):
    pass


class Environ(MutableMapping):
    """
    copy from starlette
    """
    def __init__(self, _environ: typing.MutableMapping = os.environ):
        self._environ = _environ
        self._has_been_read = set()  # type: typing.Set[typing.Any]

    def __getitem__(self, key: typing.Any) -> typing.Any:
        self._has_been_read.add(key)
        return self._environ.__getitem__(key)

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        if key in self._has_been_read:
            raise EnvironError(
                f"Attempting to set environ['{key}'], but the value has already been read."
            )
        self._environ.__setitem__(key, value)

    def __delitem__(self, key: typing.Any) -> None:
        if key in self._has_been_read:
            raise EnvironError(
                f"Attempting to delete environ['{key}'], but the value has already been read."
            )
        self._environ.__delitem__(key)

    def __iter__(self) -> typing.Iterator:
        return iter(self._environ)

    def __len__(self) -> int:
        return len(self._environ)


environ = Environ()


class Config:
    def __init__(
        self, env_file: str = None,
        _environ: typing.Mapping[str, str] = environ
    ) -> None:
        self._read_environ(_environ)
        if env_file is not None and os.path.isfile(env_file):
            self._read_file(env_file)
        pydantic_obj = self._init_pydantic_obj()
        self.__dict__.update(pydantic_obj(**self.__dict__).dict())

    def _init_pydantic_obj(self) -> Type[BaseModel]:
        annotation_dict: Dict[str, Type[Any, ...]] = {}
        for key in self.__annotations__:
            if hasattr(self, key):
                self.__dict__[key] = getattr(self, key)
                annotation_dict[key] = (self.__annotations__[key], ...)
        dynamic_model: Type[BaseModel] = create_model('DynamicFoobarModel', **annotation_dict)
        return dynamic_model

    def _read_environ(self, _environ: typing.Mapping[str, str]) -> NoReturn:
        for key in self.__annotations__.keys():
            if key in _environ:
                setattr(self, key, _environ[key])

    def _read_file(self, file_name: str) -> NoReturn:
        with open(file_name) as input_file:
            for line in input_file.readlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    setattr(self, key, value)

    def __str__(self):
        return str(
            [
                {'name': key, 'value': self.__dict__[key], 'type': type(self.__dict__[key])}
                for key in self.__dict__.keys()
            ]
        )