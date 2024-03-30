import logging
import json
import importlib

log = logging.getLogger(__name__)


COMMANDS = json.loads(
    (importlib.resources.files("luxos") / "api.json")
    .read_text()
)

