from __future__ import annotations
import ipaddress
import json
import logging
from typing import Any
import importlib.resources

import luxos

log = logging.getLogger(__name__)

COMMANDS = json.loads(
    (importlib.resources.files(luxos) / "api.json")
    .read_text()
)


def generate_ip_range(start_ip: str, end_ip: str) -> list[str]:
    # Generate a list of IP addresses from the start and end IP
    start = ipaddress.IPv4Address(start_ip)
    end = ipaddress.IPv4Address(end_ip)

    ip_list = []

    while start <= end:
        ip_list.append(str(start))
        start += 1

    return ip_list


def logon_required(
        cmd: str,
        commands_list: dict[str, dict[str, Any]] | None = None
) -> None | bool:
    # Check if the command requires logon to LuxOS API
    user_cmd = None
    commands_list = commands_list or COMMANDS

    keys = commands_list.keys()
    for key in keys:
        if key == cmd:
            user_cmd = cmd
            break

    if user_cmd is None:
        logging.info(
            f"{cmd} command is not supported. Try again with a different command."
        )
        return None
    return commands_list[cmd]['logon_required']


def main():
    print("CALLED!")
