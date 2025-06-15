import argparse
import datetime

import pytest

from luxos.cli import flags


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
    assert flags.type_hhmm().validate("12:34") == datetime.time(12, 34)

    with pytest.raises(argparse.ArgumentTypeError) as e:
        flags.type_hhmm().validate("12")
    assert e.value.args[-1] == "failed conversion into HH:MM for '12'"

    with pytest.raises(argparse.ArgumentTypeError) as e:
        flags.type_hhmm().validate("hello")
    assert e.value.args[-1] == "failed conversion into HH:MM for 'hello'"
