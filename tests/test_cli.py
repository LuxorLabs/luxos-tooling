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


def test_wrapped_cli():
    @cli.cli()
    def main(parser):
        """a simple main function

           Lorem Ipsum is simply dummy text of the printing and
         typesetting industry. Lorem Ipsum has been the industry's
        dummy text ever since the 1500s, when an unknown printer
          took a galley of type and scrambled it to make a type specimen book.
        """
        assert isinstance(parser, argparse.ArgumentParser)

    @cli.cli()
    def main2(parser):
        """another simple main function

        Lorem Ipsum is simply dummy text of the printing and
            typesetting industry. Lorem Ipsum has been the industry's standard
          dummy text ever since the 1500s, when an unknown printer
        took a galley of type and scrambled it to make a type specimen book.

        """
        assert isinstance(parser, argparse.ArgumentParser)

    assert main.attributes["doc"] == main.__doc__
    assert main2.attributes["doc"] == main2.__doc__
