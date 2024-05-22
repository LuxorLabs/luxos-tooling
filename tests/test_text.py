# ruff: noqa: W291, W293
import pytest

from luxos import text

try:
    import rich
except ModuleNotFoundError:
    rich = None  # type: ignore


def test_indent():
    txt = """

            Lorem Ipsum is simply dummy text of the printing and
          typesetting industry. Lorem Ipsum has been the industry's standard
         dummy text ever since the 1500s, when an unknown printer
           took a galley of type and scrambled it to make a type specimen book.
"""

    assert (
        text.indent(txt, "." * 2)
        == """\
..
..
..   Lorem Ipsum is simply dummy text of the printing and
.. typesetting industry. Lorem Ipsum has been the industry's standard
..dummy text ever since the 1500s, when an unknown printer
..  took a galley of type and scrambled it to make a type specimen book.
"""
    )


def test_indent2():
    txt = """\
     An unusually complicated text
    with un-even indented lines
   that make life harder
"""
    assert (
        text.indent(txt, pre="..")
        == """\
..  An unusually complicated text
.. with un-even indented lines
..that make life harder
"""
    )


def test_md():
    txt = """
    ### An example

    This is an example of help file, written in MD. The text.md(txt) function should
    format this nicely:
    
    - item 1
    - item 2
    
    | Tables   |      Are      |  Cool |
    |----------|:-------------:|------:|
    | col 1 is |  left-aligned | $1600 |
    | col 2 is |    centered   |   $12 |
    | col 3 is | right-aligned |    $1 |
"""

    assert (
        text.md(txt, md=False)
        == """
### An example

This is an example of help file, written in MD. The text.md(txt) function should
format this nicely:

- item 1
- item 2

| Tables   |      Are      |  Cool |
|----------|:-------------:|------:|
| col 1 is |  left-aligned | $1600 |
| col 2 is |    centered   |   $12 |
| col 3 is | right-aligned |    $1 |
"""
    )


@pytest.mark.skipif(not rich, reason="need rich installed")
def test_md_rich():
    txt = """
        ### An example

        This is an example of help file, written in MD. The text.md(txt) function should
        format this nicely:

        - item 1
        - item 2

        | Tables   |      Are      |  Cool |
        |----------|:-------------:|------:|
        | col 1 is |  left-aligned | $1600 |
        | col 2 is |    centered   |   $12 |
        | col 3 is | right-aligned |    $1 |
    """

    assert (
        text.md(txt, width=80)
        == """\
                                   An example                                   

This is an example of help file, written in MD. The text.md(txt) function should
format this nicely:                                                             

 • item 1                                                                       
 • item 2                                                                       

                                    
  Tables          Are         Cool  
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 
  col 1 is   left-aligned    $1600  
  col 2 is     centered        $12  
  col 3 is   right-aligned      $1  
                                    
"""
    )
    pass
