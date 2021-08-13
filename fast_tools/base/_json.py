try:
    import ojson as json  # type: ignore
except ImportError:
    try:
        import ujson as json  # type: ignore
    except ImportError:
        import json  # type: ignore
