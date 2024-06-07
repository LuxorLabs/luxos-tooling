from __future__ import annotations

import asyncio
import dataclasses as dc
import json
import traceback
from typing import Any

from .. import asyncops, misc, text


@dc.dataclass
class Result:
    host: str
    port: int
    tback: str = ""
    value: Any = None


async def wrapper(fn, host: str, port: int, *args, **kwargs) -> Result:
    try:
        return Result(host, port, value=await fn(host, port, *args, **kwargs))
    except asyncio.TimeoutError:
        return Result(host, port, tback="timeout error")
    except Exception:
        return Result(host, port, tback="".join(traceback.format_exc()))


async def run(
    ipaddresses: list[tuple[str, int]],
    cmd: str,
    params: list[str] | dict[str, str] | None,
    delay: float | None,
    details: str,
    batchsize: int = 0,
) -> None:
    result = {}

    for grupid, addresses in enumerate(misc.batched(ipaddresses, n=batchsize)):
        tasks = []
        for host, port in addresses:
            tasks.append(wrapper(asyncops.rexec, host, port, cmd, params))
        result[grupid] = await asyncio.gather(*tasks)

        # runs only on batchsize, wait delay then proceed onto the next batch
        if delay:
            await asyncio.sleep(delay)

    alltasks = [task for group in result.values() for task in group]
    successes = [task for task in alltasks if not task.tback]
    failures = [task for task in alltasks if task.tback]

    # print a nice report
    if details == "json":
        output = {}
        for task in successes:
            output[f"{task.host}:{task.port}"] = {"status": True, "result": task.value}
        for task in failures:
            output[f"{task.host}:{task.port}"] = {"status": False, "result": task.tback}
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        if details:
            print(f"task executed sucessfully: {len(successes)}")
            for task in successes:
                print(f"  > {task.host}:{task.port}")
                print(
                    text.indent(
                        json.dumps(task.value, indent=2, sort_keys=True), pre="  | "
                    )
                )
        else:
            print(
                f"task executed sucessfully (use -a|--all for details): "
                f"{len(successes)}"
            )

        if details:
            print(f"task executed with failures: {len(failures)}")
            for task in failures:
                print(f"  {task.host}:{task.port}:")
                print(f"  {text.indent(task.tback, '| ')}")
        else:
            print(
                f"task executed with failures (use -a|--all for details): "
                f"{len(failures)}"
            )


def main(*args, **kwargs) -> None:
    asyncio.run(run(*args, **kwargs))
