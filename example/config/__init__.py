"""
run output:
[
    {'name': 'REDIS_PASS', 'value': None, 'type': <class 'NoneType'>}
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
from typing import Optional
from fastapi_tools.config import Config


class MyConfig(Config):
    DEBUG: bool
    HOST: Optional[str]
    PORT: Optional[int]

    REDIS_ADDRESS: Optional[str]
    REDIS_PASS: Optional[str] = None

    MYSQL_DB_HOST: Optional[str]
    MYSQL_DB_NAME: Optional[str]
    MYSQL_DB_PASS: Optional[str]
    MYSQL_DB_USER: Optional[str]
    ES_HOST: Optional[list]


config = MyConfig('./example_config.conf')
print(config)