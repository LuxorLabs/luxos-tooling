from __future__ import annotations

import asyncio
import json

from .. import asyncops, misc, text


async def run(
    ipaddresses: list[str],
    port: int,
    cmd: str,
    params: list[str],
    timeout: float,
    delay: float | None,
    details: bool,
    batchsize: int = 0,
) -> None:
    result = {}
    batchsize = max(batchsize, 2)

    for grupid, addresses in enumerate(
        misc.batched([(ip, port) for ip in ipaddresses], n=batchsize)
    ):
        tasks = []
        for host, port in addresses:
            tasks.append(
                asyncops.execute_command(
                    host, port, timeout, cmd, params, add_address=True
                )
            )
        result[grupid] = await asyncio.gather(*tasks, return_exceptions=True)

        # runs only on batchsize, wait delay then proceed onto the next batch
        if delay:
            await asyncio.sleep(delay)

    alltasks = [task for group in result.values() for task in group]
    successes = [task for task in alltasks if not isinstance(task, Exception)]
    failures = [task for task in alltasks if isinstance(task, Exception)]

    # print a nice report
    print(f"task executed sucessfully (use -a|--all for details): {len(successes)}")
    if details:
        for (host, port), task in successes:  # type: ignore
            print(f"  > {host}:{port}")
            print(text.indent(json.dumps(task, indent=2, sort_keys=True), pre="  | "))
    print(f"task executed failures: {len(failures)}")
    for failure in failures:
        print(f"  {failure}")


def main(*args, **kwargs) -> None:
    asyncio.run(run(*args, **kwargs))
