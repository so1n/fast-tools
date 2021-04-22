import aioredis  # type: ignore
from pytest_mock import MockFixture
from requests import Response
from starlette.testclient import TestClient

from example.context import app
from .conftest import AnyStringWith  # type: ignore


class TestContext:
    def test_contest(self, mocker: MockFixture) -> None:
        debug_patch = mocker.patch("example.context.logging.debug")
        info_patch = mocker.patch("example.context.logging.info")
        warning_patch = mocker.patch("example.context.logging.warning")

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
