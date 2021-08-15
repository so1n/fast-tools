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
        debug_patch = mocker.patch("example.context.logging.debug")
        info_patch = mocker.patch("example.context.logging.info")
        warning_patch = mocker.patch("example.context.logging.warning")
        error_patch = mocker.patch("example.context.logging.error")

        with TestClient(app) as client:
            response: Response = client.get("/")
            resp_dict: dict = response.json()
            message_dict: dict = resp_dict["message"]
            client_id: int = resp_dict["client_id"]
            for key in ["request_id", "ip", "user_agent"]:
                assert key in message_dict

        debug_patch.assert_called_with(f"test_ensure_future {client_id}")
        info_patch.assert_called_with(f"test_run_in_executor {client_id}")
        warning_patch.assert_called_with(f"test_call_soon {client_id}")
        error_patch.assert_called_with(AnyStringWith("traceback info"))

        with pytest.raises(RuntimeError) as e:

            class NewContextModel(ContextBaseModel):
                request_id: str = HeaderHelper.i("X-Request-Id", default_func=lambda request: str(uuid.uuid4()))

        assert e.value.args[0] == "key:HeaderHelper:X-Request-Id already exists"
