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

COMMANDS = {
    "addgroup": {
        "logon_required": False
    },
    "addpool": {
        "logon_required": False
    },
    "asc": {
        "logon_required": False
    },
    "asccount": {
        "logon_required": False
    },
    "atm": {
        "logon_required": False
    },
    "atmset": {
        "logon_required": True
    },
    "check": {
        "logon_required": False
    },
    "coin": {
        "logon_required": False
    },
    "config": {
        "logon_required": False
    },
    "curtail": {
        "logon_required": True
    },
    "devdetails": {
        "logon_required": False
    },
    "devs": {
        "logon_required": False
    },
    "disablepool": {
        "logon_required": False
    },
    "edevs": {
        "logon_required": False
    },
    "enablepool": {
        "logon_required": False
    },
    "estats": {
        "logon_required": False
    },
    "fans": {
        "logon_required": False
    },
    "fanset": {
        "logon_required": True
    },
    "frequencyget": {
        "logon_required": False
    },
    "frequencyset": {
        "logon_required": True
    },
    "frequencystop": {
        "logon_required": True
    },
    "groupquota": {
        "logon_required": False
    },
    "healthchipget": {
        "logon_required": False
    },
    "healthchipset": {
        "logon_required": True
    },
    "healthctrl": {
        "logon_required": False
    },
    "healthctrlset": {
        "logon_required": True
    },
    "immersionswitch": {
        "logon_required": True
    },
    "kill": {
        "logon_required": False
    },
    "lcd": {
        "logon_required": False
    },
    "limits": {
        "logon_required": False
    },
    "logoff": {
        "logon_required": True
    },
    "logon": {
        "logon_required": False
    },
    "netset": {
        "logon_required": True
    },
    "pools": {
        "logon_required": False
    },
    "power": {
        "logon_required": False
    },
    "profilenew": {
        "logon_required": True
    },
    "profilerem": {
        "logon_required": True
    },
    "profiles": {
        "logon_required": False
    },
    "profileset": {
        "logon_required": True
    },
    "reboot": {
        "logon_required": True
    },
    "rebootdevice": {
        "logon_required": True
    },
    "removegroup": {
        "logon_required": False
    },
    "removepool": {
        "logon_required": True
    },
    "resetminer": {
        "logon_required": True
    },
    "session": {
        "logon_required": False
    },
    "stats": {
        "logon_required": False
    },
    "summary": {
        "logon_required": False
    },
    "switchpool": {
        "logon_required": False
    },
    "tempctrl": {
        "logon_required": False
    },
    "tempctrlset": {
        "logon_required": True
    },
    "temps": {
        "logon_required": False
    },
    "updaterun": {
        "logon_required": True
    },
    "updateset": {
        "logon_required": True
    },
    "version": {
        "logon_required": False
    },
    "voltageget": {
        "logon_required": False
    },
    "voltageset": {
        "logon_required": True
    }
}

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler("LuxOS-CLI.log")],
)


# internal_send_cgminer_command sends a command to the cgminer API server and returns the response.
def internal_send_cgminer_command(host: str, port: int, command: str,
                                  timeout_sec: int, verbose: bool) -> str:

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
                null_index = data.find(b'\x00')
                if null_index >= 0:
                    response += data[:null_index]
                    break
                response += data

            # Parse the response JSON
            r = json.loads(response.decode())
            if verbose:
                logging.info(r)
            return r

        except socket.error as e:
            raise e


# send_cgminer_command sends a command to the cgminer API server and returns the response.
def send_cgminer_command(host: str, port: int, cmd: str, param: str,
                         timeout: int, verbose: bool) -> str:
    req = str(f"{{\"command\": \"{cmd}\", \"parameter\": \"{param}\"}}\n")
    if verbose:
        logging.info(
            f"Executing command: {cmd} with params: {param} to host: {host}")

    return internal_send_cgminer_command(host, port, req, timeout, verbose)


# send_cgminer_simple_command sends a command with no params to the miner and returns the response.
def send_cgminer_simple_command(host: str, port: int, cmd: str, timeout: int,
                                verbose: bool) -> str:
    req = str(f"{{\"command\": \"{cmd}\"}}\n")
    if verbose:
        logging.info(f"Executing command: {cmd} to host: {host}")
    return internal_send_cgminer_command(host, port, req, timeout, verbose)


# check_res_structure checks that the response has the expected structure.
def check_res_structure(res: str, structure: str, min: int, max: int) -> str:
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
def get_str_field(struct: str, name: str) -> str:
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


def logon_required(cmd: str, commands_list=COMMANDS) -> bool:
    # Check if the command requires logon to LuxOS API
    user_cmd = None

    keys = commands_list.keys()
    for key in keys:
        if key == cmd:
            user_cmd = cmd
            break

    if user_cmd == None:
        logging.info(
            f"{cmd} command is not supported. Try again with a different command."
        )
        return
    return commands_list[cmd]['logon_required']


def add_session_id_parameter(session_id, parameters):
    # Add the session id to the parameters
    return [session_id, *parameters]


def parameters_to_string(parameters):
    # Convert the parameters to a string that LuxOS API accepts
    return ",".join(parameters)


def generate_ip_range(start_ip, end_ip):
    # Generate a list of IP addresses from the start and end IP
    start = ipaddress.IPv4Address(start_ip)
    end = ipaddress.IPv4Address(end_ip)

    ip_list = []

    while start <= end:
        ip_list.append(str(start))
        start += 1

    return ip_list


def load_ip_list_from_csv(csv_file):
    # Check if file exists
    if not os.path.exists(csv_file):
        logging.info(f"Error: {csv_file} file not found.")
        exit(1)

    # Load the IP addresses from the CSV file
    ip_list = []
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0 and row and row[0] == "hostname":
                continue
            if row:  # Ignore empty rows
                ip_list.extend(row)
    return ip_list


def execute_command(host: str, port: int, timeout_sec: int, cmd: str,
                    parameters: list, verbose: bool):

    # Check if logon is required for the command
    logon_req = logon_required(cmd)

    try:
        if logon_req:
            # Get a SessionID
            sid = logon(host, port, timeout_sec, verbose)
            # Add the SessionID to the parameters list at the left.
            parameters = add_session_id_parameter(sid, parameters)

            if verbose:
                logging.info(
                    f'Command requires a SessionID, logging in for host: {host}'
                )
                logging.info(f'SessionID obtained for {host}: {sid}')

        elif not logon_required and verbose:
            logging.info(f"Logon not required for executing {cmd}")

        # convert the params to a string that LuxOS API accepts
        param_string = parameters_to_string(parameters)

        if verbose:
            logging.info(f"{cmd} on {host} with parameters: {param_string}")

        # Execute the API command
        res = send_cgminer_command(host, port, cmd, param_string, timeout_sec,
                                   verbose)

        if verbose:
            logging.info(res)

        # Log off to terminate the session
        if logon_req:
            send_cgminer_command(host, port, "logoff", sid, timeout_sec,
                                 verbose)

        return res

    except Exception as e:
        logging.info(f"Error executing {cmd} on {host}: {e}")


if __name__ == "__main__":

    # define arguments
    parser = argparse.ArgumentParser(description="LuxOS CLI Tool")
    parser.add_argument('--range_start', required=False, help="IP start range")
    parser.add_argument('--range_end', required=False, help="IP end range")
    parser.add_argument('--ipfile',
                        required=False,
                        default='ips.csv',
                        help="File name to store IP addresses")
    parser.add_argument('--cmd',
                        required=True,
                        help="Command to execute on LuxOS API")
    parser.add_argument('--params',
                        required=False,
                        default=[],
                        nargs='+',
                        help="Parameters for LuxOS API")
    parser.add_argument(
        '--max_threads',
        required=False,
        default=10,
        type=int,
        help="Maximum number of threads to use. Default is 10.")
    parser.add_argument('--timeout',
                        required=False,
                        default=3,
                        type=int,
                        help="Timeout for network scan in seconds")
    parser.add_argument('--port',
                        required=False,
                        default=4028,
                        type=int,
                        help="Port for LuxOS API")
    parser.add_argument('--verbose',
                        required=False,
                        default=False,
                        type=bool,
                        help="Verbose output")

    # parse arguments
    args = parser.parse_args()

    # set timeout to milliseconds
    timeout_sec = args.timeout

    # check if IP address range or CSV with list of IP is provided
    if args.range_start and args.range_end:
        ip_list = generate_ip_range(args.range_start, args.range_end)
    elif args.ipfile:
        ip_list = load_ip_list_from_csv(args.ipfile)
    else:
        logging.info("No IP address or IP list found.")
        exit(1)

    # Set max threads to use, minimum of max threads and number of IP addresses
    max_threads = min(args.max_threads, len(ip_list))

    # Create a list of threads
    threads = []

    # Set start time
    start_time = time.time()

    # Iterate over the IP addresses
    for ip in ip_list:
        # create new thread for each IP address
        thread = threading.Thread(target=execute_command,
                                  args=(ip, args.port, timeout_sec, args.cmd,
                                        args.params, args.verbose))

        # start the thread
        threads.append(thread)
        thread.start()

        # Limit the number of concurrent threads
        if len(threads) >= max_threads:
            # Wait for the threads to finish
            for thread in threads:
                thread.join()

    # Wait for the remaining threads to finish
    for thread in threads:
        thread.join()

    # Execution completed
    end_time = time.time()
    execution_time = end_time - start_time
    logging.info(f"Execution completed in {execution_time:.2f} seconds.")
