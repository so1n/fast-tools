from prometheus_client import CONTENT_TYPE_LATEST, generate_latest  # type: ignore
from starlette.requests import Request
from starlette.responses import Response

from .util import registry


def get_metrics(request: Request) -> Response:
    return Response(generate_latest(registry), status_code=200, headers={"Content-Type": CONTENT_TYPE_LATEST})
