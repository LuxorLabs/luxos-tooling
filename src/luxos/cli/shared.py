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
        if name in {"self", "args", "kwargs"}:
            continue
        if value.default is inspect.Signature.empty:
            raise RuntimeError(f"the {klass}() cannot be called without arguments")


# The luxor base parser
class LuxosParserBase(argparse.ArgumentParser):
    def __init__(self, modules: list[types.ModuleType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modules = modules
        self.callbacks: list[ArgsCallback | None] = []

    def parse_args(self, args=None, namespace=None):
        options = super().parse_args(args, namespace)
        for name in dir(options):
            if isinstance(getattr(options, name), ArgumentTypeBase):
                fallback = getattr(options, name).value
                setattr(
                    options,
                    name,
                    None if fallback is ArgumentTypeBase._NA else fallback,
                )
        return options

    def add_argument(self, *args, **kwargs):
        typ = kwargs.get("type")
        obj = None
        if isinstance(typ, type) and issubclass(typ, ArgumentTypeBase):
            check_default_constructor(typ)
            obj = typ()
        if isinstance(typ, ArgumentTypeBase):
            obj = typ
        if obj is not None:
            obj.default = kwargs.get("default", ArgumentTypeBase._NA)
            kwargs["default"] = obj
            kwargs["type"] = obj
        super().add_argument(*args, **kwargs)


class ArgumentTypeBase:
    class _NA:
        pass

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self._default = self._NA
        self.__name__ = self.__class__.__name__

    @property
    def default(self):
        return self._default

    @default.setter
    def default(self, value):
        if value is ArgumentTypeBase._NA:
            self._default = ArgumentTypeBase._NA
        else:
            self._default = self._validate(value)
        return self._default

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
