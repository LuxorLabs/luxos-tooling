from __future__ import annotations
import asyncio
import os
import csv
import json
import time
import socket
import logging
import argparse
import ipaddress
import threading
from typing import Any

from luxos.api import logon_required

log = logging.getLogger(__name__)


# internal_send_cgminer_command sends a command to the cgminer API server and returns the response.
def internal_send_cgminer_command(
    host: str, port: int, command: str, timeout_sec: int, verbose: bool
) -> dict[str, Any]:
    # Create a socket connection to the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            # set timeout
            sock.settimeout(timeout_sec)

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


# send_cgminer_command sends a command to the cgminer API server and returns the response.
def send_cgminer_command(
    host: str, port: int, cmd: str, param: str, timeout: int, verbose: bool
) -> dict[str, Any]:
    req = str(f'{{"command": "{cmd}", "parameter": "{param}"}}\n')
    log.debug(f"Executing command: {cmd} with params: {param} to host: {host}")

    return internal_send_cgminer_command(host, port, req, timeout, verbose)


# send_cgminer_simple_command sends a command with no params to the miner and returns the response.
def send_cgminer_simple_command(
    host: str, port: int, cmd: str, timeout: int, verbose: bool
) -> dict[str, Any]:
    req = str(f'{{"command": "{cmd}"}}\n')
    log.debug(f"Executing command: {cmd} to host: {host}")
    return internal_send_cgminer_command(host, port, req, timeout, verbose)


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
                f"error: unexpected number of {structure} in response; min: {min}, max: {max}, actual: {len(res[structure])}"
            )

    # Should we check only min?
    if min >= 0:
        # Check the minimum number of structure elements.
        if len(res[structure]) < min:
            raise ValueError(
                f"error: unexpected number of {structure} in response; min: {min}, max: {max}, actual: {len(res[structure])}"
            )

    # Should we check only max?
    if max >= 0:
        # Check the maximum number of structure elements.
        if len(res[structure]) < min:
            raise ValueError(
                f"error: unexpected number of {structure} in response; min: {min}, max: {max}, actual: {len(res[structure])}"
            )

    return res


# get_str_field tries to get the field as a string and returns it.
def get_str_field(struct: dict[str, Any], name: str) -> str:
    try:
        s = str(struct[name])
    except Exception as e:
        raise ValueError(f"error: invalid {name} str field: {e}")

    return s


def logon(host: str, port: int, timeout: int, verbose: bool) -> str:
    # Send 'logon' command to cgminer and get the response
    res = send_cgminer_simple_command(host, port, "logon", timeout, verbose)

    # Check if the response has the expected structure
    check_res_structure(res, "SESSION", 1, 1)

    # Extract the session data from the response
    session = res["SESSION"][0]

    # Get the 'SessionID' field from the session data
    s = get_str_field(session, "SessionID")

    # If 'SessionID' is empty, raise an error indicating invalid session id
    if s == "":
        raise ValueError("error: invalid session id")

    # Return the extracted 'SessionID'
    return s


def add_session_id_parameter(session_id, parameters):
    # Add the session id to the parameters
    return [session_id, *parameters]


def parameters_to_string(parameters):
    # Convert the parameters to a string that LuxOS API accepts
    return ",".join(parameters)


def generate_ip_range(start_ip: str, end_ip: str) -> list[str]:
    # Generate a list of IP addresses from the start and end IP
    start = ipaddress.IPv4Address(start_ip)
    end = ipaddress.IPv4Address(end_ip)

    ip_list = []

    while start <= end:
        ip_list.append(str(start))
        start += 1

    return ip_list


def load_ip_list_from_csv(csv_file: str) -> list[str]:
    # Check if file exists
    if not os.path.exists(csv_file):
        logging.info(f"Error: {csv_file} file not found.")
        exit(1)

    # Load the IP addresses from the CSV file
    ip_list = []
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            # skip commented lines
            if row and row[0].strip().startswith("#"):
                continue
            if i == 0 and row and row[0] == "hostname":
                continue
            if row:  # Ignore empty rows
                ip_list.extend(row)
    return ip_list


def execute_command(
    host: str, port: int, timeout_sec: int, cmd: str, parameters: list, verbose: bool
):
    # Check if logon is required for the command
    logon_req = logon_required(cmd)

    try:
        if logon_req:
            # Get a SessionID
            sid = logon(host, port, timeout_sec, verbose)
            # Add the SessionID to the parameters list at the left.
            parameters = add_session_id_parameter(sid, parameters)

            log.debug("Command requires a SessionID, logging in for host: %s", host)
            log.info("SessionID obtained for %s: %s", host, sid)

        # TODO verify this
        elif not logon_required:  # type: ignore
            log.debug("Logon not required for executing %s", cmd)

        # convert the params to a string that LuxOS API accepts
        param_string = parameters_to_string(parameters)

        log.debug("%s on %s with parameters: %s", cmd, host, param_string)

        # Execute the API command
        res = send_cgminer_command(host, port, cmd, param_string, timeout_sec, verbose)

        log.debug(res)

        # Log off to terminate the session
        if logon_req:
            send_cgminer_command(host, port, "logoff", sid, timeout_sec, verbose)

        return res

    except Exception:
        log.exception("Error executing %s on %s", cmd, host)


def main():
    # define arguments
    parser = argparse.ArgumentParser(description="LuxOS CLI Tool")
    parser.add_argument("--range_start", required=False, help="IP start range")
    parser.add_argument("--range_end", required=False, help="IP end range")
    parser.add_argument(
        "--ipfile",
        required=False,
        default="ips.csv",
        help="File name to store IP addresses",
    )
    parser.add_argument("--cmd", required=True, help="Command to execute on LuxOS API")
    parser.add_argument(
        "--params",
        required=False,
        default=[],
        nargs="+",
        help="Parameters for LuxOS API",
    )
    parser.add_argument(
        "--max_threads",
        required=False,
        default=10,
        type=int,
        help="Maximum number of threads to use. Default is 10.",
    )
    parser.add_argument(
        "--timeout",
        required=False,
        default=3,
        type=int,
        help="Timeout for network scan in seconds",
    )
    parser.add_argument(
        "--port", required=False, default=4028, type=int, help="Port for LuxOS API"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--batch_delay",
        required=False,
        default=0,
        type=int,
        help="Delay between batches in seconds",
    )
    parser.add_argument(
        "--async",
        dest="async_engine",
        action="store_true",
        help="enable the new async engine",
    )
    parser.add_argument(
        "-a",
        "--all",
        dest="details",
        action="store_true",
        help="show full result output",
    )

    # parse arguments
    args = parser.parse_args()
    args.error = parser.error

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("LuxOS-CLI.log")],
    )

    # set timeout to milliseconds
    timeout_sec = args.timeout

    # check if IP address range or CSV with list of IP is provided
    if args.range_start and args.range_end:
        ip_list = generate_ip_range(args.range_start, args.range_end)
    elif args.ipfile:
        ip_list = load_ip_list_from_csv(args.ipfile)
    else:
        args.error("No IP address or IP list found.")

    # Set max threads to use, minimum of max threads and number of IP addresses
    max_threads = min(args.max_threads, len(ip_list))

    # Set start time
    start_time = time.monotonic()

    if args.async_engine:
        from . import async_luxos

        asyncio.run(
            async_luxos.run(
                ipaddresses=ip_list,
                port=args.port,
                cmd=args.cmd,
                params=args.params,
                timeout=timeout_sec,
                delay=args.batch_delay,
                details=args.details,
                batchsize=args.max_threads,
            )
        )

        # TODO remove this duplicate code
        end_time = time.monotonic()
        execution_time = end_time - start_time
        log.info(f"Execution completed in {execution_time:.2f} seconds.")
        return

    # Create a list of threads
    threads = []

    # Iterate over the IP addresses
    for ip in ip_list:
        # create new thread for each IP address
        thread = threading.Thread(
            target=execute_command,
            args=(ip, args.port, timeout_sec, args.cmd, args.params, args.verbose),
        )

        # start the thread
        threads.append(thread)
        thread.start()

        # Limit the number of concurrent threads
        if len(threads) >= max_threads:
            # Wait for the threads to finish
            for thread in threads:
                thread.join()

            # Introduce the batch delay if specified
            if args.batch_delay > 0:
                print(f"Waiting {args.batch_delay} seconds")
                time.sleep(args.batch_delay)

            # Clear the thread list for the next batch
            threads = []

    # Wait for the remaining threads to finish
    for thread in threads:
        thread.join()

    # Execution completed
    end_time = time.monotonic()
    execution_time = end_time - start_time
    log.info(f"Execution completed in {execution_time:.2f} seconds.")


if __name__ == "__main__":
    main()
