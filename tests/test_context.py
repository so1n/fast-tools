import uuid

import aioredis  # type: ignore
import pytest
from pytest_mock import MockFixture
from requests import Response  # type: ignore
from starlette.testclient import TestClient

from example.context import app
from fast_tools.context import ContextBaseModel, HeaderHelper

from .conftest import AnyStringWith  # type: ignore


class TestContext:
    def test_contest(self, mocker: MockFixture) -> None:
        with TestClient(app) as client:
            response: Response = client.get("/")
            resp_dict: dict = response.json()
            message_dict: dict = resp_dict["message"]
            for key in ["request_id", "ip", "user_agent"]:
                assert key in message_dict

        with pytest.raises(RuntimeError) as e:

            class NewContextModel(ContextBaseModel):
                request_id: str = HeaderHelper.i("X-Request-Id", default_func=lambda request: str(uuid.uuid4()))

        assert e.value.args[0] == "key:HeaderHelper:X-Request-Id already exists"
