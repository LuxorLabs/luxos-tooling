from luxos import misc

def test_misc_batched():
    data = {}
    for index, group in enumerate(misc.batched(range(10), 3)):
        data[index] = group

    assert data == {
        0: (0, 1, 2),
        1: (3, 4, 5),
        2: (6, 7, 8),
        3: (9,),
    }

def test_indent():
    txt = """\
     An unusually complicated text
    with un-even indented lines
   that make life harder
"""
    assert (
        misc.indent(txt, pre="..")
        == """\
..  An unusually complicated text
.. with un-even indented lines
..that make life harder
"""
    )