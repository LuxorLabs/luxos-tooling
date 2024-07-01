#!/usr/bin/env python
"""build and publish doc pages to git hub pages"""

import logging
import shutil
import subprocess
from pathlib import Path

import sphinx.cmd.build

from luxos.cli import v1 as cli

LOGGING_CONFIG = {
    "level": logging.WARNING,
}

log = logging.getLogger(__name__)


def add_arguments(parser):
    parser.add_argument("--build", action="store_true", help="no clone, just build")
    parser.add_argument("--commit", action="store_true", help="commit changes")
    parser.add_argument("builddir", type=Path)


def process_args(args):
    if (not args.build) and args.builddir.exists():
        args.error(f"build dir path present, {args.builddir}")
    if args.build and not args.builddir.exists():
        args.error(f"missing build dir, {args.builddir}")

    if not (path := Path("docs/conf.py")).exists():
        args.error(f"sphinx conf doc not found, {path}")


def run(cmd, **kwargs):
    subprocess.check_call([str(c) for c in cmd], **kwargs)


def runo(cmd):
    return subprocess.check_output([str(c) for c in cmd], encoding="utf-8")


def clone(builddir):
    remote = runo(["git", "config", "remote.origin.url"]).strip()

    run(["git", "clone", "-b", "gh-pages", remote, builddir])


# cleanup
def cleanup(builddir):
    exclude = {".git", ".nojekyll", ".gitignore"}
    for path in builddir.glob("*"):
        if path.name in exclude:
            continue
        log.info("removing %s", path)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


@cli.cli(add_arguments, process_args)
def main(args):
    if not args.build:
        clone(args.builddir)
    cleanup(args.builddir)
    sphinx.cmd.build.main(["docs", str(args.builddir)])
    if args.commit:
        run(
            [
                "git",
                "commit",
                "-a",
                "-m",
                "update",
            ],
            cwd=args.builddir,
        )
        run(["git", "push"], cwd=args.builddir)


if __name__ == "__main__":
    main()
