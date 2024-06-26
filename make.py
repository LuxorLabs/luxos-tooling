#!/usr/bin/env python
# Usage:
#   curl -LO https://github.com/LuxorLabs/luxos-tooling/raw/main/make.pyz
#   python make.pyz
"""A make-like script"""

import contextlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

try:
    from make import fileos, misc, task  # type: ignore
except ImportError:
    print("""Please run:
  python make.pyz <command>
""")
    sys.exit()

log = logging.getLogger(__name__)

BUILDDIR = Path.cwd() / "build"
DOCDIR = Path.cwd() / "build" / "docs"  # output doc dir


def getdocdir():
    if not DOCDIR.exists():
        subprocess.check_call(
            [
                "git",
                "clone",
                "-b",
                "gh-pages",
                "git@github.com:LuxorLabs/luxos-tooling.git",
                str(DOCDIR),
            ]
        )
        for path in DOCDIR.glob("*"):
            if path.name == ".git":
                continue
            if path.is_file():
                path.unlink()
            else:
                fileos.rmtree(path)
    return str(DOCDIR)


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

    changed = False
    for target, entrypoint in targets:
        dst = o.output_dir / target
        out = misc.makezapp(dst, workdir / "src", main=entrypoint, compressed=True)

        relpath = dst.relative_to(Path.cwd()) if dst.is_relative_to(Path.cwd()) else dst
        if out:
            print(f"Written: {relpath}", file=sys.stderr)
            changed = True
        else:
            print(f"Skipping generation: {relpath}", file=sys.stderr)
    sys.exit(int(changed))


@task()
def check():
    """runs all checks on code base"""
    subprocess.check_call(["ruff", "check", "src", "tests"])


@task()
def fmt():
    """format and fix the code"""
    subprocess.check_call(["ruff", "check", "--fix", "src", "tests"])
    subprocess.check_call(["ruff", "format", "src", "tests"])


@task()
def tests():
    """runs all tests (excluding the manual ones)"""
    workdir = Path.cwd()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd() / "src")
    subprocess.check_call(
        [
            "pytest",
            "-vvs",
            "--manual",
            "--cov",
            "luxos",
            "--cov-report",
            f"html:{BUILDDIR / 'coverage'}",
            str(workdir / "tests"),
        ],
        env=env,
    )
    print(f"Coverage report under {BUILDDIR / 'coverage'}")


@task(name="beta-build")
def beta_build(parser, argv):
    """create beta packages for luxos (only works in github)"""

    parser.add_argument(
        "-n", "--dry-run", dest="dryrun", action="store_true", help="dry run"
    )
    parser.add_argument(
        "--release", action="store_true", help="generate release packages"
    )
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
        version = current if options.release else f"{current}b{gdata['run_number']}"

        log.info("creating for version %s [%s]", version, gdata["sha"])
        misc.set_variable_def(pyproject, "version", lineno, version, quote)

        # __init__.py
        initfile = save("src/luxos/__init__.py")
        lineno, old, quote = misc.get_variable_def(initfile, "__version__")
        log.debug("found at LN:%i: __version__ = '%s'", lineno, old)
        if old != "" and old != current:
            raise RuntimeError(f"found in {initfile} __version__ {old} != {current}")
        misc.set_variable_def(initfile, "__version__", lineno, version, quote)

        lineno, old, quote = misc.get_variable_def(initfile, "__hash__")
        log.debug("found at LN:%i: __hash__ = '%s'", lineno, old)
        if old != "" and old != gdata["sha"]:
            raise RuntimeError(f"found in {initfile} __hash__ {old} != {gdata['sha']}")
        misc.set_variable_def(initfile, "__hash__", lineno, gdata["sha"], quote)

        if not options.dryrun:
            subprocess.check_call([sys.executable, "-m", "build"])  # noqa: S603


@task()
def docs():
    """build the documentation"""
    from sphinx.cmd.build import main

    argv = [
        Path.cwd() / "docs",
        getdocdir(),
    ]
    main([str(c) for c in argv])
    # PYTHONPATH=src sphinx-apidoc -o docs/api  src/luxos


@task(name="serve-docs")
def serve_docs():
    from sphinx_autobuild.__main__ import main

    argv = [
        "--port",
        "8000",
        Path.cwd() / "docs",
        getdocdir(),
    ]
    sys.argv = ["", *[str(c) for c in argv]]
    main()
