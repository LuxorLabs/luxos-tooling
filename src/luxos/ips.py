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


def _parse_expr(txt: str) -> None | tuple[str, str, int | None]:
    tokens = {
        "ip": re.compile(r"(?P<ip>\d{1,3}([.]\d{1,3}){3})"),
        "sep": re.compile(":"),
        "div": re.compile("-"),
        "port": re.compile(r"(?P<port>\d+)"),
    }

    txt2 = txt.replace(" ", "")

    items = []
    while txt2.strip():
        for k, e in tokens.items():
            if match := e.match(txt2):
                i, j = match.span()
                items.append((k, txt2[i:j]))
                txt2 = txt2[j:]
                break
        else:
            raise RuntimeError(f"cannot parse text '{txt}'")

    if len(items) == 0:
        return None

    def matcher(syntax):
        def match(left, right):
            if len(left) != len(right):
                return False
            for a, b in zip(left, right):
                if isinstance(b, str):
                    if a != b:
                        return False
                elif a not in b:
                    return False
            return True

        start = end = port = None
        if match(syntax, ["ip"]):
            start = items[0][1]
        elif match(syntax, ["ip", "sep", "port"]):
            start = items[0][1]
            port = int(items[2][1])
        elif match(syntax, ["ip", {"sep", "div"}, "ip"]):
            start = items[0][1]
            end = items[2][1]
        elif match(syntax, ["ip", "sep", "port", {"div", "sep"}, "ip"]):
            start = items[0][1]
            end = items[4][1]
            port = int(items[2][1])
        elif match(syntax, ["ip", {"div", "sep"}, "ip", "sep", "port"]):
            start = items[0][1]
            end = items[2][1]
            port = int(items[4][1])
        elif match(syntax, ["ip", "sep", "port", {"div", "sep"}, "ip", "sep", "port"]):
            start = items[0][1]
            end = items[4][1]
            port = int(items[2][1])
            port1 = int(items[6][1])
            if port != port1:
                raise RuntimeError(f"ports mismatch {port} != {port1}")
        return start, end, port

    syntax = [item[0] for item in items]
    return matcher(syntax)


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
        if not (found := _parse_expr(segment)):
            continue
        start, end, theport = found
        if start is None and end is None:
            raise RuntimeError(f"cannot parse '{segment}'")
        if end is None:
            yield (start, theport or port)
            return

        cur = ipaddress.IPv4Address(start)
        last = ipaddress.IPv4Address(end)
        while cur <= last:
            yield (str(cur), theport or port)
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
