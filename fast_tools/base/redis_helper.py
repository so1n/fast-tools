import asyncio
import logging
import json
import time

from contextlib import asynccontextmanager
from typing import Optional, Any, List, Tuple

from aioredis import ConnectionsPool, Redis, errors
from fast_tools.base.utils import namespace as _namespace


class RedisHelper(object):
    def __init__(
        self,
        namespace: str = _namespace,
    ):
        self._namespace: str = namespace
        self._conn_pool: Optional["ConnectionsPool"] = None
        self.client: Optional["Redis"] = None

    def init(self, conn_pool: "ConnectionsPool", namespace: Optional[str] = None):
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

    async def _lock(self, key: str, timeout: int) -> bool:
        lock = await self.execute("set", key, "1", "ex", timeout, "nx")
        return True if lock == "ok" else False

    @asynccontextmanager
    async def lock(
            self,
            lock_key: str,
            timeout: int = 1 * 60,
            block_timeout: Optional[int] = None,
            sleep_time: float = 0.1,
            is_raise_exc: bool = True,
            delay_time: Optional[int] = None,
    ) -> bool:
        if timeout and timeout > sleep_time:
            raise RuntimeError("'sleep' must be less than 'timeout'")
        real_key: str = f"{self._namespace}:lock:{lock_key}"
        lock_ret: bool = False
        start_time: int = int(time.time())
        try:
            while True:
                lock_ret = await self._lock(real_key, timeout)
                if lock_ret or (block_timeout and (int(time.time()) - start_time) > block_timeout):
                    break
                else:
                    await asyncio.sleep(sleep_time)

            if not lock_ret and is_raise_exc:
                raise TimeoutError('Get lock timeout')
            yield lock_ret
        finally:
            if lock_ret:
                await self.del_key(real_key, delay_time)

    async def exists(self, key: str) -> bool:
        ret: int = await self.execute("exists", key)
        return True if ret == 1 else False

    async def get_dict(self, key) -> dict:
        data = await self.execute("get", key)
        if not data or data == "":
            return {}
        return json.loads(data)

    async def set_dict(self, key, data: dict, timeout: Optional[int] = None) -> None:
        await self.execute("set", key, json.dumps(data))
        if timeout:
            await self.execute("EXPIRE", key, timeout)

    async def del_key(self, key, delay: Optional[int] = None) -> bool:
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

    async def hmset_dict(self, key, key_dict: dict):
        value_list: list = []
        for _key in key_dict.keys():
            value_list.append(_key)
            value_list.append(json.dumps({_key: key_dict[_key]}))
        await self.execute("HMSET", key, *value_list)

    async def hget_dict(self, key, field) -> Any:
        value: str = await self.execute("HGET", key, field)
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

    def closed(self):
        return self._conn_pool.closed

    async def close(self) -> None:
        if self._conn_pool is not None and not self._conn_pool.closed:
            logging.info(f"{self.__class__.__name__} Close.")
            self._conn_pool.close()
            await self._conn_pool.wait_closed()
        else:
            logging.warning(f"{self.__class__.__name__} has been closed")

    @property
    def namespace(self):
        return self._namespace
