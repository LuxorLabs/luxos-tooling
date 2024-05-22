"""user facing functions for normal use"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Callable

import luxos.misc
from luxos.asyncops import rexec  # noqa: F401
from luxos.scripts.luxos import execute_command  # noqa: F401


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


def load_ips_from_csv(path: Path | str, port: int = 4028) -> list[tuple[str, int]]:
    from .ips import iter_ip_ranges

    result = []
    for line in Path(path).read_text().split(os.linesep):
        line = line.partition("#")[0]
        if not line.strip():
            continue
        for host, port2 in iter_ip_ranges(line):
            result.append((host, port2 or port))
    return result


async def launch(
    addresses: list[tuple[str, int]], call: Callable[[str, int], Any], *args, **kwargs
) -> Any:
    """launch an async function on a list of (host, port) miners

    Eg.
        async printme(host, port, value):
            print(await rexec(host, port, "version"))
        asyncio.run(launch([("127.0.0.1", 4028)], printme, value=11, batch=10))
    """
    # special kwargs!!
    n = int(kwargs.pop("batch") or 0) if "batch" in kwargs else None
    if n and n < 0:
        raise RuntimeError(
            f"cannot pass the 'batch' keyword argument with a value < 0: batch={n}"
        )

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
