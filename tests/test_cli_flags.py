import argparse
import datetime

import pytest

from luxos.cli import flags
from luxos.cli.v1 import AbortWrongArgumentError


def test_type_ipaddress_type():
    assert flags.type_ipaddress(strict=False)("hello").value == ("hello", None)
    assert flags.type_ipaddress(strict=False)("hello:123").value == ("hello", 123)

    pytest.raises(argparse.ArgumentTypeError, flags.type_ipaddress(), "12:dwedwe")


def test_type_ipaddress():
    from luxos.cli import v1 as cli

    # test with the class as type
    parser = cli.LuxosParser([])
    parser.add_argument("--address", type=flags.type_ipaddress)

    assert parser.parse_args([]).address is None
    assert parser.parse_args(["--address", "127.0.0.1"]).address == ("127.0.0.1", None)
    assert parser.parse_args(["--address", "127.0.0.1:123"]).address == (
        "127.0.0.1",
        123,
    )
    pytest.raises(
        AbortWrongArgumentError, parser.parse_args, ["--address", "hello:123"]
    )
    pytest.raises(AbortWrongArgumentError, parser.parse_args, ["--address", "hello"])

    # test with the class as type and a default of None
    parser = cli.LuxosParser([])
    parser.add_argument("--address", type=flags.type_ipaddress, default=None)

    assert parser.parse_args([]).address is None
    assert parser.parse_args(["--address", "127.0.0.1"]).address == ("127.0.0.1", None)
    assert parser.parse_args(["--address", "127.0.0.1:123"]).address == (
        "127.0.0.1",
        123,
    )
    pytest.raises(
        AbortWrongArgumentError, parser.parse_args, ["--address", "hello:123"]
    )
    pytest.raises(AbortWrongArgumentError, parser.parse_args, ["--address", "hello"])

    # test with the instance as type and a default of None
    parser = cli.LuxosParser([])
    parser.add_argument(
        "--address", type=flags.type_ipaddress(strict=True), default=None
    )

    assert parser.parse_args([]).address is None
    assert parser.parse_args(["--address", "127.0.0.1"]).address == ("127.0.0.1", None)
    assert parser.parse_args(["--address", "127.0.0.1:123"]).address == (
        "127.0.0.1",
        123,
    )
    pytest.raises(
        AbortWrongArgumentError, parser.parse_args, ["--address", "hello:123"]
    )
    pytest.raises(AbortWrongArgumentError, parser.parse_args, ["--address", "hello"])

    # test with the instance as type with strict set to False and a default of None
    parser = cli.LuxosParser([])
    parser.add_argument(
        "--address", type=flags.type_ipaddress(strict=False), default=None
    )

    assert parser.parse_args([]).address is None
    assert parser.parse_args(["--address", "127.0.0.1"]).address == ("127.0.0.1", None)
    assert parser.parse_args(["--address", "127.0.0.1:123"]).address == (
        "127.0.0.1",
        123,
    )
    assert parser.parse_args(["--address", "hello"]).address == ("hello", None)
    assert parser.parse_args(["--address", "hello:123"]).address == ("hello", 123)

    # tests with a invalid default
    with pytest.raises(RuntimeError) as x:
        cli.LuxosParser([]).add_argument(
            "--address", type=flags.type_ipaddress, default="xwc"
        )
    assert x.value.args[0].startswith("cannot use value='xwc' as default")
    with pytest.raises(RuntimeError) as x:
        cli.LuxosParser([]).add_argument(
            "--address", type=flags.type_ipaddress(strict=True), default="xwc"
        )
    assert x.value.args[0].startswith("cannot use value='xwc' as default")

    cli.LuxosParser([]).add_argument(
        "--address", type=flags.type_ipaddress(strict=False), default="xwc"
    )
    cli.LuxosParser([]).add_argument(
        "--address", type=flags.type_ipaddress(strict=False), default="xwc:123"
    )
    with pytest.raises(RuntimeError) as x:
        cli.LuxosParser([]).add_argument(
            "--address", type=flags.type_ipaddress(strict=False), default="xwc:12:2"
        )
    with pytest.raises(RuntimeError) as x:
        cli.LuxosParser([]).add_argument(
            "--address", type=flags.type_ipaddress(strict=False), default="xwc:sqwq"
        )


def test_type_range(resolver):
    assert flags.type_range("127.0.0.1") == [("127.0.0.1", None)]
    assert flags.type_range("127.0.0.1:1234") == [("127.0.0.1", 1234)]
    assert flags.type_range("127.0.0.1:127.0.0.3") == [
        ("127.0.0.1", None),
        ("127.0.0.2", None),
        ("127.0.0.3", None),
    ]

    assert flags.type_range("a.host") == [
        ("a.host", None),
    ]
    assert flags.type_range("a.host:111") == [
        ("a.host", 111),
    ]

    # many ways to express the same range
    fmts = [
        "127.0.0.1:1234-127.0.0.2",
        "127.0.0.1:1234:127.0.0.2",
        "127.0.0.1:1234:127.0.0.2:1234",
        "127.0.0.1:127.0.0.2:1234",
        "127.0.0.1-127.0.0.2:1234",
        "127.0.0.1:1234-127.0.0.2:1234",
    ]
    for fmt in fmts:
        assert flags.type_range(fmt) == [
            ("127.0.0.1", 1234),
            ("127.0.0.2", 1234),
        ]

    pytest.raises(argparse.ArgumentTypeError, flags.type_range, "12")
    pytest.raises(argparse.ArgumentTypeError, flags.type_range, "a.host:another.host")


def test_type_hhmm():
    assert flags.type_hhmm()("12:34").value == datetime.time(12, 34)
    pytest.raises(argparse.ArgumentTypeError, flags.type_hhmm(), "12")
