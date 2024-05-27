from __future__ import annotations

import importlib.resources
import json
import logging

log = logging.getLogger(__name__)


COMMANDS = json.loads((importlib.resources.files("luxos") / "api.json").read_text())


def logon_required(cmd: str, commands_list=COMMANDS) -> bool | None:
    # Check if the command requires logon to LuxOS API

    if cmd not in COMMANDS:
        log.info(
            "%s command is not supported. Try again with a different command.", cmd
        )
        return None

    return COMMANDS[cmd]["logon_required"]


# TODO timeouts should be float | None
# TODO prepare for refactoring using example in
#      tests.test_asyncops.test_bridge_execute_command
def execute_command(
    host: str, port: int, timeout: int, cmd: str, params: list[str], verbose: bool
):
    from .scripts import luxos

    return luxos.execute_command(host, port, timeout, cmd, params, verbose)
