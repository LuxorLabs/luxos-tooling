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
