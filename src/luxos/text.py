from __future__ import annotations

import io


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


def md(txt: str, md: bool | None = None, **kwargs) -> str:
    """convert text to markdown if rich library is present"""
    try:
        from rich.markdown import Markdown

        md = True if md is None else md
    except ModuleNotFoundError:
        md = False

    if md:
        from rich.console import Console

        buf = io.StringIO()
        console = Console(file=buf, **kwargs)
        console.print(Markdown(indent(txt, "")))
        return buf.getvalue()
    else:
        return indent(txt, "")
