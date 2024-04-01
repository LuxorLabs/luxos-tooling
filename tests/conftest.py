# nothing to see here, yet
import contextlib
import subprocess
import sys
import dataclasses as dc
import time
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
    module = util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore
    return module


@pytest.fixture(scope="function")
def echopool(resolver, tmp_path, request):
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

    @dc.dataclass
    class Pool:
        def __init__(self):
            self.process: subprocess.Popen | None = None
            self.addresses: list[tuple[str, int]] | None = None

        def start(
            self,
            number: int,
            mode: str = "echo+",
            verbose: bool = False,
            timeout: float | None = None,
        ):
            cmd = [sys.executable, script, "--mode", mode]

            if verbose:
                cmd.append("-v")
            cmd.append("-v")

            path = tmp_path / f"{request.function.__name__}.txt"
            cmd.extend(["--server-file", path])

            cmd.append(number)

            self.process = subprocess.Popen([str(c) for c in cmd])

            # wait at most 5 seconds for the underlying server to start up
            timeout = 5.0 if timeout is None else timeout
            ttl = (time.monotonic() + timeout) if timeout else None

            while self.addresses is None:
                if ttl and (time.monotonic() > ttl):
                    raise RuntimeError("failed to start underlying server", cmd)
                addresses = []
                with contextlib.suppress(FileNotFoundError):
                    for line in path.read_text().split("\n"):
                        if found := mod.is_server_line(line):
                            addresses.append(found)
                        if mod.is_end_server_lines(line):
                            self.addresses = addresses
                            break
                time.sleep(0.01)

        def shutdown(self):
            if self.process:
                self.process.kill()

    pool = Pool()
    try:
        yield pool
    finally:
        pool.shutdown()


def pytest_addoption(parser):
    parser.addoption(
        "--manual",
        action="store_true",
        dest="manual",
        default=False,
        help="run manual tests",
    )


def pytest_configure(config):
    if not config.option.manual:
        setattr(config.option, "markexpr", "not manual")
