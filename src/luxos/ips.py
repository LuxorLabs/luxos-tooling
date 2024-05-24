"""ipaddress manipulation"""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from typing import Generator


def splitip(txt: str) -> tuple[str, int | None]:
    expr = re.compile(r"(?P<ip>\d{1,3}([.]\d{1,3}){3})(:(?P<port>\d+))?")
    if not (match := expr.search(txt)):
        raise RuntimeError(f"invalid ip:port address {txt}")
    return match["ip"], int(match["port"]) if match["port"] is not None else None


def iter_ip_ranges(
    txt: str, port: int | None = None, rsep: str = "-", gsep: str = ","
) -> Generator[tuple[str, int | None], None, None]:
    """iterate over ip ranges.

    The txt string cav have one of these formats:

    1. a single ip such as '127.0.0.1' or '127.0.0.1:8080'
    2. an (inclusive) range using two ips separated by `-`
         as '127.0.0.1 - 127.0.0.3'
    3. a combination of the above `,` separated as
         '127.0.0.1 , 192.168.0.1-192.168.0.10'

    Example:
    ```python
    for ip in iter_ip_ranges("127.0.0.1 , 127.0.0.3-127.0.0.15"):
        print(ip)

    127.0.0.1
    127.0.0.2
    127.0.0.3
    ...
    127.0.0.15
    ```
    """
    for segment in txt.replace(" ", "").split(gsep):
        start, _, end = segment.partition(rsep)
        if not end:
            start, sport = splitip(start)
            yield (start, sport or port)
        else:
            start, sport = splitip(start)
            end, eport = splitip(end)
            if (sport and eport) and (sport != eport):
                raise RuntimeError(f"invalid range ports in {segment}")
            cur = ipaddress.IPv4Address(start)
            last = ipaddress.IPv4Address(end)
            theport = sport or eport or port
            while cur <= last:
                yield (str(cur), theport)
                cur += 1


def load_ips_from_csv(path: Path | str, port: int = 4028) -> list[tuple[str, int]]:
    """loads ip addresses from a csv file

    Example:
    ```python

    foobar.csv contains ranges as parsed by iter_ip_ranges
    127.0.0.1 # a single address
    127.0.0.2-127.0.0.10


    for ip in load_ips_from_csv("foobar.csv"):
        print(ip)

    (127.0.0.1, 4028)
    (127.0.0.2, 4028)
    (127.0.0.3, 4028)
    ...
    (127.0.0.10, 4028)
    ```

    """
    result = []
    for line in Path(path).read_text().split("\n"):
        line = line.partition("#")[0]
        if not line.strip():
            continue
        for host, port2 in iter_ip_ranges(line):
            result.append((host, port2 or port))
    return result
