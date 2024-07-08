#!/usr/bin/env python
from __future__ import annotations

import argparse
import contextlib
import dataclasses as dc
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def validate_gdata(gdata: dict[str, Any], keys: list[str] | None = None):
    """validate the GITHUB json dioctionary

    Eg.
        validate_gdata(json.loads(os.getenv("GITHUB_DUMP")))

        In github workflow:
        env:
            GITHUB_DUMP: ${{ toJson(github) }}
    """
    missing = []
    keys = keys or ["run_number", "sha", "ref_name", "ref_type", "workflow_ref"]
    for key in keys:
        if key not in gdata:
            missing.append(key)
    if missing:
        raise RuntimeError(f"missing keys: {', '.join(missing)}")


@contextlib.contextmanager
def backups():
    pathlist: list[Path | str] = []

    def save(path: Path | str):
        nonlocal pathlist
        original = Path(path).expanduser().absolute()
        backup = original.parent / f"{original.name}.bak"
        if backup.exists():
            raise RuntimeError("backup file present", backup)
        shutil.copy(original, backup)
        pathlist.append(backup)
        return original

    try:
        yield save
    finally:
        for backup in pathlist:
            original = backup.with_suffix("")
            original.unlink()
            shutil.move(backup, original)


@dc.dataclass
class File:
    path: Path
    lines: list[str] = dc.field(default_factory=list)

    def __post_init__(self):
        self.lines = self.path.read_text().split("\n")

    def save(self):
        self.path.write_text("\n".join(self.lines))

    def find(self, call):
        result = []
        for lineno, line in enumerate(self.lines):
            if ret := call(line):
                result.append((lineno, line, ret))
        if len(result) > 1:
            raise RuntimeError(f"too many matches: {result}")
        return result[0] if result else (None, None, None)

    def find_var(self, key):
        expr = re.compile(
            r"\s*" + key + r"\s*[=]\s*(?P<quote>['\"])(?P<value>(\d+([.]\d)*)?)\1"
        )
        return self.find(lambda line: expr.search(line))

    def replace_or_append(self, txt, lineno):
        if lineno is None:
            self.lines.append(txt)
        else:
            self.lines[lineno] = txt


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("initfile", type=Path)
    parser.add_argument("--release", action="store_true")
    parser.add_argument(
        "-n", "--dry-run", dest="dryrun", action="store_true", help="dry run"
    )
    return parser.parse_args(args)


def main(args):
    github_dump = os.getenv("GITHUB_DUMP")
    if not github_dump:
        raise RuntimeError("missing GITHUB_DUMP variable")
    gdata = (
        json.loads(Path(github_dump[1:]).read_text())
        if github_dump.startswith("@")
        else json.loads(github_dump)
    )

    validate_gdata(gdata, ["run_number", "sha", "ref_name", "ref_type", "workflow_ref"])

    with contextlib.ExitStack() as stack:
        save = stack.enter_context(backups())

        # pyproject.toml
        pyproject = File(save("pyproject.toml"))

        lineno, line, ret = pyproject.find_var("version")
        current = ret.group("value")
        version = current if args.release else f"{current}b{gdata['run_number']}"
        if current != version:
            pyproject.lines[lineno] = f'version = "{version}"'
            pyproject.save()

        # inifile
        initfile = File(save(args.initfile))

        lineno, line, ret = initfile.find_var("__version__")
        initfile.replace_or_append(f'__version__ = "{version}"', lineno)

        lineno, line, ret = initfile.find_var("__hash__")
        initfile.replace_or_append(f"__hash__ = \"{gdata['sha']}\"", lineno)

        initfile.save()

        if not args.dryrun:
            subprocess.check_call([sys.executable, "-m", "build"])  # noqa: S603


if __name__ == "__main__":
    main(parse_args())
