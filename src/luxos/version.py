from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Literal, overload

__version__ = ""
__hash__ = ""


@overload
def get_version(
    modules: list[types.ModuleType] | None, as_string: Literal[True]
) -> str: ...


@overload
def get_version(
    modules: list[types.ModuleType] | None, as_string: Literal[False]
) -> dict[str, str]: ...


@overload
def get_version(
    modules: list[types.ModuleType] | None, as_string: bool
) -> str | dict[str, str]: ...


def get_version(
    modules: list[types.ModuleType] | None = None, as_string: bool = False
) -> str | dict[str, str]:
    from luxos.version import __hash__, __version__

    result = {
        "py": sys.version.partition(" ")[0],
        "luxos": ", ".join(
            str(c) if str(c) else "N/A" for c in [__version__, __hash__]
        ),
    }

    module = modules[-1] if modules else None
    if module:
        if path := getattr(module, "__file__", None):
            name = Path(path).name
        else:
            name = getattr(module, "__name__", str(module))
        if name not in {
            "luxos.py",
            "luxos_run.py",
        }:
            result[name] = getattr(module, "__version__", "N/A")

    return ", ".join(f"{k}[{v}]" for k, v in result.items()) if as_string else result
