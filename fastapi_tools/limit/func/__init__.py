from fastapi import Request


async def client_ip(request: Request) -> str:
    if 'X-Real-IP' in request.headers:
        return request.headers['X-Real-IP']
    return request.client.host
