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


def test_iter_ip_ranges():
    assert set(misc.iter_ip_ranges("127.0.0.1")) == {"127.0.0.1"}
    assert set(misc.iter_ip_ranges("127.0.0.1-127.0.0.3")) == {
        "127.0.0.1",
        "127.0.0.2",
        "127.0.0.3",
    }
    assert set(misc.iter_ip_ranges("127.0.0.1-127.0.0.3:127.0.0.15")) == {
        "127.0.0.1",
        "127.0.0.2",
        "127.0.0.3",
        "127.0.0.15",
    }
