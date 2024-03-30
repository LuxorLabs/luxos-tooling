# catch-all module (find later a better place)
from __future__ import annotations
import sys
import itertools


if sys.version_info >= (3, 12):
    batched = itertools.batched
else:
    def batched(iterable, n):
        if n < 1:
            raise ValueError("n must be at least one")
        it = iter(iterable)
        while batch := tuple(itertools.islice(it, n)):
            yield batch


def indent(txt: str, pre: str = " " * 2) -> str:
    """simple text indentation"""

    from textwrap import dedent

    txt = dedent(txt)
    if txt.endswith("\n"):
        last_eol = "\n"
        txt = txt[:-1]
    else:
        last_eol = ""

    result = pre + txt.replace("\n", "\n" + pre) + last_eol
    return result if result.strip() else result.strip()