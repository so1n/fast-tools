import os
import typing
from collections.abc import MutableMapping
from typing import Any, Dict, NoReturn, Optional, Type

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
        self, config_file: Optional[str] = None, _environ: typing.Mapping[str, str] = environ
    ) -> None:
        self._config_dict: Dict[str, Any] = {}
        self._config_dict.update(_environ)
        if config_file is not None and os.path.isfile(config_file):
            self._read_file(config_file)
        self._init_pydantic_obj()

    def _init_pydantic_obj(self):
        annotation_dict: Dict[str, Type[Any, ...]] = {}
        for key in self.__annotations__:
            if key not in self._config_dict:
                default_value = getattr(self, key, Config)
                if default_value != Config:
                    # set default value
                    self._config_dict[key] = default_value
                annotation_dict[key] = (self.__annotations__[key], ...)
        dynamic_model: Type[BaseModel] = create_model('DynamicFoobarModel', **annotation_dict)
        self.__dict__.update(dynamic_model(**self._config_dict).dict())

    def _read_file(self, file_name: str) -> NoReturn:
        with open(file_name) as input_file:
            for line in input_file.readlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    self._config_dict[key] = value

    def __str__(self):
        return str(
            [
                {'name': key, 'value': self._config_dict[key], 'type': type(self._config_dict[key])}
                for key in self._config_dict.keys()
            ]
        )