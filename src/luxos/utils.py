"""user facing functions for normal use"""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Any, Callable
from luxos.asyncops import rexec  # noqa: F401


def load_ips_from_csv(path: Path | str, port: int = 4028) -> list[tuple[str, int]]:
    from luxos.scripts.luxos import load_ip_list_from_csv

    result = []
    for ip in load_ip_list_from_csv(str(path)):
        result.append((ip, port))
    return result


async def launch(
    addresses: list[tuple[str, int]],
    call: Callable[[str, int], Any],
    batch: int | None = None,
) -> Any:
    """launch an async function on a list of (host, port) miners

    Eg.
        async printme(host, port):
            print(await rexec(host, port, "version"))
        asyncio.run(launch([("127.0.0.1", 4028)], printme))
    """
    # see https://www.artificialworlds.net/blog/2017/06/12/making-100-million-requests-with-python-aiohttp/
    from luxos.misc import batched

    if batch:
        result = []
        for arguments in batched(addresses, batch):
            tasks = [call(*args) for args in arguments]
            for task in await asyncio.gather(*tasks, return_exceptions=True):
                result.append(task)
        return result
    else:
        tasks = [call(*args) for args in addresses]
        return await asyncio.gather(*tasks, return_exceptions=True)
