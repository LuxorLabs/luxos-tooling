from __future__ import annotations

import functools
import logging
import asyncio
import json

from typing import Any

from . import exceptions
from . import api


log = logging.getLogger(__name__)

TIMEOUT = 3.0  # default timeout for operations


def wrapped(function):
    """wraps a function acting on a host and re-raise with internal exceptions

    This re-raise exceptions so they all derive from MinerConnectionError, eg:
    @wrapped
    def somcode(host: str, port: int, ...):
        ...

    try:
        await somecode()
    except MinerConnectionError as e:  <- this will catch all exceptions!
        e.address
        raise MyNewExecption() from e  <- this will re-raise
    """
    @functools.wraps(function)
    async def _function(host: str, port: int, *args, **kwargs):
        try:
            return await function(host, port, *args, **kwargs)
        except asyncio.TimeoutError as e:
            # we augment underlying TimeOuts
            raise exceptions.MinerCommandTimeoutError(host, port) from e
        except exceptions.MinerConnectionError:
            raise
        except Exception as e:
            # we augment any other exception with (host, port) info
            log.exception("internal error")
            raise exceptions.MinerConnectionError(host, port, "internal error") from e
    return _function


async def _roundtrip(
    host: str, port: int, cmd: bytes | str, timeout: float | None
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

# TODO add annotations
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
        print(await roundtrip(host, port, {"version"}))
        -> (json) {'STATUS': [{'Code': 22, 'Description': 'LUXminer 20 ...
        print(await roundtrip(host, port, "version"))
        -> (str) "{'STATUS': [{'Code': 22, 'Description': 'LUXminer 20 ..
    """
    timeout = TIMEOUT if timeout is None else timeout
    count = 0

    if not isinstance(cmd, (bytes, str)):
        cmd = json.dumps(cmd, indent=2, sort_keys=True)
        if asjson is None:
            asjson = True

    last_exception = None
    while count <= retry:
        try:
            timeout = TIMEOUT if timeout is None else timeout
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
    host: str,
    port: int,
    res: dict[str, Any],
    extrakey: str | None = None,
    minfields: None | int = None,
    maxfields: None | int = None,
) -> dict[str, Any]:
    # all miner message comes with a STATUS
    for key in ["STATUS", "id", *([extrakey] if extrakey else [])]:
        if key in res:
            continue
        raise exceptions.MinerCommandMalformedMessageError(host, port, f"missing {key} from logon message", res)

    if not extrakey or not (minfields or maxfields):
        return res

    n = len(res[extrakey])
    msg = None
    if minfields and (n < minfields):
        msg = f"found {n} fields for {extrakey} invalid: " f"{n} <= {minfields}"
    elif maxfields and (n > maxfields):
        msg = f"found {n} fields for {extrakey} invalid: " f"{n} >= {maxfields}"
    if msg is None:
        return res[extrakey]
    raise exceptions.MinerCommandMalformedMessageError(host, port, msg, res)


@wrapped
async def logon(host: str, port: int, timeout: float | None = 3) -> str:
    timeout = TIMEOUT if timeout is None else timeout
    res = await roundtrip(host, port, {"command": "logon"}, timeout)

    # when we first logon, we'll receive a token (session_id)
    #   [STATUS][SessionID]
    # on subsequent logon, we receive a
    #   [STATUS][Msg] == "Another session is active" ([STATUS][Code] 402)
    if "SESSION" not in res and res.get("STATUS", [{}])[0].get("Code") == 402:
        raise exceptions.MinerCommandSessionAlreadyActive(host, port, "connection active", res)
    sessions = validate_message(host, port, res, "SESSION", 1, 1)

    session = sessions[0]  # type: ignore

    if "SessionID" not in session:
        raise exceptions.MinerCommandSessionAlreadyActive(host, port, "no SessionID in data", res)
    return str(session["SessionID"])


@wrapped
async def logoff(
    host: str, port: int, sid: str, timeout: float | None = 3
) -> dict[str, Any]:
    timeout = TIMEOUT if timeout is None else timeout
    return await roundtrip(host, port, {"command": "logoff", "parameter": sid}, timeout)


@wrapped
async def execute_command(
    host: str,
    port: int,
    timeout_sec: float | None,
    cmd: str,
    parameters: list[str] | None = None,
    verbose: bool = False,
    asjson: bool | None = True,
    add_address: bool = False
) -> tuple[tuple[str, int], dict[str, Any]] | dict[str, Any]:
    timeout = TIMEOUT if timeout_sec is None else timeout_sec
    parameters = parameters or []

    sid = None
    if api.logon_required(cmd):
        sid = await logon(host, port)
        parameters = [sid, *parameters]
        log.info("session id requested & obtained for %s:%i (%s)", host, port, sid)
    else:
        log.debug("no logon required for command %s on %s:%i", cmd, host, port)

    try:
        packet = {"command": cmd}
        if parameters:
            packet["parameter"] = ",".join(parameters)
        ret = await roundtrip(host, port, packet, timeout, asjson=asjson)
        return ((host, port), ret) if add_address else ret
    finally:
        if sid:
            await logoff(host, port, sid)
