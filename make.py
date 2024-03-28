#!/usr/bin/env python
"""A make-like script"""
import argparse
import os
import sys
import logging
import functools
import subprocess
from pathlib import Path


def task(name=None):
    """task decorator

    This decorator will run the decorated function so:
        1. change the current directory to this script
           directory
        2. call the decorated task
        3. return to the (eventual) starting dir

    The wrapped function can have few `magic` arguments:
        - args : this is the sys.argv[2:] list
        - parser : this will be a argparse.ArgumentParser ready
        - workdir : in case you dont want to auto cd into workdir
    """
    def _task1(fn):
        @functools.wraps(fn)
        def _task(workdir, args):
            from inspect import signature
            cwd = Path.cwd()
            try:
                kwargs = {}
                if "args" in signature(fn).parameters:
                    kwargs["args"] = args
                if "parser" in signature(fn).parameters:
                    class F(argparse.ArgumentDefaultsHelpFormatter):
                        pass
                    kwargs["parser"] = argparse.ArgumentParser(
                        formatter_class=F, description=_task.description)
                if "workdir" in signature(fn).parameters:
                    kwargs["workdir"] = workdir
                else:
                    os.chdir(workdir)
                return fn(**kwargs)
            finally:
                os.chdir(cwd)

        _task.task = name or fn.__name__
        _task.description = (
            fn.__doc__.strip().partition("\n")[0] if fn.__doc__ else "no help available"
        )
        return _task

    return _task1


@task(name=None)
def onepack(parser, args, workdir):
    """create a one .pyz single file package"""
    from zipapp import create_archive

    parser.add_argument("-o", "--output",
                   default=workdir / "luxos.pyz", type=Path)
    o = parser.parse_args(args)

    create_archive(
        workdir / "src",
        o.output,
        main="luxos.api:main",
        compressed=True
    )
    relpath = (
        o.output.relative_to(Path.cwd())
        if o.output.is_relative_to(Path.cwd())
        else o.output
    )
    print(f"Written: {relpath}", file=sys.stderr)


@task()
def checks():
    """runs all checks on code base"""
    subprocess.check_call(["ruff", "check", "src", "tests"], cwd=workdir)


@task()
def tests():
    workdir = Path.cwd()
    subprocess.check_call(
        ["pytest", "-vvs", str(workdir / "tests") ]
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    tasks = [ item for item in list(locals().values()) if getattr(item, "task", None)]

    if len(sys.argv) < 2 or sys.argv[1] not in [t.task for t in tasks]:
        txt = "\n".join(f"  {task.task} - {task.description}" for task in tasks)
        print(  # noqa: T201
            f"""\
make.py <command> {{arguments}}

Commands:
{txt}
""",
            file=sys.stderr,
        )
        sys.exit()

    workdir = Path(__file__).parent
    function = [t for t in tasks if sys.argv[1] == t.task][0]
    function(workdir, args=sys.argv[2:])
