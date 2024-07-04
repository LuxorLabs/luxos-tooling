"""user facing functions for normal use"""

from __future__ import annotations

import asyncio
import dataclasses as dc
import functools
import traceback
from typing import Any, Awaitable, Callable

import luxos.misc
from luxos.asyncops import rexec, validate  # noqa: F401

# we bring here functions from other modules
from luxos.exceptions import MinerCommandTimeoutError
from luxos.ips import ip_ranges, load_ips_from_csv  # noqa: F401
from luxos.syncops import execute_command  # noqa: F401

# + LuxosLaunchBaseResult
#    + LuxosLaunchResult
#    + LuxosLaunchError
#       + LuxosLaunchTimeoutError


@dc.dataclass
class LuxosLaunchBaseResult:
    host: str
    port: int

    @property
    def address(self):
        return f"{self.host}:{self.port}"


@dc.dataclass
class LuxosLaunchResult(LuxosLaunchBaseResult):
    data: Any = None


@dc.dataclass
class LuxosLaunchError(LuxosLaunchBaseResult):
    traceback: str | None = None
    brief: str = ""


@dc.dataclass
class LuxosLaunchTimeoutError(LuxosLaunchError, asyncio.TimeoutError):
    pass


async def launch(
    addresses: list[tuple[str, int]],
    function: Callable[[str, int], Awaitable[Any]],
    batch: int = 0,
    asobj: bool = False,
) -> list[LuxosLaunchError | LuxosLaunchTimeoutError | Any]:
    """
    Launch an async function on a list of (host, port) miners.

    This function takes a list of (host, port) tuples (points) to
    miners, and for each "point" call `function` on it.

    Arguments:
        addresses: list of (host: str, port: int)
        function: async callable with (host: str, port: int) call signature
        batch: limit the number of concurrent calls (unlimited by default)
        asobj: if True all results will be instances subclasses
               of LuxosLaunchBaseResult

    Examples:
        This will gather the miners versions in a dict::

            async printme(host: str, port: int):
                res = await rexec(host, port, "version"))
            addresses = load_ips_from_csv("miners.csv")
            asyncio.run(launch(addresses, printme))


    """

    def wraps(fn):
        @functools.wraps(fn)
        async def _fn(host: str, port: int):
            out = None
            try:
                data = await fn(host, port)
                out = LuxosLaunchResult(host, port, data) if asobj else data
            except (asyncio.TimeoutError, MinerCommandTimeoutError) as exc:
                tback = "".join(traceback.format_exc())
                brief = repr(exc.__context__ or exc.__cause__)
                out = LuxosLaunchTimeoutError(host, port, traceback=tback, brief=brief)
            except Exception as exc:
                tback = "".join(traceback.format_exc())
                brief = repr(exc.__context__ or exc.__cause__)
                out = LuxosLaunchError(host, port, traceback=tback, brief=brief)
            return out

        return _fn

    call = wraps(function)
    if batch:
        result = []
        for subaddresses in luxos.misc.batched(addresses, batch):
            tasks = [call(*address) for address in subaddresses]
            result.extend(await asyncio.gather(*tasks, return_exceptions=True))
        return result
    else:
        tasks = [call(*address) for address in addresses]
        return await asyncio.gather(*tasks, return_exceptions=True)
