from __future__ import annotations

import contextlib
import json
import logging
import socket
from typing import Any

from luxos.api import logon_required

from .asyncops import TIMEOUT, parameters_to_list, validate_message
from .exceptions import MinerCommandSessionAlreadyActive, MinerConnectionError

log = logging.getLogger(__name__)


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


def logon(host: str, port: int, timeout: float | None = None) -> str:
    # Send 'logon' command to cgminer and get the response
    timeout = TIMEOUT if timeout is None else timeout
    res = send_cgminer_simple_command(host, port, "logon", timeout)
    if res["STATUS"][0]["STATUS"] == "E":
        raise MinerCommandSessionAlreadyActive(host, port, res["STATUS"][0]["Msg"])
    # Check if the response has the expected structure
    session = validate_message(host, port, res, "SESSION")[0]
    return str(session["SessionID"])


def logoff(
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
        sid = logon(host, port, timeout_sec)
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
        logoff(host, port, sid, timeout_sec)

    return res


def rexec(
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
    current = validate_message(host, port, res, "ATM")[0]["Enabled"]
    rexec(host, port, "atmset", {"enabled": enabled}, timeout=timeout)
    yield current
    rexec(host, port, "atmset", {"enabled": current}, timeout=timeout)
