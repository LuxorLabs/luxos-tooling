"""user facing functions for normal use"""

from __future__ import annotations

import asyncio
import functools
import traceback
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
    def __init__(self, tback: str, host: str, port: int, *args, **kwargs):
        self.tback = tback
        super().__init__(host, port, *args, **kwargs)

    def __str__(self):
        from .text import indent

        msg = indent(str(self.tback), "| ")
        return f"{self.address}: \n{msg}"


class LuxosLaunchTimeoutError(LuxosLaunchError, asyncio.TimeoutError):
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


if __name__ == "__main__":

    async def main():
        from .text import indent

        hosts = [
            ("10.206.0.213", 4028),
            ("10.206.0.213", 4029),
        ]

        async def task(host, port):
            return (await rexec(host, port, "config"))["CONFIG"][0]["ProfilXe"]  # type: ignore

        results = await launch(hosts, task)
        for result in results:
            if isinstance(result, asyncio.TimeoutError):
                print("== TIMEOUT EXCEPTION")
                print(indent(str(result), "| "))
            if isinstance(result, LuxosLaunchTimeoutError):
                print("== LUXOS TIMEOUT EXCEPTION")
                print(indent(str(result), "| "))
            if isinstance(result, LuxosLaunchError):
                print("== LUXOS ERROR EXCEPTION")
                print(indent(str(result), "| "))
            if isinstance(result, Exception):
                print("== EXCEPTION")
                print(indent(str(result), "| "))
            else:
                print(f"RESULT: {result}")

    asyncio.run(main())
