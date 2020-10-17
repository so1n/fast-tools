"""
example run output:
[
    {'name': 'REDIS_PASS', 'value': None, 'type': <class 'NoneType'>},
    {'name': 'DEBUG', 'value': True, 'type': <class 'bool'>},
    {'name': 'PORT', 'value': 8000, 'type': <class 'int'>},
    {'name': 'HOST', 'value': '127.0.0.1', 'type': <class 'str'>},
    {'name': 'REDIS_ADDRESS', 'value': 'localhost', 'type': <class 'str'>},
    {'name': 'MYSQL_DB_HOST', 'value': 'localhost', 'type': <class 'str'>},
    {'name': 'MYSQL_DB_USER', 'value': 'root', 'type': <class 'str'>},
    {'name': 'MYSQL_DB_PASS', 'value': 'rootpass', 'type': <class 'str'>},
    {'name': 'MYSQL_DB_NAME', 'value': 'rootdb', 'type': <class 'str'>},
    {'name': 'ES_HOST', 'value': ['127.0.0.1:9200', '127.0.0.2:9200'], 'type': <class 'list'>}
]
"""
from typing import List, Optional
from fast_tools.config import Config

from pydantic.fields import Json


class MyConfig(Config):
    DEBUG: bool
    HOST: str
    PORT: int

    REDIS_ADDRESS: str
    REDIS_PASS: Optional[str] = None

    MYSQL_DB_HOST: str
    MYSQL_DB_NAME: str
    MYSQL_DB_PASS: str
    MYSQL_DB_USER: str
    ES_HOST: Json[List]
    TEST_LIST_INT: Json[List]
    YML_ES_HOST: Optional[List[str]] = None
    YML_TEST_LIST_INT: Optional[List[int]] = None


def main(config_path: str, group: str):
    print(config_path, MyConfig(config_path, group=group))


if __name__ == '__main__':
    main('example_config.ini', 'test')
    main('example_config.yml', 'test')
