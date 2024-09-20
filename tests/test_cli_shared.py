import pytest

from luxos.cli import shared


def test_check_default_constructor():
    class A:
        def __init__(self, value):
            pass

    pytest.raises(RuntimeError, shared.check_default_constructor, A)

    class A:
        def __init__(self, value=1):
            pass

    assert shared.check_default_constructor(A) is None
