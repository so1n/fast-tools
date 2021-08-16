import pytest

from example.config import MyConfig
from fast_tools.config import Json

from .conftest import AnyStringWith  # type: ignore


class TestConfig:
    def test_inherit_error(self) -> None:
        class CustomerField(Json):
            ...

        with pytest.raises(RuntimeError) as e:
            CustomerField()
        assert e.value.args[0] == "Only classes that inherit BaseField can be used"

    def test_config(self) -> None:
        ini_dict: dict = {
            "DEBUG": True,
            "HOST": "127.0.0.1",
            "ALIAS_HOST": "127.0.0.1",
            "PORT": 8000,
            "REDIS_ADDRESS": "localhost",
            "REDIS_PASS": None,
            "MYSQL_DB_HOST": "localhost",
            "MYSQL_DB_NAME": "rootdb",
            "MYSQL_DB_PASS": "rootpass",
            "MYSQL_DB_USER": "root",
            "ES_HOST": ["127.0.0.1:9200", "127.0.0.2:9200"],
            "TEST_LIST_INT": [1, 2, 3, 4],
            "YML_ES_HOST": None,
            "YML_TEST_LIST_INT": None,
        }
        yml_dict: dict = {
            "DEBUG": True,
            "HOST": "127.0.0.1",
            "ALIAS_HOST": "127.0.0.1",
            "PORT": 8000,
            "REDIS_ADDRESS": "localhost",
            "REDIS_PASS": None,
            "MYSQL_DB_HOST": "localhost",
            "MYSQL_DB_NAME": "rootdb",
            "MYSQL_DB_PASS": "rootpass",
            "MYSQL_DB_USER": "root",
            "ES_HOST": ["127.0.0.1:9200", "127.0.0.2:9200"],
            "TEST_LIST_INT": [1, 2, 3, 4],
            "YML_ES_HOST": ["127.0.0.1:9200", "127.0.0.2:9200"],
            "YML_TEST_LIST_INT": [1, 2, 3, 4],
        }

        assert MyConfig("example/config/example_config.ini", group="test").model.dict() == ini_dict
        assert MyConfig("example/config/example_config.yml", group="test").model.dict() == yml_dict
