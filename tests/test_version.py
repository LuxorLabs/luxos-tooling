import contextlib
import sys
import types
from unittest import mock

import pytest

from luxos import version

PYVERSION = sys.version.partition(" ")[0]

VALUES = [
    ("", "", "N/A, N/A"),
    ("1.2.3", "", "1.2.3, N/A"),
    ("1.2.3", "abcdef", "1.2.3, abcdef"),
    ("", "abcdef", "N/A, abcdef"),
]


@pytest.mark.parametrize("mversion, mhash, expected", VALUES)
def test_no_extra_modules(mversion, mhash, expected):
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch("luxos.version.__version__", mversion))
        stack.enter_context(mock.patch("luxos.version.__hash__", mhash))
        assert version.get_version_info() == {
            "py": PYVERSION,
            "luxos": expected,
        }
        assert version.get_version() == f"py[{PYVERSION}], luxos[{expected}]"


def test_add_module_info():
    module = types.ModuleType("xyz")
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch("luxos.version.__version__", "1.2.4"))
        stack.enter_context(mock.patch("luxos.version.__hash__", "a123b"))
        assert version.get_version_info([module]) == {
            "py": PYVERSION,
            "luxos": "1.2.4, a123b",
            "xyz": "N/A",
        }

    module.__name__ = "ABC"
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch("luxos.version.__version__", "1.2.4"))
        stack.enter_context(mock.patch("luxos.version.__hash__", "a123b"))
        assert version.get_version_info([module]) == {
            "py": PYVERSION,
            "luxos": "1.2.4, a123b",
            "ABC": "N/A",
        }

    module.__version__ = "9.9.9"
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch("luxos.version.__version__", "1.2.4"))
        stack.enter_context(mock.patch("luxos.version.__hash__", "a123b"))
        assert version.get_version_info([module]) == {
            "py": PYVERSION,
            "luxos": "1.2.4, a123b",
            "ABC": "9.9.9",
        }
