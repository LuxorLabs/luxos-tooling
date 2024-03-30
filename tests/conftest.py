# nothing to see here, yet
import subprocess
import sys
import dataclasses as dc
import types
from pathlib import Path

import pytest


DATADIR = Path(__file__).parent / "data"


@pytest.fixture(scope="function")
def resolver(request):
    """return a resolver object to lookup for test data

    Example:
        def test_me(resolver):
            print(resolver.lookup("a/b/c")) -> tests/data/a/b/c
    """

    @dc.dataclass
    class Resolver:
        root: Path
        name: str

        def lookup(self, path: Path | str) -> Path:
            candidates = [
                self.root / self.name / path,
                self.root / path,
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate
            raise FileNotFoundError(f"cannot find {path}", candidates)

    yield Resolver(DATADIR, request.module.__name__)


def loadmod(path: Path) -> types.ModuleType:
    from importlib import util

    spec = util.spec_from_file_location(Path(path).name, Path(path))
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="function")
def echopool(resolver):
    """yield a pool of echo servers

    Example:
        def test_me(echopool):
            echopool.start(30)
            host, port = echopool.addresses[0]
            ret = luxos.api.send_cgminer_command(host, port, "helo", "world")

    Note:
        set the environemnt variable to a miner to test against it,
        eg. export LUXOS_TEST_MINER=1.2.3.4:99999

        minerd has only two methods, .server_address and .load!
    """
    script = resolver.lookup("echopool.py")
    mod = loadmod(script)

    class Pool:
        def __init__(self):
            self.process = None

        def start(
            self,
            number: int,
            mode: str = "echo+",
            verbose: bool = False,
            delay_s: float | None = None,
            async_delay_s: float | None = None,
        ):
            cmd = [sys.executable, script, "--mode", mode]
            if verbose:
                cmd.append("-v")
            if delay_s:
                cmd.extend(["--delay", delay_s])
            if async_delay_s:
                cmd.extend(["--async-delay", async_delay_s])
            cmd.append(number)

            self.process = subprocess.Popen(
                [str(c) for c in cmd], stdout=subprocess.PIPE
            )

            self.addresses = []
            while True:
                line = str(self.process.stdout.readline(), "utf-8")
                if found := mod.is_server_line(line):
                    self.addresses.append(found)
                if mod.is_end_server_lines(line):
                    break

        def shutdown(self):
            if self.process:
                self.process.kill()

    pool = Pool()
    try:
        yield pool
    finally:
        pool.shutdown()
