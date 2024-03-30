import sys
import asyncio
import itertools
import json

from typing import Any

from . import exceptions


if sys.version_info >= (3, 12):
    batched = itertools.batched
else:

    def batched(iterable, n):
        if n < 1:
            raise ValueError("n must be at least one")
        it = iter(iterable)
        while batch := tuple(itertools.islice(it, n)):
            yield batch


async def _roundtrip(
    host: str, port: int, cmd: bytes | str, timeout: float | None = None
) -> str:
    """simple asyncio socket based send/receive function

    Example:
        print(await _roundtrip(host, port, version))
        -> (str) "{'STATUS': [{'Code': 22, 'Description'...."
    """
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port), timeout
    )

    writer.write(cmd.encode() if isinstance(cmd, str) else cmd)
    await writer.drain()

    response = bytearray()
    while True:
        data = await asyncio.wait_for(reader.read(1), timeout=timeout)
        if not data:
            break
        null_index = data.find(b"\x00")
        if null_index >= 0:
            response += data[:null_index]
            break
        response += data

    return response.decode()


async def roundtrip(
    host: str,
    port: int,
    cmd: bytes | str | dict[str, Any],
    timeout: float | None = None,
    asjson: bool | None = True,
    retry: int = 0,
    retry_delay: float | None = None,
):
    """utility wrapper around _roundrip

    Example:
        print(await roundtrip(host, port, {"version))
        -> (json) {'STATUS': [{'Code': 22, 'Description': 'LUXminer 20 ...
    """
    count = 0

    if not isinstance(cmd, (bytes, str)):
        cmd = json.dumps(cmd, indent=2, sort_keys=True)
        if asjson is None:
            asjson = True

    last_exception = None
    while count <= retry:
        try:
            res = await _roundtrip(host, port, cmd, timeout)
            if asjson:
                return json.loads(res)
            else:
                return res
        except (Exception, asyncio.TimeoutError) as e:
            last_exception = e
        if retry_delay:
            await asyncio.sleep(retry_delay)
        count += 1
    if last_exception is not None:
        raise last_exception


def validate_message(
    res: dict[str, Any],
    extrakey: str | None = None,
    minfields: None | int = None,
    maxfields: None | int = None,
) -> dict[str, Any]:
    # all miner message comes with a STATUS
    for key in ["STATUS", "id", *([extrakey] if extrakey else [])]:
        if key in res:
            continue
        raise exceptions.MinerMalformedMessageError(f"missing {key}", res)

    if not extrakey or not (minfields or maxfields):
        return res

    n = len(res[extrakey])
    msg = None
    if minfields and (n < minfields):
        msg = (f"found {n} fields for {extrakey} invalid: "
               f"{n} <= {minfields}")
    elif maxfields and (n > maxfields):
        msg = (f"found {n} fields for {extrakey} invalid: "
               f"{n} >= {maxfields}")
    if msg is None:
        return res[extrakey]
    raise exceptions.MinerMalformedMessageError(msg, res)


async def logon(host: str, port: int, timeout: float | None = 3) -> str:
    res = await roundtrip(host, port, {"command": "logon"}, timeout)

    # when we first logon, we'll receive a token (session_id)
    #   [STATUS][SessionID]
    # on subsequent logon, we receive a
    #   [STATUS][Msg] == "Another session is active" ([STATUS][Code] 402)

    sessions = validate_message(res, "SESSION", 1, 1)
    session = sessions[0]  # type: ignore

    if "SessionID" not in session:
        raise exceptions.MinerSessionAlreadyActive("no SessionID in data", res)
    return str(session["SessionID"])


async def logoff(host: str, port: int, sid: str, timeout: float | None = 3) -> dict[str,Any]:
    return await roundtrip(host, port, {"command": "logoff", "parameter": sid}, timeout)
