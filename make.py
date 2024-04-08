#!/usr/bin/env python
"""A make-like script"""

import contextlib
import json
import os
import sys
import logging
import subprocess
from pathlib import Path

# curl -LO https://github.com/cav71/hatch-ci/raw/beta/0.1.4/make.pyz
from make import fileos, misc, task  # type: ignore

log = logging.getLogger(__name__)


@task()
def hello(argv):
    """this is the hello world"""
    print(  # noqa: T201
        f"""
Hi!
python: {sys.executable}
version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}
cwd: {Path.cwd()}
argv: {argv}
"""
    )


@task(name=None)
def onepack(parser, argv):
    """create a one .pyz single file package"""
    from configparser import ConfigParser, ParsingError

    workdir = Path.cwd()

    config = ConfigParser(strict=False)
    with contextlib.suppress(ParsingError):
        config.read(workdir / "pyproject.toml")

    targets = []
    section = "project.scripts"
    for target in config.options(section):
        entrypoint = config.get(section, target).strip("'").strip('"')
        targets.append((f"{target}.pyz", entrypoint))

    parser.add_argument("-o", "--output-dir", default=workdir, type=Path)
    o = parser.parse_args(argv)

    for target, entrypoint in targets:
        dst = o.output_dir / target
        out = misc.makezapp(dst, workdir / "src", main=entrypoint, compressed=True)

        relpath = dst.relative_to(Path.cwd()) if dst.is_relative_to(Path.cwd()) else dst
        if out:
            print(f"Written: {relpath}", file=sys.stderr)
        else:
            print(f"Skipping generation: {relpath}", file=sys.stderr)


@task()
def checks():
    """runs all checks on code base"""
    subprocess.check_call(["ruff", "check", "src", "tests"])


@task()
def tests():
    """runs all tests (excluding the manual ones)"""
    workdir = Path.cwd()
    subprocess.check_call(["pytest", "-vvs", str(workdir / "tests")])


@task(name="beta-build")
def beta_build(parser, argv):
    """create beta packages for luxos (only works in github)"""

    parser.add_argument("-n", "--dry-run", dest="dryrun", action="store_true", help="dry run")
    parser.add_argument("--release", action="store_true", help="generate release packages")
    options = parser.parse_args(argv)

    github_dump = os.getenv("GITHUB_DUMP")
    if not github_dump:
        raise RuntimeError("missing GITHUB_DUMP variable")
    gdata = (
        json.loads(Path(github_dump[1:]).read_text())
        if github_dump.startswith("@")
        else json.loads(github_dump)
    )
    misc.validate_gdata(
        gdata, ["run_number", "sha", "ref_name", "ref_type", "workflow_ref"]
    )

    with contextlib.ExitStack() as stack:
        save = stack.enter_context(fileos.backups())

        # pyproject.toml
        pyproject = save("pyproject.toml")
        lineno, current, quote = misc.get_variable_def(pyproject, "version")
        log.debug("found at LN:%i: version = '%s'", lineno, current)
        version = current if options.release else "{current}b{gdata['run_number']}"

        log.info("creating for version %s [%s]", version, gdata["sha"])
        misc.set_variable_def(pyproject, "version", lineno, version, quote)

        # __init__.py
        initfile = save("src/luxos/__init__.py")
        lineno, old, quote = misc.get_variable_def(initfile, "__version__")
        log.debug("found at LN:%i: __version__ = '%s'", lineno, old)
        if old != "" and old != current:
            raise RuntimeError(f"found in {initfile} __version__ {old} != {current}")
        misc.set_variable_def(pyproject, "__version__", lineno, version, quote)

        lineno, old, quote = misc.get_variable_def(initfile, "__hash__")
        log.debug("found at LN:%i: __hash__ = '%s'", lineno, old)
        if old != "" and old != gdata["sha"]:
            raise RuntimeError(f"found in {initfile} __hash__ {old} != {gdata['sha']}")
        misc.set_variable_def(pyproject, "__hash__", lineno, gdata["sha"], quote)

        if not options.dryrun:
            subprocess.check_call([sys.executable, "-m", "build"])  # noqa: S603
