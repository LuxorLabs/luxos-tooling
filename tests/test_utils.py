## NOTE ##
# Some of these tests spawn an underlying server, it might be better not run
# unattended. Some also require a miner, we might not have it handy.
import asyncio

import pytest

import luxos.asyncops
from luxos import utils


@pytest.mark.manual
@pytest.mark.asyncio
async def test_basic_call(echopool):
    """places few round trip calls"""
    echopool.start(1)
    host, port = echopool.addresses[0]

    # this will bomb at around 10k
    for index in range(1_000):
        ret = await luxos.asyncops.roundtrip(
            host, port, f"hello world {index}", asjson=False
        )
        assert ret == f"received by ('{host}', {port}): hello world {index}"


@pytest.mark.manual
@pytest.mark.asyncio
async def test_basic_batched_call(echopool):
    """places few round trip calls"""
    echopool.start(1)
    host, port = echopool.addresses[0]

    # this will bomb at around 10k if run sequentially!
    calls = [
        luxos.asyncops.roundtrip(host, port, f"hello world {index}", asjson=False)
        for index in range(10_000)
    ]
    expected = {
        f"received by ('{host}', {port}): hello world {index}"
        for index in range(len(calls))
    }
    found = set()
    from luxos.misc import batched

    for group in batched(calls, 100):
        tasks = await asyncio.gather(*group, return_exceptions=True)
        found.update(tasks)
    assert expected == found


@pytest.mark.manual
@pytest.mark.asyncio
async def test_util_launch_oneshot(echopool):
    """places few round trip calls"""
    echopool.start(1)
    host, port = echopool.addresses[0]

    async def call(index, *_):
        return await luxos.asyncops.roundtrip(
            host, port, f"hello world {index}", asjson=False
        )

    addresses = [(index, None) for index in range(10)]

    expected = {
        f"received by ('{host}', {port}): hello world {index}" for index, _ in addresses
    }

    ret = await utils.launch(addresses, call)
    assert set(ret) == expected


@pytest.mark.manual
@pytest.mark.asyncio
async def test_util_launch_batched(echopool):
    """places *many* round trip calls"""

    echopool.start(1)
    host, port = echopool.addresses[0]

    async def call(index, *_):
        return await luxos.asyncops.roundtrip(
            host, port, f"hello world {index}", asjson=False
        )

    # utils.launch will choke at 10k without batch argument
    addresses = [(index, None) for index in range(10_000)]
    expected = {
        f"received by ('{host}', {port}): hello world {index}" for index, _ in addresses
    }

    ret = await utils.launch(addresses, call, batch=100)
    assert set(ret) == expected


def test_util_ip_ranges():
    assert set(utils.ip_ranges("127.0.0.1")) == {("127.0.0.1", None)}
    assert set(utils.ip_ranges("127.0.0.1->127.0.0.3", gsep="\n", rsep="->")) == {
        ("127.0.0.1", None),
        ("127.0.0.2", None),
        ("127.0.0.3", None),
    }
    assert set(utils.ip_ranges("127.0.0.1-127.0.0.3\n127.0.0.15", gsep="\n")) == {
        ("127.0.0.1", None),
        ("127.0.0.2", None),
        ("127.0.0.3", None),
        ("127.0.0.15", None),
    }
