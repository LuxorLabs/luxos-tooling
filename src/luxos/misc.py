# catch-all module (find later a better place)
from __future__ import annotations

import ipaddress
import itertools
import sys
import types
from pathlib import Path
from typing import Generator

if sys.version_info >= (3, 12):
    batched = itertools.batched
else:

    def batched(iterable, n):
        if n < 1:
            raise ValueError("n must be at least one")
        it = iter(iterable)
        while batch := tuple(itertools.islice(it, n)):
            yield batch


def iter_ip_ranges(
    txt: str, gsep: str = ":", rsep: str = "-"
) -> Generator[str, None, None]:
    """iterate over ip ranges

    for ip in iter_ip_ranges("127.0.0.1-127.0.0.3:127.0.0.15"):
        print(ip)

    127.0.0.1
    127.0.0.2
    127.0.0.3
    127.0.0.15

    NOTE: use the `:` (gsep) to separate ips groups, and `-` (rsep) to define a range.
    """

    for segment in txt.split(gsep):
        start, _, end = segment.partition(rsep)
        if not end:
            yield start
        else:
            cur = ipaddress.IPv4Address(start)
            last = ipaddress.IPv4Address(end)
            while cur <= last:
                yield str(cur)
                cur += 1


def loadmod(path: Path) -> types.ModuleType:
    from importlib import util
    from types import ModuleType
    from urllib.parse import urlparse
    from urllib.request import urlopen

    if urlparse(str(path)).scheme in {"http", "https"}:
        urltxt = str(urlopen(str(path)).read(), encoding="utf-8")
        mod = ModuleType(str(path).rpartition("/")[2])
        exec(urltxt, mod.__dict__)
        return mod

    spec = util.spec_from_file_location(Path(path).name, Path(path))
    module = util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore
    return module
