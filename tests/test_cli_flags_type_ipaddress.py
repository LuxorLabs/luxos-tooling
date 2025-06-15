import argparse

import pytest

from luxos.cli import flags


def test_type_ipaddress_validate():
    assert flags.type_ipaddress(strict=False).validate("hello") == ("hello", None)
    assert flags.type_ipaddress(strict=False).validate("hello:123") == ("hello", 123)

    with pytest.raises(argparse.ArgumentTypeError) as e:
        flags.type_ipaddress(strict=True).validate("hello")
    assert e.value.args[-1] == (
        "failed to convert to a strict ip address: "
        "cannot convert 'hello' into an ipv4 address N.N.N.N"
    )

    with pytest.raises(argparse.ArgumentTypeError) as e:
        flags.type_ipaddress(strict=True).validate("1.2.3.4:hello")
    assert e.value.args[-1] == (
        "failed to convert to a strict ip address: "
        "cannot convert 'hello' to an integer"
    )

    assert flags.type_ipaddress(strict=True).validate("1.2.3.4:567") == ("1.2.3.4", 567)


def test_type_ipaddress_no_args(cli_generator):
    parser = cli_generator().add_argument("address", type=flags.type_ipaddress)

    with pytest.raises(argparse.ArgumentError) as e:
        parser.parse_args([])
    assert e.value.args[-1] == "the following arguments are required: address"

    with pytest.raises(argparse.ArgumentError) as e:
        parser.parse_args(["hello"])
    assert e.value.args[-1] == (
        "failed to convert to a strict ip address: "
        "cannot convert 'hello' into an ipv4 address N.N.N.N"
    )

    with pytest.raises(argparse.ArgumentError) as e:
        parser.parse_args(["1.2.3.4:booo"])
    assert e.value.args[-1] == (
        "failed to convert to a strict ip address: "
        "cannot convert 'booo' to an integer"
    )

    assert parser.parse_args(["1.2.3.4"]).address == ("1.2.3.4", None)
    assert parser.parse_args(["1.2.3.4:123"]).address == ("1.2.3.4", 123)


def test_type_ipaddress_no_args_default(cli_generator):
    with pytest.raises(RuntimeError) as e:
        cli_generator().add_argument(
            "address", type=flags.type_ipaddress, default="xxx"
        )
    assert e.value.args[-1] == (
        "cannot use value='xxx' as default: "
        "failed to convert to a strict ip address: "
        "cannot convert 'xxx' into an ipv4 address N.N.N.N"
    )

    with pytest.raises(RuntimeError) as e:
        cli_generator().add_argument(
            "address", type=flags.type_ipaddress, default="1.2.3.4:no"
        )
    assert e.value.args[-1] == (
        "cannot use value='1.2.3.4:no' as default: "
        "failed to convert to a strict ip address: "
        "cannot convert 'no' to an integer"
    )

    parser = cli_generator().add_argument(
        "address", type=flags.type_ipaddress, nargs="?", default="1.2.3.4"
    )
    assert parser.parse_args([]).address == ("1.2.3.4", None)

    parser = cli_generator().add_argument(
        "address", type=flags.type_ipaddress, nargs="?", default="1.2.3.4:123"
    )
    assert parser.parse_args([]).address == ("1.2.3.4", 123)

    parser = cli_generator().add_argument(
        "address", type=flags.type_ipaddress, nargs="?", default="1.2.3.4:123"
    )
    assert parser.parse_args(["5.6.7.8"]).address == ("5.6.7.8", None)

    parser = cli_generator().add_argument(
        "address", type=flags.type_ipaddress, nargs="?", default="1.2.3.4:123"
    )
    assert parser.parse_args(["5.6.7.8:90"]).address == ("5.6.7.8", 90)


def test_type_ipaddress_with_args(cli_generator):
    with pytest.raises(RuntimeError) as e:
        cli_generator().add_argument(
            "address", type=flags.type_ipaddress(strict=True), default="xxx"
        )
    assert e.value.args[-1] == (
        "cannot use value='xxx' as default: "
        "failed to convert to a strict ip address: "
        "cannot convert 'xxx' into an ipv4 address N.N.N.N"
    )
    cli_generator().add_argument(
        "address", type=flags.type_ipaddress(strict=False), default="xxx"
    )

    parser = cli_generator().add_argument(
        "address", type=flags.type_ipaddress(port=456), nargs="?", default="1.2.3.4"
    )
    assert parser.parse_args([]).address == ("1.2.3.4", 456)
    assert parser.parse_args(["5.6.7.8"]).address == ("5.6.7.8", 456)
    assert parser.parse_args(["5.6.7.8:90"]).address == ("5.6.7.8", 90)
