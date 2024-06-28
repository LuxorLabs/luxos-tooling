from __future__ import annotations

import contextlib
import functools
import json
import logging
import socket
import time
from typing import Any

from luxos.api import logon_required

from . import exceptions
from .asyncops import (
    RETRIES,
    RETRIES_DELAY,
    TIMEOUT,
    parameters_to_list,
    validate,  # noqa: F401
    validate_message,
)
from .exceptions import MinerCommandSessionAlreadyActive, MinerConnectionError

log = logging.getLogger(__name__)


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
    def _function(host: str, port: int, *args, **kwargs):
        try:
            return function(host, port, *args, **kwargs)
        except TimeoutError as e:
            # we augment underlying TimeOuts
            raise exceptions.MinerCommandTimeoutError(host, port) from e
        except exceptions.MinerConnectionError:
            raise
        except Exception as e:
            # we augment any other exception with (host, port) info
            log.exception("internal error")
            raise exceptions.MinerConnectionError(host, port, "internal error") from e

    return _function


def retryfn(
    timeout: float, retry: int, retry_delay: float, fn, host, port, *args, **kwargs
):
    """will retry fn calls up to timeout of up to number retry"""
    last_exception = None
    count = retry
    t0 = time.monotonic()
    while True:
        if retry > 0 and count <= 0:
            break
        if timeout and (time.monotonic() - t0) >= timeout:
            break

        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exception = e
        log.debug("failed to retrieve result for '%s'", fn.__name__)

        if retry > 0:
            count -= 1
        if retry and retry_delay:
            time.sleep(retry_delay)

    if last_exception is not None:
        raise exceptions.MinerCommandTimeoutError(host, port) from last_exception


def _roundtrip(
    host: str, port: int, cmd: bytes | str, timeout: float | None = None
) -> str:
    """simple asyncio socket based send/receive function

    Example:
        print(_roundtrip(host, port, "version"))
        -> (str) "{'STATUS': [{'Code': 22, 'Description'...."
    """
    timeout = TIMEOUT if timeout is None else timeout
    # Create a socket connection to the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # set timeout
        if timeout:
            sock.settimeout(timeout)

        # Connect to the server
        sock.connect((host, port))
        log.debug("connecting to %s:%i", host, port)
        # Send the command to the server
        sock.sendall(cmd.encode() if isinstance(cmd, str) else cmd)

        # Receive the response from the server
        response = []
        # Read one byte at a time so we can wait for the null terminator.
        # this is to avoid waiting for the timeout as we don't know how long
        # the response will be and socket.recv() will block until reading
        # the specified number of bytes.
        while data := sock.recv(2**3):
            response.append(data)

        result = "".join(block.decode() for block in response)
        log.debug("received: %s", result)
        return result


def roundtrip(
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
    count = retry
    t0 = time.monotonic()
    while True:
        if retry > 0 and count <= 0:
            break
        if timeout and (time.monotonic() - t0) >= timeout:
            break

        try:
            res = _roundtrip(host, port, cmd, timeout)
            if asjson:
                return json.loads(res)
            else:
                return res
        except Exception as e:
            last_exception = e
        log.debug("failed to retrieve result for '%s'", cmd)

        if retry > 0:
            count -= 1
        if retry and retry_delay:
            time.sleep(retry_delay)

    if last_exception is not None:
        raise exceptions.MinerCommandTimeoutError(host, port) from last_exception


@wrapped
def logon(host: str, port: int, timeout: float | None = None) -> str:
    timeout = TIMEOUT if timeout is None else timeout
    res = roundtrip(host, port, {"command": "logon"}, timeout=timeout)

    # when we first logon, we'll receive a token (session_id)
    #   [STATUS][SessionID]
    # on subsequent logon, we receive a
    #   [STATUS][Msg] == "Another session is active" ([STATUS][Code] 402)
    if "SESSION" not in res and res.get("STATUS", [{}])[0].get("Code") == 402:
        raise exceptions.MinerCommandSessionAlreadyActive(
            host, port, "connection active", res
        )
    sessions = validate_message(host, port, res, "SESSION", 1, 1)

    session = sessions["SESSION"][0]

    if "SessionID" not in session:
        raise exceptions.MinerCommandSessionAlreadyActive(
            host, port, "no SessionID in data", res
        )
    return str(session["SessionID"])


@wrapped
def logoff(
    host: str, port: int, sid: str, timeout: float | None = None
) -> dict[str, Any]:
    timeout = TIMEOUT if timeout is None else timeout
    return roundtrip(
        host, port, {"command": "logoff", "parameter": sid}, timeout=timeout
    )


def rexec(
    host: str,
    port: int,
    cmd: str,
    parameters: str | int | float | bool | list[Any] | dict[str, Any] | None = None,
    timeout: float | None = None,
    retry: int | None = None,
    retry_delay: float | None = None,
) -> dict[str, Any] | None:
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
                    return {"sid": logon(host, port, timeout)}
                else:
                    return logoff(host, port, parameters[0])
            except Exception as exc:
                failure = exc
            if retry and (i < retry) and retry_delay:
                time.sleep(retry_delay)
        if isinstance(failure, Exception):
            raise failure

    failure = None
    sid = ""
    for i in range(retry + 1):
        if not logon_required(cmd):
            log.debug("no logon required for command '%s' on %s:%i", cmd, host, port)
            break
        try:
            sid = logon(host, port, timeout)
            parameters = [sid, *parameters]
            log.debug("session id requested & obtained for %s:%i (%s)", host, port, sid)
            break
        except Exception as exc:
            failure = exc
        if retry and (i < retry) and retry_delay:
            time.sleep(retry_delay)

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
            ret = roundtrip(host, port, packet, timeout=timeout)
            log.debug("received from %s:%s: %s", host, port, str(ret))
            if sid:
                logoff(host, port, sid)
            return ret
        except Exception as exc:
            failure = exc
        if retry and (i < retry) and retry_delay:
            log.debug("failed attempt %i (out of %i)", i + 1, retry)
            time.sleep(retry_delay)

    if sid:
        logoff(host, port, sid)
    if isinstance(failure, Exception):
        raise failure


# !!! LEGACY CODE BELOW !!!


# internal_send_cgminer_command sends a command to the
# cgminer API server and returns the response.
def internal_send_cgminer_command(
    host: str, port: int, command: str, timeout: float | None
) -> dict[str, Any]:
    timeout_sec = TIMEOUT if timeout is None else timeout
    # Create a socket connection to the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            # set timeout
            if timeout_sec is not None:
                sock.settimeout(timeout)

            # Connect to the server
            sock.connect((host, port))

            # Send the command to the server
            sock.sendall(command.encode())

            # Receive the response from the server
            response = bytearray()
            while True:
                # Read one byte at a time so we can wait for the null terminator.
                # this is to avoid waiting for the timeout as we don't know how long
                # the response will be and socket.recv() will block until reading
                # the specified number of bytes.
                try:
                    data = sock.recv(1)
                except socket.timeout:
                    # Timeout occurred, check if we have any data so far
                    if len(response) == 0:
                        raise ValueError("timeout waiting for data")
                    else:
                        break
                if not data:
                    break
                null_index = data.find(b"\x00")
                if null_index >= 0:
                    response += data[:null_index]
                    break
                response += data

            # Parse the response JSON
            r = json.loads(response.decode())
            log.debug(r)
            return r

        except socket.error as e:
            raise e


# send_cgminer_command sends a command to the cgminer API server and
# returns the response.
def send_cgminer_command(
    host: str, port: int, cmd: str, param: str, timeout: float | None = None
) -> dict[str, Any]:
    timeout = TIMEOUT if timeout is None else timeout
    req = str(f'{{"command": "{cmd}", "parameter": "{param}"}}\n')
    log.debug(f"Executing command: {cmd} with params: {param} to host: {host}")
    return internal_send_cgminer_command(host, port, req, timeout)


# send_cgminer_simple_command sends a command with no params
# to the miner and returns the response.
def send_cgminer_simple_command(
    host: str, port: int, cmd: str, timeout: float | None = None
) -> dict[str, Any]:
    timeout = TIMEOUT if timeout is None else timeout
    req = str(f'{{"command": "{cmd}"}}\n')
    log.debug(f"Executing command: {cmd} to host: {host}")
    return internal_send_cgminer_command(host, port, req, timeout)


# check_res_structure checks that the response has the expected structure.
def check_res_structure(
    res: dict[str, Any], structure: str, min: int, max: int
) -> dict[str, Any]:
    # Check the structure of the response.
    if structure not in res or "STATUS" not in res or "id" not in res:
        raise ValueError("error: invalid response structure")

    # Should we check min and max?
    if min >= 0 and max >= 0:
        # Check the number of structure elements.
        if not (min <= len(res[structure]) <= max):
            raise ValueError(
                f"error: unexpected number of {structure} in response; "
                f"min: {min}, max: {max}, actual: {len(res[structure])}"
            )

    # Should we check only min?
    if min >= 0:
        # Check the minimum number of structure elements.
        if len(res[structure]) < min:
            raise ValueError(
                f"error: unexpected number of {structure} in response; "
                f"min: {min}, max: {max}, actual: {len(res[structure])}"
            )

    # Should we check only max?
    if max >= 0:
        # Check the maximum number of structure elements.
        if len(res[structure]) < min:
            raise ValueError(
                f"error: unexpected number of {structure} in response; "
                f"min: {min}, max: {max}, actual: {len(res[structure])}"
            )

    return res


# get_str_field tries to get the field as a string and returns it.
def get_str_field(struct: dict[str, Any], name: str) -> str:
    try:
        s = str(struct[name])
    except Exception as e:
        raise ValueError(f"error: invalid {name} str field: {e}")

    return s


def __logon(host: str, port: int, timeout: float | None = None) -> str:
    # Send 'logon' command to cgminer and get the response
    timeout = TIMEOUT if timeout is None else timeout
    res = send_cgminer_simple_command(host, port, "logon", timeout)
    if res["STATUS"][0]["STATUS"] == "E":
        raise MinerCommandSessionAlreadyActive(host, port, res["STATUS"][0]["Msg"])
    # Check if the response has the expected structure
    session = validate_message(host, port, res, "SESSION")[0]
    return str(session["SessionID"])


def __logoff(
    host: str, port: int, sid: str, timeout: float | None = None
) -> dict[str, Any]:
    timeout = TIMEOUT if timeout is None else timeout
    res = send_cgminer_command(host, port, "logoff", sid, timeout)
    return validate_message(host, port, res)


def add_session_id_parameter(session_id, parameters) -> list[Any]:
    # Add the session id to the parameters
    return [session_id, *parameters]


def parameters_to_string(parameters):
    # Convert the parameters to a string that LuxOS API accepts
    return ",".join(parameters)


def execute_command(
    host: str,
    port: int,
    timeout_sec: int | float | None,
    cmd: str,
    parameters: str | list[Any] | dict[str, Any] | None = None,
    verbose: bool = False,
):
    timeout_sec = TIMEOUT if timeout_sec is None else timeout_sec
    # Check if logon is required for the command
    logon_req = logon_required(cmd)

    parameters = parameters_to_list(parameters)

    if logon_req:
        # Get a SessionID
        sid = __logon(host, port, timeout_sec)
        # Add the SessionID to the parameters list at the left.
        parameters = add_session_id_parameter(sid, parameters)

        log.debug("SessionID obtained for %s: %s", host, sid)

    # TODO verify this
    elif not logon_req:
        log.debug("Logon not required for executing %s", cmd)

    # convert the params to a string that LuxOS API accepts
    param_string = ",".join(parameters)

    log.debug("%s on %s with parameters: %s", cmd, host, param_string)

    # Execute the API command
    res = send_cgminer_command(host, port, cmd, param_string, timeout_sec)

    log.debug(res)

    # Log off to terminate the session
    if logon_req:
        __logoff(host, port, sid, timeout_sec)

    return res


def __rexec(
    host: str,
    port: int,
    cmd: str,
    parameters: str | list[Any] | dict[str, Any] | None = None,
    timeout: float | None = None,
    retry: int | None = None,
    retry_delay: float | None = None,
) -> dict[str, Any] | None:
    if retry or retry_delay:
        raise NotImplementedError("cannot use rexec in suncops with retry!")
    return execute_command(host, port, timeout, cmd, parameters)


@contextlib.contextmanager
def with_atm(host, port, enabled: bool, timeout: float | None = None):
    res = rexec(host, port, "atm", timeout=timeout)
    if not res:
        raise MinerConnectionError(host, port, "cannot check atm")
    current = validate_message(host, port, res, "ATM")["ATM"][0]["Enabled"]
    rexec(host, port, "atmset", {"enabled": enabled}, timeout=timeout)
    yield current
    rexec(host, port, "atmset", {"enabled": current}, timeout=timeout)
