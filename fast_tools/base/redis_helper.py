import asyncio
import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any, List, Optional, Tuple

from aioredis import ConnectionsPool, Redis, errors  # type: ignore

from fast_tools.base.utils import NAMESPACE as _namespace


class LockError(Exception):
    ...


class Lock(object):
    """design like pyredis.lock"""

    # KEYS[1] - lock name
    # ARGV[1] - token
    # return 1 if the lock was released, otherwise 0
    LUA_RELEASE_SCRIPT = """
                    local token = redis.call('get', KEYS[1])
                    if not token or token ~= ARGV[1] then
                        return 0
                    end
                    redis.call('del', KEYS[1])
                    return 1
                """

    def __init__(
        self,
        redis_helper: "RedisHelper",
        lock_key: str,
        timeout: int = 1 * 60,
        block_timeout: Optional[int] = None,
        sleep_time: float = 0.1,
    ):

        self._redis: "RedisHelper" = redis_helper
        self._lock_key: str = f"{self._redis.namespace}:lock:{lock_key}"
        self._timeout: int = timeout
        self._blocking_timeout: Optional[int] = block_timeout
        self._sleep_time: float = sleep_time

        self.local: ContextVar = ContextVar("token", default=None)

    async def __aenter__(self, blocking_timeout: Optional[int] = None) -> "Lock":
        # force blocking, as otherwise the user would have to check whether
        # the lock was actually acquired or not.
        await self.acquire(blocking_timeout=blocking_timeout)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.release()

    async def locked(self) -> bool:
        """
        Returns True if this key is locked by any process, otherwise False.
        """
        return self._redis.client.get(self._lock_key) != ""

    async def do_release(self, expected_token: int) -> None:
        if not bool(
            await self._redis.client.eval(self.LUA_RELEASE_SCRIPT, keys=[self._lock_key], args=[expected_token])
        ):
            raise LockError("Cannot release a lock that's no longer owned")

    async def release(self) -> None:
        """Releases the already acquired lock"""
        expected_token = self.local.get()
        if expected_token is None:
            raise LockError("Cannot release an unlocked lock")
        self.local.set(None)
        await self.do_release(expected_token)

    async def do_acquire(self, token: str) -> bool:
        timeout: Optional[int] = int(self._timeout) if self._timeout else None

        if await self._redis.execute("SET", self._lock_key, token, "ex", timeout, "nx") == "ok":
            return True
        return False

    async def acquire(self, blocking_timeout: Optional[int] = None) -> bool:
        sleep: float = self._sleep_time
        token: str = str(uuid.uuid1())
        if blocking_timeout is None:
            blocking_timeout = self._blocking_timeout
        stop_trying_at: Optional[float] = None
        if blocking_timeout is not None:
            stop_trying_at = time.time() + blocking_timeout
        while True:
            if await self.do_acquire(token):
                self.local.set(token)
                return True
            if stop_trying_at is not None and time.time() > stop_trying_at:
                return False
            await asyncio.sleep(sleep)


class RedisHelper(object):
    def __init__(
        self,
        namespace: str = _namespace,
    ):
        self._namespace: str = namespace
        self._conn_pool: Optional["ConnectionsPool"] = None
        self.client: Optional["Redis"] = None

    def init(self, conn_pool: "ConnectionsPool", namespace: Optional[str] = None) -> None:
        if conn_pool is None:
            logging.error("conn_pool is none")
        elif self._conn_pool is not None and not self._conn_pool.closed:
            logging.error(f"Init error, {self.__class__.__name__} already init")
        else:
            self._conn_pool = conn_pool
            self.client = Redis(self._conn_pool)
            if namespace:
                self._namespace = namespace

    async def execute(self, command: str, *args: Any, **kwargs: Any) -> Optional[Any]:
        try:
            async with self._conn_pool.get() as conn:
                return await conn.execute(command, *args, **kwargs)
        except Exception as e:
            raise errors.RedisError(
                f"{self.__class__.__name__} execute error. error:{e}."
                f" command:{command}, args:{args}, kwargs:{kwargs}"
            ) from e

    def lock(
        self,
        key: str,
        timeout: int = 1 * 60,
        block_timeout: Optional[int] = None,
        sleep_time: float = 0.1,
    ) -> Lock:
        return Lock(self, key, timeout, block_timeout, sleep_time)

    async def exists(self, key: str) -> bool:
        ret: Optional[int] = await self.execute("exists", key)
        return True if ret and ret == 1 else False

    async def get_dict(self, key: str) -> dict:
        data = await self.execute("get", key)
        if not data or data == "":
            return {}
        return json.loads(data)

    async def set_dict(self, key: str, data: dict, timeout: Optional[int] = None) -> None:
        await self.execute("set", key, json.dumps(data))
        if timeout:
            await self.execute("EXPIRE", key, timeout)

    async def del_key(self, key: str, delay: Optional[int] = None) -> bool:
        if delay:
            return bool(await self.execute("EXPIRE", key, delay))
        return bool(await self.execute("del", key))

    async def pipeline(self, exec_list: List[Tuple]) -> Optional[list]:
        try:
            p = self.client.pipeline()
            for command, *args in exec_list:
                if command == "del":
                    command = "delete"
                getattr(p, command)(*args)

            return await p.execute()
        except Exception as e:
            raise errors.PipelineError(f"Redis pipeline error, exec_list:{exec_list}") from e

    async def hmset_dict(self, key: str, key_dict: dict) -> None:
        value_list: list = []
        for _key in key_dict.keys():
            value_list.append(_key)
            value_list.append(json.dumps({_key: key_dict[_key]}))
        await self.execute("HMSET", key, *value_list)

    async def hget_dict(self, key: str, field: str) -> Any:
        value: Optional[str] = await self.execute("HGET", key, field)
        if value is None:
            return None
        return json.loads(value)[field]

    async def hmget_dict(self, key: str) -> dict:
        return_dict = {}
        scan = 0
        while True:
            scan, kv_list = await self.execute("HSCAN", key, scan)
            for i in range(0, len(kv_list) - 1, 2):
                _key = kv_list[i]
                _value = json.loads(kv_list[i + 1])
                try:
                    return_dict[_key] = _value[_key]
                except Exception as e:
                    logging.error(f"hmget error:{e}, key{_key}, value{_value}")

            if scan == "0":
                break
        return return_dict

    def closed(self) -> None:
        return self._conn_pool.closed

    async def close(self) -> None:
        if self._conn_pool is not None and not self._conn_pool.closed:
            logging.info(f"{self.__class__.__name__} Close.")
            self._conn_pool.close()
            await self._conn_pool.wait_closed()
        else:
            logging.warning(f"{self.__class__.__name__} has been closed")

    @property
    def namespace(self) -> str:
        return self._namespace
