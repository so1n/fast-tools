from requests import Response
from starlette.testclient import TestClient

from example.exporter import app


class TestExporter:
    def test_exporter(self) -> None:
        with TestClient(app) as client:
            client.get("/")
            client.get("/not_found")
            client.get("/api/users/login")
            client.get("/api/users/123/items/abc")
            client.get("/api/users/456/items/def")
            response: Response = client.get("/metrics")
            assert "/not_found" not in response.text
            assert "/metrics" not in response.text
            assert "/api/users/{user_id}/items/{item_id}" in response.text
            assert "/" in response.text
            assert "/api/users/login" in response.text
