import aioredis  # type: ignore
import pytest
from requests import Response
from starlette.testclient import TestClient

from example.cbv import app
from .conftest import AnyStringWith  # type: ignore


pytestmark = pytest.mark.asyncio


class TestCbv:
    def test_cbv(self) -> None:
        with TestClient(app) as client:
            response: Response = client.get("/?test_default_id=345")
            assert response.status_code == 203
            assert response.json() == {
                "message": "hello, world",
                "user_agent": "testclient",
                "host": "testserver",
                "id": 345
            }
            response = client.post("/")
            assert response.status_code == 200
            assert response.json() == {
                "message": "hello, world",
                "user_agent": "testclient",
                "host": "testserver",
                "id": 123
            }