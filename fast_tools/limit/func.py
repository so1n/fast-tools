from typing import Optional, Tuple

from fastapi import Request


async def client_ip(request: Request) -> Tuple[str, Optional[str]]:
    if "X-Real-IP" in request.headers:
        return request.headers["X-Real-IP"], None
    return request.client.host, None
