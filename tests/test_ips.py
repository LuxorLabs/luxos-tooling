from __future__ import annotations

import pytest

from luxos import ips

VALUES = """
127.0.0.1                       -> 127.0.0.1, None, None
127.0.0.1:1234                  -> 127.0.0.1, None, 1234
127.0.0.1:1234:127.0.0.3        -> 127.0.0.1, 127.0.0.3, 1234
127.0.0.1:1234-127.0.0.3        -> 127.0.0.1, 127.0.0.3, 1234
127.0.0.1-127.0.0.3:1234        -> 127.0.0.1, 127.0.0.3, 1234
127.0.0.1:127.0.0.3:1234        -> 127.0.0.1, 127.0.0.3, 1234
127.0.0.1:1234-127.0.0.3:1234   -> 127.0.0.1, 127.0.0.3, 1234

a.host                          -> a.host, None, None
a.host:1234                     -> a.host, None, 1234
"""


def _getdata():
    result = []
    for line in VALUES.split("\n"):
        if line.strip() and not line.strip().startswith("#"):
            index = line.find("->")
            start, end, port = line[index + 2 :].strip().split(",")
            port = None if port.strip() == "None" else int(port)
            start = None if start.strip() == "None" else start.strip()
            end = None if end.strip() == "None" else end.strip()
            result.append((line[: index - 2].strip(), (start, end, port)))
    return result


@pytest.mark.parametrize("txt, expected", _getdata())
def test_parse_expr(txt, expected):
    assert ips.parse_expr(txt) == expected

    # two different ports
    pytest.raises(
        ips.AddressParsingError, ips.parse_expr, "127.0.0.1:9999-127.0.0.3:1234"
    )

    # misisng port
    pytest.raises(ips.AddressParsingError, ips.parse_expr, "127.0.0.1:")

    # port not int (or mix/match hostnames with ipaddress
    pytest.raises(ips.AddressParsingError, ips.parse_expr, "127.0.0.1:hello")

    pytest.raises(ips.AddressParsingError, ips.parse_expr, "hostname:")


def test_splitip():
    assert ips.splitip("123.1.2.3") == ("123.1.2.3", None)
    assert ips.splitip("123.1.2.3:123") == ("123.1.2.3", 123)
    pytest.raises(RuntimeError, ips.splitip, "123.1.2222.3:123")


def test_iter_ip_ranges():
    assert set(ips.iter_ip_ranges("127.0.0.1")) == {("127.0.0.1", None)}
    assert set(ips.iter_ip_ranges("127.0.0.1:8080")) == {("127.0.0.1", 8080)}

    # ip-ip or ip:ip
    alts = ["127.0.0.1-127.0.0.3", "127.0.0.1:127.0.0.3"]
    for alt in alts:
        assert set(ips.iter_ip_ranges(alt)) == {
            ("127.0.0.1", None),
            ("127.0.0.2", None),
            ("127.0.0.3", None),
        }

    # ip:port-ip or ip:port:ip
    alts = []
    for alt in alts:
        assert set(ips.iter_ip_ranges(alt)) == {
            ("127.0.0.1", 8080),
            ("127.0.0.2", 8080),
            ("127.0.0.3", 8080),
        }

    # ip-ip:port or ip:ip:port
    alts = [
        "127.0.0.1:8080-127.0.0.3",
        "127.0.0.1:8080:127.0.0.3",
        "127.0.0.1-127.0.0.3:8080",
        "127.0.0.1:127.0.0.3:8080",
        "127.0.0.1:8080-127.0.0.3:8080",
        "127.0.0.1:8080:127.0.0.3:8080",
    ]
    for alt in alts:
        assert set(ips.iter_ip_ranges(alt)) == {
            ("127.0.0.1", 8080),
            ("127.0.0.2", 8080),
            ("127.0.0.3", 8080),
        }

    _ = set(ips.iter_ip_ranges("127.0.0.1:8080:127.0.0.3:8080"))
    pytest.raises(
        ips.AddressParsingError,
        set,
        ips.iter_ip_ranges("127.0.0.1:8080:127.0.0.3:8081"),
    )

    assert set(ips.iter_ip_ranges("127.0.0.1:1234 - 127.0.0.3, 127.0.0.15:999")) == {
        ("127.0.0.1", 1234),
        ("127.0.0.2", 1234),
        ("127.0.0.3", 1234),
        ("127.0.0.15", 999),
    }


def test_load_ips_from_csv(resolver):
    pytest.raises(FileNotFoundError, ips.load_ips_from_csv, "/xwexwe/ewdew")

    assert ips.load_ips_from_csv(resolver.lookup("miners.csv")) == [
        ("127.0.0.1", 4028),
        ("127.0.0.2", 8080),
        ("127.0.0.3", 4028),
        ("127.0.0.4", 4028),
        ("127.0.0.5", 9999),
        ("127.0.0.6", 9999),
        ("127.0.0.7", 9999),
        ("somehost", 4028),
        ("another.host", 4028),
        ("one.more", 12345),
    ]


def test_load_ips_from_yaml(resolver):
    pytest.raises(FileNotFoundError, ips.load_ips_from_yaml, "/xwexwe/ewdew")
    pytest.raises(
        ips.DataParsingError, ips.load_ips_from_yaml, resolver.lookup("miners.csv")
    )

    assert ips.load_ips_from_yaml(resolver.lookup("miners.yaml")) == [
        ("127.0.0.1", 4028),
        ("127.0.0.2", 8080),
        ("127.0.0.3", 4028),
        ("127.0.0.4", 4028),
        ("127.0.0.5", 9999),
        ("127.0.0.6", 9999),
        ("127.0.0.7", 9999),
        ("an.host", 4028),
        ("another.host", 111),
    ]
