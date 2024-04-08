import argparse
import sys
from unittest import mock

from luxos.cli import v1 as cli


def test_docstring():
    @cli.cli()
    def hello():
        "this is a docstring"
        pass

    assert hello.__doc__ == "this is a docstring"


def test_callme():
    @cli.cli()
    def main(parser):
        assert isinstance(parser, argparse.ArgumentParser)

    main()

    args = ["dummy.py"]
    with mock.patch.object(sys, "argv", args):

        @cli.cli()
        def main2(args):
            assert isinstance(args, argparse.Namespace)

        main2()
