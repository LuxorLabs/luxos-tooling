import argparse

import pytest

from luxos.cli import shared


class Flag(shared.ArgumentTypeBase):
    def __init__(self, only_odd=False):
        self.only_odd = only_odd
        super().__init__()

    def validate(self, txt):
        value = int(txt)
        if self.only_odd:
            if (value % 2) == 0:
                raise argparse.ArgumentTypeError(f"non odd value '{txt}'")
        return value


def test_check_default_constructor():
    """verifies the class constructor requires no arguments"""

    class A:
        def __init__(self, value):
            pass

    pytest.raises(RuntimeError, shared.check_default_constructor, A)

    class A:
        def __init__(self, value=1):
            pass

    assert shared.check_default_constructor(A) is None


def test_add_argument():
    """test all failures mode for add_argument default"""
    p = shared.LuxosParserBase([], exit_on_error=False)

    with pytest.raises(ValueError) as e:
        p.add_argument("--flag", type=Flag, default="yyy")
    assert e.value.args[0] == "invalid literal for int() with base 10: 'yyy'"

    with pytest.raises(RuntimeError) as e:
        p.add_argument("--flag", type=Flag(only_odd=True), default="124")
    assert e.value.args[0] == "cannot use value='124' as default: non odd value '124'"

    with pytest.raises(RuntimeError) as e:
        p.add_argument("--flag", type=Flag(only_odd=True), default=124)
    assert e.value.args[0] == "cannot use value=124 as default: non odd value '124'"

    with pytest.raises(RuntimeError) as e:
        p.add_argument("--flag", type=Flag(only_odd=True), default=126)
    assert e.value.args[0] == "cannot use value=126 as default: non odd value '126'"

    with pytest.raises(RuntimeError) as e:
        p.add_argument("--flag", type=Flag(only_odd=True), default="126")
    assert e.value.args[0] == "cannot use value='126' as default: non odd value '126'"

    p.add_argument("--flag", type=Flag)
    assert (
        len(
            action := [
                a for a in p._actions if isinstance(a.type, shared.ArgumentTypeBase)
            ]
        )
        == 1
    )
    assert action[0].default.default is shared.ArgumentTypeBase._NA

    p.add_argument("--flag1", type=Flag, default="124")
    assert (
        len(
            actions := [
                a for a in p._actions if isinstance(a.type, shared.ArgumentTypeBase)
            ]
        )
        == 2
    )
    assert actions[1].default.default == 124

    p.add_argument("--flag2", type=Flag, default=126)
    assert (
        len(
            actions := [
                a for a in p._actions if isinstance(a.type, shared.ArgumentTypeBase)
            ]
        )
        == 3
    )
    assert actions[2].default.default == 126


def test_special_flag_no_restriction():
    """parse arguments with no default and no constrain on Flag"""
    p = shared.LuxosParserBase([], exit_on_error=False)
    p.add_argument("--flag", type=Flag)

    a = p.parse_args([])
    assert a.flag is None

    a = p.parse_args(
        [
            "--flag",
            "123",
        ]
    )
    assert a.flag == 123

    a = p.parse_args(
        [
            "--flag",
            "124",
        ]
    )
    assert a.flag == 124

    with pytest.raises(argparse.ArgumentError) as e:
        p.parse_args(["--flag", "boo"])
    assert e.value.args[-1] == "invalid Flag value: 'boo'"

    # same as above but with a default fallback
    p = shared.LuxosParserBase([], exit_on_error=False)
    p.add_argument("--flag", type=Flag, default="42")

    a = p.parse_args([])
    assert a.flag == 42

    a = p.parse_args(
        [
            "--flag",
            "123",
        ]
    )
    assert a.flag == 123

    a = p.parse_args(
        [
            "--flag",
            "124",
        ]
    )
    assert a.flag == 124

    with pytest.raises(argparse.ArgumentError) as e:
        p.parse_args(["--flag", "boo"])
    assert e.value.args[-1] == "invalid Flag value: 'boo'"


def test_special_flag_with_restriction_no_default():
    p = shared.LuxosParserBase([], exit_on_error=False)
    p.add_argument("--flag", type=Flag(only_odd=True))

    a = p.parse_args([])
    assert a.flag is None

    a = p.parse_args(
        [
            "--flag",
            "123",
        ]
    )
    assert a.flag == 123

    with pytest.raises(argparse.ArgumentError) as e:
        p.parse_args(["--flag", "122"])
    assert e.value.args[-1] == "non odd value '122'"

    with pytest.raises(argparse.ArgumentError) as e:
        p.parse_args(["--flag", "boo"])
    assert e.value.args[-1] == "invalid Flag value: 'boo'"

    # same as above but with a default fallback
    p = shared.LuxosParserBase([], exit_on_error=False)
    p.add_argument("--flag", type=Flag(only_odd=True), default=43)

    a = p.parse_args([])
    assert a.flag == 43

    a = p.parse_args(
        [
            "--flag",
            "123",
        ]
    )
    assert a.flag == 123

    with pytest.raises(argparse.ArgumentError) as e:
        p.parse_args(["--flag", "122"])
    assert e.value.args[-1] == "non odd value '122'"

    with pytest.raises(argparse.ArgumentError) as e:
        p.parse_args(["--flag", "boo"])
    assert e.value.args[-1] == "invalid Flag value: 'boo'"
