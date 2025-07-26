from __future__ import annotations

import asyncio
import contextlib
import functools
import json
import logging
from typing import Any

from . import api, exceptions

log = logging.getLogger(__name__)

#: default timeout (s) for operations
TIMEOUT = 3.0
#: default number (>1) of retries on a failed operation
RETRIES = 0
#: delay (s) between retries
RETRIES_DELAY = 1.0


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
        print(await _roundtrip(host, port, "version"))
        -> (str) "{'STATUS': [{'Code': 22, 'Description'...."
    """
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port), timeout
    )

    writer.write(cmd.encode() if isinstance(cmd, str) else cmd)
    await writer.drain()

    response = bytearray()
    while True:
        data = await asyncio.wait_for(reader.read(8), timeout=timeout)
        if not data:
            break
        delimiter = data.find(b"\x00")
        if delimiter >= 0:
            response += data[:delimiter]
            break
        response += data

    return response.decode()


# TODO add annotations
async def roundtrip(
    host: str,
    port: int,
    cmd: bytes | str | dict[str, Any],
    asjson: bool | None = True,
    timeout: float | None = None,
    retry: int | None = 0,
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
    retry = RETRIES if retry is None else retry
    retry_delay = RETRIES_DELAY if retry_delay is None else retry_delay

    if not isinstance(cmd, (bytes, str)):
        cmd = json.dumps(cmd, indent=2, sort_keys=True)
        if asjson is None:
            asjson = True

    last_exception = None
    for _ in range(max(retry, 1)):
        try:
            res = await _roundtrip(host, port, cmd, timeout)
            if asjson:
                return json.loads(res.strip())
            else:
                return res
        except (Exception, asyncio.TimeoutError) as e:
            last_exception = e
        if retry and retry_delay:
            await asyncio.sleep(retry_delay)

    if last_exception is not None:
        raise exceptions.MinerCommandTimeoutError(host, port) from last_exception


def validate_message(
    host: str,
    port: int,
    res: dict[str, Any],
    extrakey: str | None = None,
    minfields: None | int = 1,
    maxfields: None | int = 1,
) -> Any:
    # all miner message comes with a STATUS
    for key in ["STATUS", "id"]:
        if key in res:
            continue
        raise exceptions.MinerCommandMalformedMessageError(
            host, port, f"missing {key} from message STATUS", res
        )

    # no further validation here
    if not extrakey:
        return res

    if not res["STATUS"] or not res["STATUS"][0].get("STATUS") == "S":
        raise exceptions.MinerCommandMalformedMessageError(
            host, port, "no status information in message", res
        )

    # TODO if minfield is 0, there might not be extrakey
    if minfields == 0 and extrakey not in res:
        return []

    if extrakey not in res:
        if not minfields:
            return []
        raise exceptions.MinerCommandMalformedMessageError(
            host, port, f"missing {extrakey} from message", res
        )

    n = len(res[extrakey])
    msg = None

    cond = ""
    if minfields is not None and maxfields is None:
        cond = f" ({n} < {minfields})"
    elif minfields is None and maxfields is not None:
        cond = f" ({n} > {maxfields})"
    elif minfields is not None and maxfields is not None:
        if n > maxfields:
            cond = f" ({n} > {maxfields})"
        else:
            cond = f" ({n} < {minfields})"

    if (minfields is not None) and (n < minfields):
        msg = f"found too few items for '{extrakey}' {cond}"
    elif (maxfields is not None) and (n > maxfields):
        msg = f"found too many items for '{extrakey}' {cond}"
    if msg is None:
        return res
    raise exceptions.MinerCommandMalformedMessageError(host, port, msg, res)


def validate(
    res: dict[str, Any],
    extrakey: str | None = None,
    minfields: None | int = None,
    maxfields: None | int = None,
) -> Any:
    """
    Validate a message returned from a miner.

    Args:
        res: The dictionary returned from a miner.
        extrakey: if present it will try to extract it from res.
        cmd: A string representing the command to execute.
        minfields: The min length of the field extrakey.
        maxfields: The max length of the field extrakey.

    Returns:
        A dictionary containing the response from the execution of the
        command if extrakey is None, else a dict or a list of items.

    Raises:

        RuntimeError: if minfield > maxfield (internal error).
        MinerMessageMalformedError: the res dict is missing either
            'STATUS' or 'id' keys.
        MinerMessageError: the message is well formed but STATUS is not `S`.
        MinerMessageMalformedError: the res[extrakey] is not a list
        MinerMessageInvalidError: the message is missing `extarkey` or
            the len(res[extrakey]) is not valid.
    """

    if minfields is not None and maxfields is not None:
        if minfields > maxfields:
            raise RuntimeError(f"invalid arguments: {minfields=} > {maxfields=}")
    # all miner message comes with a STATUS
    for key in ["STATUS", "id"]:
        if key in res:
            continue
        raise exceptions.MinerMessageMalformedError(
            f"missing {key} from message STATUS", res
        )

    # no further validation here
    if not extrakey:
        return res

    if (status := res["STATUS"][0].get("STATUS")) != "S":
        raise exceptions.MinerMessageError(
            f"wrong status '{status}' in message (expected S)", res
        )
    # ok, when there aren't pools, the POOLS command
    # doesn't add a 'POOLS': [] item
    if extrakey not in res and not minfields:
        return None

    if extrakey not in res:
        raise exceptions.MinerMessageInvalidError(
            f"missing {extrakey} from message", res
        )

    values = res[extrakey]
    if not isinstance(values, list):
        raise exceptions.MinerMessageMalformedError(
            f"message reply doesn't contain list in '{extrakey}'", res
        )

    n = len(values)
    msg = None

    cond = ""
    if minfields is not None and maxfields is None:
        cond = f" ({n} < {minfields})"
    elif minfields is None and maxfields is not None:
        cond = f" ({n} > {maxfields})"
    elif minfields is not None and maxfields is not None:
        if n > maxfields:
            cond = f" ({n} > {maxfields})"
        else:
            cond = f" ({n} < {minfields})"

    if (minfields is not None) and (n < minfields):
        msg = f"found too few items for '{extrakey}' {cond}"
    elif (maxfields is not None) and (n > maxfields):
        msg = f"found too many items for '{extrakey}' {cond}"
    if msg is not None:
        raise exceptions.MinerMessageInvalidError(msg, res)

    if isinstance(values, list):
        ones = (len(values), minfields, maxfields)
        if ones == (1, 1, 1):
            return values[0]
    return values


@wrapped
async def logon(host: str, port: int, timeout: float | None = None) -> str:
    timeout = TIMEOUT if timeout is None else timeout
    res = await roundtrip(host, port, {"command": "logon"}, timeout=timeout)

    # when we first logon, we'll receive a token (session_id)
    #   [STATUS][SessionID]
    # on subsequent logon, we receive a
    #   [STATUS][Msg] == "Another session is active" ([STATUS][Code] 402)
    if "SESSION" not in res and res.get("STATUS", [{}])[0].get("Code") == 402:
        raise exceptions.MinerCommandSessionAlreadyActive(
            host, port, "connection active", res
        )
    sessions = validate_message(host, port, res, "SESSION", 1, 1)["SESSION"]

    session = sessions[0]

    if "SessionID" not in session:
        raise exceptions.MinerCommandSessionAlreadyActive(
            host, port, "no SessionID in data", res
        )
    return str(session["SessionID"])


@wrapped
async def logoff(
    host: str, port: int, sid: str, timeout: float | None = None
) -> dict[str, Any]:
    timeout = TIMEOUT if timeout is None else timeout
    return await roundtrip(
        host, port, {"command": "logoff", "parameter": sid}, timeout=timeout
    )


def parameters_to_list(
    parameters: str | int | float | bool | list[Any] | dict[str, Any] | None = None,
) -> list[str]:
    if isinstance(parameters, dict):
        data = []
        for key, value in parameters.items():
            if value is None:
                value = "null"
            elif value is True:
                value = "true"
            elif value is False:
                value = "false"
            data.append(f"{key}={value}")
        parameters = data
    parameters = (
        [parameters] if isinstance(parameters, (int, float, str)) else parameters
    ) or []
    parameters = [str(param) for param in parameters]
    return parameters


async def rexec(
    host: str,
    port: int,
    cmd: str,
    parameters: str | int | float | bool | list[Any] | dict[str, Any] | None = None,
    timeout: float | None = None,
    retry: int | None = None,
    retry_delay: float | None = None,
) -> dict[str, Any]:
    """
    Send a command to a host.

    Args:
        host: A string representing the host IP or a name.
        port: An integer representing the port number to connect to.
        cmd: A string representing the command to execute.
        parameters: Any additional parameters for the command.
        timeout: A float representing the maximum time in seconds to
            wait for a response before timing out.
        retry: Optional. An integer representing the number of times
            to retry the command execution in case of failure.
        retry_delay: Optional. A float representing the delay in seconds
            between each retry attempt.

    Returns:
        A dictionary containing the response from the execution of the command.

    Raises:
        Any exception that occurs during the execution of the command.

    Notes:
        If `timeout`/`retry`/`retry_delay` aren't provided (or None),
        they will default to the module level values
        (:py:data:`TIMEOUT`, :py:data:`RETRIES`, and :py:data:`RETRIES_DELAY`).

        This function will handle logon/logoff automatically.

    """

    parameters = parameters_to_list(parameters)

    timeout = TIMEOUT if timeout is None else timeout
    retry = RETRIES if retry is None else retry
    retry_delay = RETRIES_DELAY if retry_delay is None else retry_delay

    # if cmd is logon/logoff we dealt with it differently
    if cmd in {"logon", "logoff"}:
        failure = None
        for i in range(retry or 1):
            try:
                if cmd == "logon":
                    return {"sid": await logon(host, port, timeout)}
                else:
                    return await logoff(host, port, parameters[0])
            except Exception as exc:
                failure = exc
            if retry and (i < retry) and retry_delay:
                await asyncio.sleep(retry_delay)
        if isinstance(failure, Exception):
            raise failure

    failure = None
    sid = ""
    for i in range(retry + 1):
        if not api.logon_required(cmd):
            log.debug("no logon required for command '%s' on %s:%i", cmd, host, port)
            break
        try:
            sid = await logon(host, port, timeout)
            parameters = [sid, *parameters]
            log.debug("session id requested & obtained for %s:%i (%s)", host, port, sid)
            break
        except Exception as exc:
            failure = exc
        if retry and (i < retry) and retry_delay:
            await asyncio.sleep(retry_delay)

    if isinstance(failure, Exception):
        raise failure

    packet = {"command": cmd}
    if parameters:
        packet["parameter"] = ",".join(parameters)
    log.debug(
        "executing command '%s' on '%s:%i' with parameters: %s",
        cmd,
        host,
        port,
        packet.get("parameter", ""),
    )

    failure = None
    for i in range(retry + 1):
        try:
            ret = await roundtrip(host, port, packet, timeout=timeout)
            log.debug("received from %s:%s: %s", host, port, str(ret))
            if sid:
                await logoff(host, port, sid)
            return ret
        except Exception as exc:
            failure = exc
        if retry and (i < retry) and retry_delay:
            log.debug("failed attempt %i (out of %i)", i + 1, retry)
            await asyncio.sleep(retry_delay)

    if sid:
        await logoff(host, port, sid)
    if isinstance(failure, Exception):
        raise failure
    return {}


@contextlib.asynccontextmanager
async def with_atm(host, port, enabled: bool, timeout: float | None = None):
    res = await rexec(host, port, "atm", timeout=timeout)
    if not res:
        raise exceptions.MinerConnectionError(host, port, "cannot check atm")
    current = validate_message(host, port, res, "ATM")["ATM"][0]["Enabled"]
    await rexec(host, port, "atmset", {"enabled": enabled}, timeout=timeout)
    # TODO
    yield current
    await rexec(host, port, "atmset", {"enabled": current}, timeout=timeout)
