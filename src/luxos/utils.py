"""user facing functions for normal use"""

from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable

import luxos.misc
from luxos.asyncops import rexec  # noqa: F401

# we bring here functions from other modules
from luxos.exceptions import MinerConnectionError
from luxos.ips import load_ips_from_csv  # noqa: F401

# TODO prepare for refactoring using example in
#      tests.test_asyncops.test_bridge_execute_command
from luxos.scripts.luxos import execute_command  # noqa: F401


class LuxosLaunchError(MinerConnectionError):
    pass


def ip_ranges(
    txt: str, rsep: str = "-", gsep: str = ":"
) -> list[tuple[str, int | None]]:
    """return a list of ips given a text expression.

    Eg.
        >>> for ip in ip_ranges("127.0.0.1"):
        ...     print(ip)
        127.0.0.1

        >>> for ip in ip_ranges("127.0.0.1-127.0.0.3"):
        ...     print(ip)
        127.0.0.1
        127.0.0.2
        127.0.0.3

    NOTE: use the `:` (gsep) to separate ips groups, and `-` (rsep) to define a range.
    """
    from .ips import iter_ip_ranges

    return list(iter_ip_ranges(txt, rsep=rsep, gsep=gsep))


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
            except Exception as exc:
                raise LuxosLaunchError(host, port) from exc

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
