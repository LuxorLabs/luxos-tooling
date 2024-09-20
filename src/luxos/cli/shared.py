from __future__ import annotations

import argparse
import inspect
import sys
import types
from typing import Callable

# The return type of add_arguments

if sys.version_info >= (3, 10):
    ArgsCallback = Callable[[argparse.Namespace], None | argparse.Namespace]
else:
    ArgsCallback = Callable


def check_default_constructor(klass: type):
    signature = inspect.signature(klass.__init__)  # type: ignore[misc]
    for name, value in signature.parameters.items():
        if name == "self":
            continue
        if value.default is inspect.Signature.empty:
            raise RuntimeError(f"the {klass}() cannot be called without arguments")


# The luxor base parser
class LuxosParserBase(argparse.ArgumentParser):
    def __init__(self, modules: list[types.ModuleType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modules = modules
        self.callbacks: list[ArgsCallback | None] = []

    def add_argument(self, *args, **kwargs):
        typ = kwargs.get("type")
        if isinstance(typ, type) and issubclass(typ, ArgumentTypeBase):
            check_default_constructor(typ)
            obj = typ()
            obj.default = kwargs.get("default")
            kwargs["default"] = obj
            kwargs["type"] = obj
        if isinstance(typ, ArgumentTypeBase):
            kwargs["default"] = typ.new2(kwargs.get("default"))
            kwargs["type"] = kwargs["default"]
        super().add_argument(*args, **kwargs)


class ArgumentTypeBase:
    class _NA:
        pass

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self._default = self._NA

    @property
    def default(self):
        return self._default

    @default.setter
    def default(self, value):
        self._default = self._validate(value)
        return self._default

    @classmethod
    def new(cls, obj=_NA):
        result = cls()
        result.default = obj
        if result.default is not ArgumentTypeBase._NA:
            result.default = result._validate(result.default)
        return result

    def new2(self, default):
        self.default = default
        return self

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
