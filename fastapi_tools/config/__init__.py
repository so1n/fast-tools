import ast
import os
import typing
from collections.abc import MutableMapping
from typing import Any, NoReturn, Union


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
        self._init_default_value()
        self._read_environ(_environ)
        if env_file is not None and os.path.isfile(env_file):
            self._read_file(env_file)
        self._check_not_set_value()

    def _init_default_value(self):
        for key in self.__annotations__:
            if hasattr(self, key):
                self.__dict__[key] = getattr(self, key)

    def _check_not_set_value(self):
        for key in self.__annotations__:
            if not hasattr(self, key):
                raise ValueError(f'{self.__class__.__name__}.{key} not set value')

    def __setattr__(self, key: str, value: Any) -> NoReturn:
        if key not in self.__annotations__:
            raise AttributeError(
                "{} not found attr:{}".format(self.__class__.__name__, key)
            )
        # Now support typing.Optional, typing.Union and python base type
        key_type = self.__annotations__[key]
        if hasattr(key_type, '__origin__') and key_type.__origin__ is Union:
            # get typing.type from Union
            key_type = key_type.__args__

        if not isinstance(value, key_type):
            try:
                if isinstance(key_type, tuple):
                    for i in key_type:
                        try:
                            value = self._python_type_conversion(i, value)
                            break
                        except TypeError:
                            value = None
                    else:
                        raise TypeError
                else:
                    value = self._python_type_conversion(key_type, value)
            except Exception:
                raise TypeError(f"The type of {key} should be {key_type}")
        self.__dict__[key] = value

    @staticmethod
    def _python_type_conversion(key_type, value: str):
        value = ast.literal_eval(value)
        if type(value) == key_type:
            return value
        return TypeError(f"Value type:{type(value)} is not {key_type}")

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
