"""user facing functions for normal use"""

from __future__ import annotations

import asyncio
import functools
import traceback
from typing import Any, Callable

import luxos.misc
from luxos.asyncops import rexec  # noqa: F401

# we bring here functions from other modules
from luxos.exceptions import (  # noqa: F401
    LuxosLaunchError,
    LuxosLaunchTimeoutError,
    MinerConnectionError,
)
from luxos.ips import ip_ranges, load_ips_from_csv  # noqa: F401
from luxos.syncops import execute_command  # noqa: F401


async def launch(
    addresses: list[tuple[str, int]], call: Callable[[str, int], Any], *args, **kwargs
) -> Any:
    """launch an async function on a list of (host, port) miners

    Special kwargs:
        - batch execute operation in group of batch tasks (rate limiting)
        - naked do not wrap the call, so is up to you catching exceptions (default None)

    Eg.
        async printme(host, port, value):
            print(await rexec(host, port, "version"))
        asyncio.run(launch([("127.0.0.1", 4028)], printme, value=11, batch=10))
    """

    # a naked options, wraps the 'call' and re-raise exceptions as LuxosLaunchError
    naked = kwargs.pop("naked") if "naked" in kwargs else None

    def wraps(fn):
        @functools.wraps(fn)
        async def _fn(host: str, port: int):
            try:
                return await fn(host, port)
            except asyncio.TimeoutError as exc:
                tback = "".join(traceback.format_exc())
                raise LuxosLaunchTimeoutError(tback, host, port) from exc
            except Exception as exc:
                tback = "".join(traceback.format_exc())
                raise LuxosLaunchError(tback, host, port) from exc

        return _fn

    n = int(kwargs.pop("batch") or 0) if "batch" in kwargs else None
    if n and n < 0:
        raise RuntimeError(
            f"cannot pass the 'batch' keyword argument with a value < 0: batch={n}"
        )
    if not naked:
        call = wraps(call)

    if n:
        result = []
        for subaddresses in luxos.misc.batched(addresses, n):
            tasks = [call(*address, *args, **kwargs) for address in subaddresses]
            for task in await asyncio.gather(*tasks, return_exceptions=True):
                result.append(task)
        return result
    else:
        tasks = [call(*address, *args, **kwargs) for address in addresses]
        return await asyncio.gather(*tasks, return_exceptions=True)
