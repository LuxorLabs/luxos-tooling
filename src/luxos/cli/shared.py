from __future__ import annotations

import argparse
import sys
import types
from typing import Callable

# The return type of add_arguments

if sys.version_info >= (3, 10):
    ArgsCallback = Callable[[argparse.Namespace], None | argparse.Namespace]
else:
    ArgsCallback = Callable


# The luxor base parser
class LuxosParserBase(argparse.ArgumentParser):
    def __init__(self, modules: list[types.ModuleType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modules = modules
        self.callbacks: list[ArgsCallback | None] = []

    def add_argument(self, *args, **kwargs):
        try:
            if issubclass(kwargs.get("type"), ArgumentTypeBase):
                kwargs["default"] = kwargs.get("type")(kwargs.get("default"))
                kwargs["type"] = kwargs["default"]
        except TypeError:
            pass
        super().add_argument(*args, **kwargs)


class ArgumentTypeBase:
    class _NA:
        pass

    def __init__(self, default=_NA):
        self.default = default
        if default is not ArgumentTypeBase._NA:
            self.default = self._validate(default)

    def __call__(self, txt):
        self._value = None
        self._value = self._validate(txt)
        return self

    @property
    def value(self):
        return getattr(self, "_value", self.default)

    def _validate(self, value):
        try:
            return self.validate(value)
        except argparse.ArgumentTypeError as exc:
            if not hasattr(self, "_value"):
                raise RuntimeError(f"cannot use {value=} as default: {exc.args[0]}")
            raise

    def validate(self, txt):
        raise NotImplementedError("need to implement the .validate(self, txt)  method")
