from __future__ import annotations

import argparse
import types
from typing import Callable

# The return type of add_arguments
ArgsCallback = Callable[[argparse.Namespace], None | argparse.Namespace]


# The luxor base parser
class LuxosParserBase(argparse.ArgumentParser):
    def __init__(self, modules: list[types.ModuleType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modules = modules
        self.callbacks: list[ArgsCallback | None] = []
