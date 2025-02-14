"""ipaddress manipulation"""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from typing import Generator

from .exceptions import AddressParsingError, LuxosBaseException


class DataParsingError(LuxosBaseException):
    pass


def splitip(txt: str, strict=True) -> tuple[str, int | None]:
    if txt.count(":") not in {0, 1}:
        raise ValueError("too many ':' in value")

    host, _, port_txt = txt.partition(":")
    host = host.strip()
    try:
        port = int(port_txt) if port_txt else None
    except ValueError:
        raise ValueError(f"cannot convert '{port_txt}' to an integer")
    if not host.strip():
        raise ValueError(f"cannot find host part in '{txt}'")

    if not strict:
        return host, port

    if re.search(r"(?P<ip>\d{1,3}([.]\d{1,3}){3})", host) and all(
        int(c) < 256 for c in host.split(".")
    ):
        return host, port
    raise ValueError(f"cannot convert '{host}' into an ipv4 address N.N.N.N")


def parse_expr(txt: str) -> None | tuple[str, str | None, int | None]:
    """parse text into a (start, end, port) tuple.

    Parses a text in these forms:
        <ip>
        <ip>:port
        <startip>:<endip>
        <startip>:<port>:<endip>
    Eg.
        >>> parse_expr("127.0.0.1")
        ("127.0.0.1", None, None)
        >>> ips.parse_expr("127.0.0.1:1234:127.0.0.3")
        ("127.0.0.1", "127.0.0.3", 1234)
    """
    tokens = {
        "ip": re.compile(r"(?P<ip>\d{1,3}([.]\d{1,3}){3})"),
        "sep": re.compile(":"),
        "div": re.compile("-"),
        "port": re.compile(r"(?P<port>\d+)"),
        "address": re.compile(r"(?P<address>[^:]+)"),
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
            raise AddressParsingError(f"cannot parse text '{txt}'")

    if len(items) == 0:
        raise AddressParsingError(f"cannot parse '{txt}'")

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
        if match(syntax, [{"ip", "address"}]):
            start = items[0][1]
        elif match(syntax, [{"ip", "address"}, "sep", "port"]):
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
                raise AddressParsingError(f"ports mismatch {port} != {port1}")
        else:
            raise AddressParsingError(f"cannot parse '{txt}': {syntax=}")
        return start, end, port

    syntax = [item[0] for item in items]
    return matcher(syntax)


def iter_ip_ranges(
    txt: str, port: int | None = None, gsep: str = ",", strict: bool = True
) -> Generator[tuple[str, int | None], None, None]:
    """iterate over ip ranges.

    The txt string cav have one of these formats:

    1. a single ip and (optional) port: ``127.0.0.1`` or ``127.0.0.1:8080``
    2. an (inclusive) range using two ips separated by a
       ``-`` (minus) sign: ``127.0.0.1-127.0.0.3``
    3. a combination of the above separated by a ``,`` (comma) sign:
       ``127.0.0.1,192.168.0.1-192.168.0.10``

    Example::

        for ip in iter_ip_ranges("127.0.0.1,127.0.0.3-127.0.0.15:9999"):
            print(ip)

        (127.0.0.1, None),
        (127.0.0.3, 9999),
        ...
        (127.0.0.15, 9999),
    """
    for segment in txt.replace(" ", "").split(gsep):
        try:
            if not (found := parse_expr(segment)):
                continue
        except AddressParsingError:
            if strict:
                raise
            continue
        start, end, theport = found
        if start is None and end is None:
            raise RuntimeError(f"cannot parse '{segment}'")
        if end is None:
            yield (start, theport or port)
            continue

        cur = ipaddress.IPv4Address(start)
        last = ipaddress.IPv4Address(end)
        while cur <= last:
            yield (str(cur), theport or port)
            cur += 1


def ip_ranges(
    txt: str, gsep: str = ":", strict: bool = True
) -> list[tuple[str, int | None]]:
    """return a list of ips given a text expression.

    Eg.
        >>> for ip in ip_ranges("127.0.0.1"):
        ...     print(ip)
        127.0.0.1

        >>> for ip in ip_ranges("127.0.0.1-127.0.0.3"):
        ...     print(ip)
        127.0.0.1
        127.0.0.2
        127.0.0.3

    NOTE: use the `:` (gsep) to separate ips groups, and `-` (rsep) to define a range.
    """
    return list(iter_ip_ranges(txt, gsep=gsep, strict=strict))


def load_ips_from_csv(
    path: Path | str, port: int | None = 4028, strict: bool = False
) -> list[tuple[str, int | None]]:
    """
    Load ip addresses from a csv file.

    Arguments:
        path: a Path object to load data from (csv-like)
        port: a fallback port if not defined
        strict: abort with AddressParsingError if there's a malformed entry

    Raises:
        AddressParsingError: if strict is set to True and there's a
            malformed entry in path.

    Notes:
        The **strict** argument if set to False will ignore malformed
        lines in csv. If set to True it will raise AddressParsingError on
        invalid entries.

    Example:
        **foobar.csv** file::

            # comment (or empty lines) will be ignored
            127.0.0.1 # a single address
            127.0.0.2-127.0.0.10 # a range of addresses

            # you can specify a port
            127.0.0.11:9999
            127.0.0.12-127.0.0.20:8888

        You can read into a list of (host, port) tuples as::

           for ip in load_ips_from_csv("foobar.csv"):
               print(ip)

           (127.0.0.1, 4028)
           (127.0.0.2, 4028)
           (127.0.0.3, 4028)
           ...
           (127.0.0.10, 4028)

    """
    result = []
    for line in Path(path).read_text().split("\n"):
        line = line.partition("#")[0]
        if not line.strip():
            continue
        # for excel, an exception
        if line.strip().lower() == "hostname":
            continue
        for host, port2 in iter_ip_ranges(line, strict=strict):
            result.append((host, port2 or port))
    return result


def load_ips_from_yaml(
    path: Path | str, port: int | None = 4028, strict: bool = False
) -> list[tuple[str, int | None]]:
    """
    Load ip addresses from a yaml file.

    Arguments:
        path: a Path object to load data from (csv-like)
        port: a fallback port if not defined
        strict: abort with AddressParsingError if there's a malformed entry

    Raises:
        AddressParsingError: if strict is set to True and
            there's a malformed entry in path.

    Notes:
        The **strict** argument if set to False will ignore malformed
        lines in csv. If set to True it will raise AddressParsingError on
        invalid entries.

    Example:
        **foobar.yaml** file::

            miners:
                luxos_port: 9999  # default fallback port
                addresses:
                    - 127.0.0.1 # a single address
                    - 127.0.0.2-127.0.0.10 # a range of addresses

                    # you can specify a port
                    - 127.0.0.11:9999
                    - 127.0.0.12-127.0.0.20:8888
    """
    from yaml import safe_load

    txt = Path(path).read_text()
    try:
        data = safe_load(txt)
    except Exception as exc:
        raise DataParsingError(f"cannot parse yaml file {path}") from exc

    if "miners" in data and "addresses" in data["miners"]:
        miners = data["miners"]
        default_port = miners.get("luxos_port", None)
        result = []
        for address in data["miners"]["addresses"]:
            for host, thisport in iter_ip_ranges(address, strict=strict):
                result.append((host, thisport or default_port or port))
        return result

    raise DataParsingError(f"cannot find miners definitions in {path}")
