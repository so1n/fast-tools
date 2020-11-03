import os
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY, multiprocess, CollectorRegistry
from starlette.requests import Request
from starlette.responses import Response


def get_metrics(request: Request) -> Response:
    if "prometheus_multiproc_dir" in os.environ:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    else:
        registry = REGISTRY

    return Response(generate_latest(registry), status_code=200, headers={"Content-Type": CONTENT_TYPE_LATEST})
