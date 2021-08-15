import os
from typing import Optional

from prometheus_client import REGISTRY, CollectorRegistry, multiprocess

registry: CollectorRegistry = REGISTRY


def init_registry(customer_registry: Optional[CollectorRegistry] = None) -> None:
    global registry
    if getattr(registry, "__inited", False):
        raise RuntimeError("already init registry")
    if customer_registry:
        registry = customer_registry
    if "prometheus_multiproc_dir" in os.environ:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    setattr(registry, "__inited", True)
