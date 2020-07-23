import os
import typing
from collections.abc import MutableMapping
from typing import NoReturn, Type, Optional

from pydantic import BaseModel


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
        self,
        model: Type[BaseModel],
        file: Optional[str] = None,
        is_load_environ: bool = False,
    ) -> None:
        self._model: 'Optional[BaseModel]' = None
        self._dict = {}
        if is_load_environ:
            self._read_environ(environ)
        if file is not None and os.path.isfile(file):
            self._read_file(file)

        self._load_model(model)

    def _load_model(self, model: Type[BaseModel]):
        self._model = model(**self._dict)

    def _read_environ(self, _environ: typing.Mapping[str, str]) -> NoReturn:
        self._dict.update(dict(_environ))

    def _read_file(self, file_name: str) -> NoReturn:
        file_dict: dict = {}
        with open(file_name) as input_file:
            for line in input_file.readlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    file_dict[key] = value
        self._dict.update(file_dict)

    def __str__(self):
        return self._model.json()
