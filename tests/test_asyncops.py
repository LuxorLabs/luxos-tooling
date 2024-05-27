from __future__ import annotations

import asyncio
import contextlib
import os

import pytest

import luxos.asyncops as aapi
from luxos import exceptions, misc

## NOTE ##
# This tests spawn an underlying server, it might be better not run
# unattended. Some also require a miner, we might not have it handy.
pytestmark = pytest.mark.manual


def getminer() -> None | tuple[str, int]:
    if not (minerd := os.getenv("LUXOS_TEST_MINER")):
        return None
    host, port = minerd.split(":")
    return host.strip(), int(port)


def test_rexec_parameters():
    assert aapi._rexec_parameters(None) == []
    assert aapi._rexec_parameters("hello") == ["hello"]
    assert aapi._rexec_parameters(["hello", "world"]) == ["hello", "world"]
    assert aapi._rexec_parameters(["hello", 1]) == ["hello", "1"]
    assert aapi._rexec_parameters({"hello": 1}) == ["hello=1"]
    assert aapi._rexec_parameters({"hello": True}) == ["hello=true"]


def test_validate_message():
    pytest.raises(
        exceptions.MinerCommandMalformedMessageError, aapi.validate_message, "a", 0, {}
    )
    host, port = "a", 0

    assert aapi.validate_message(host, port, {"STATUS": 1, "id": 2})

    pytest.raises(
        exceptions.MinerCommandMalformedMessageError,
        aapi.validate_message,
        host,
        port,
        {
            "STATUS": 1,
            "id": 2,
        },
        "wooow",
    )

    assert aapi.validate_message(
        host, port, {"STATUS": 1, "id": 2, "wooow": [1, 2]}, "wooow"
    )

    with pytest.raises(exceptions.MinerCommandMalformedMessageError) as excinfo:
        aapi.validate_message(
            host, port, {"STATUS": 1, "id": 2, "wooow": [1, 2]}, "wooow", minfields=9
        )
    assert excinfo.value.args[2] == "found 2 fields for wooow invalid: 2 <= 9"

    with pytest.raises(exceptions.MinerCommandMalformedMessageError) as excinfo:
        aapi.validate_message(
            host, port, {"STATUS": 1, "id": 2, "wooow": [1, 2]}, "wooow", maxfields=1
        )
    assert excinfo.value.args[2] == "found 2 fields for wooow invalid: 2 >= 1"

    with pytest.raises(exceptions.MinerCommandMalformedMessageError) as excinfo:
        aapi.validate_message(
            host,
            port,
            {"STATUS": 1, "id": 2, "wooow": [1, 2]},
            "wooow",
            minfields=9,
            maxfields=10,
        )
    assert excinfo.value.args[2] == "found 2 fields for wooow invalid: 2 <= 9"

    assert aapi.validate_message(
        host,
        port,
        {"STATUS": 1, "id": 2, "wooow": [1, 2]},
        "wooow",
        minfields=2,
        maxfields=10,
    )


@pytest.mark.asyncio
async def test_private_roundtrip_one_listener(echopool):
    """checks roundrtip sends and receive a message (1-listener)"""
    echopool.start(1, mode="echo+")
    host, port = echopool.addresses[0]
    ret = await aapi._roundtrip(host, port, "hello", None)
    assert ret == f"received by ('{host}', {port}): hello"


@pytest.mark.asyncio
async def test_private_roundtrip_many_listeners(echopool):
    """checks the roundrip can connect en-masse to many lsiteners"""
    echopool.start(100, mode="echo+")

    blocks = {}
    for index, group in enumerate(misc.batched(echopool.addresses, 10)):
        tasks = []
        for host, port in group:
            tasks.append(aapi._roundtrip(host, port, "hello olleh", None))
        blocks[index] = await asyncio.gather(*tasks, return_exceptions=True)

    assert len(blocks) == 10
    assert sum(len(x) for x in blocks.values()) == 100
    allitems = [item for b in blocks.values() for item in b]
    assert f"received by {echopool.addresses[3]}: hello olleh" in allitems


@pytest.mark.skipif(not getminer(), reason="need to set LUXOS_TEST_MINER")
@pytest.mark.asyncio
async def test_miner_logon_logoff_cycle():
    host, port = getminer()

    sid = None
    try:
        sid = await aapi.logon(host, port)
    except exceptions.MinerCommandSessionAlreadyActive as e:
        raise RuntimeError("a session is already active on {host}:{port}") from e
    finally:
        if sid:
            await aapi.logoff(host, port, sid)


@pytest.mark.skipif(not getminer(), reason="need to set LUXOS_TEST_MINER")
@pytest.mark.asyncio
async def test_miner_double_logon_cycle():
    host, port = getminer()

    sid = await aapi.logon(host, port)
    try:
        with pytest.raises(exceptions.MinerCommandSessionAlreadyActive) as excinfo:
            await aapi.logon(host, port)
        assert excinfo.value.args[0] == f"session active for {host}:{port}"
    except Exception:
        pass
    finally:
        if sid:
            await aapi.logoff(host, port, sid)


@pytest.mark.skipif(not getminer(), reason="need to set LUXOS_TEST_MINER")
@pytest.mark.asyncio
async def test_miner_version():
    host, port = getminer()

    res = await aapi.execute_command(host, port, None, "version", asjson=True)
    assert "VERSION" in res
    assert len(res["VERSION"]) == 1
    assert "API" in res["VERSION"][0]


@pytest.mark.skipif(not getminer(), reason="need to set LUXOS_TEST_MINER")
@pytest.mark.asyncio
async def test_miner_profile_sets():
    from random import choices
    from string import ascii_lowercase

    # random profile name
    profile = f"test-{''.join(choices(ascii_lowercase, k=5))}"

    # get the initial profile list
    host, port = getminer()
    profiles = (await aapi.rexec(host, port, "profiles"))["PROFILES"]
    assert profiles and profile not in {p["Profile Name"] for p in profiles}

    # create a new profile
    # TODO there's a bug
    #  when ATM is running you shouldn't be able to create/delete
    #  profiles, the following test shoudl fail at the first try
    # -> to pass this test, you need to disable ATM

    params = f"{profile},{profiles[0]['Frequency']},{profiles[0]['Voltage']}"
    await aapi.rexec(host, port, "profilenew", params)

    try:
        profiles1 = (await aapi.rexec(host, port, "profiles"))["PROFILES"]
        assert profile in {p["Profile Name"] for p in profiles1}
    finally:
        await aapi.rexec(host, port, "profilerem", profile)

    # verify we restored the same profiles
    profiles2 = (await aapi.rexec(host, port, "profiles"))["PROFILES"]
    expected = {p["Profile Name"] for p in profiles}
    found = {p["Profile Name"] for p in profiles2}
    assert found == expected


@pytest.mark.asyncio
async def test_roundtrip_timeout():
    """checks roundrtip sends and receive a message (1-listener)"""
    host, port = "127.0.0.99", 12345
    with pytest.raises(aapi.exceptions.MinerCommandTimeoutError):
        await aapi.rexec(host, port, "hello", timeout=0.5)


@pytest.mark.skipif(not getminer(), reason="need to set LUXOS_TEST_MINER")
def test_bridge_execute_command():
    from luxos.scripts.luxos import execute_command
    from luxos.utils import rexec

    # get the initial profile list
    host, port = getminer()

    def adapter(awaitable):
        with contextlib.suppress(asyncio.TimeoutError):
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(awaitable)

    out = execute_command(host, port, 3, "profiles", parameters=[], verbose=True)
    out1 = adapter(rexec(host, port, cmd="profiles"))
    assert out["PROFILES"] == out1["PROFILES"]

    port += 1
    out = execute_command(host, port, 3, "profiles", parameters=[], verbose=True)
    out1 = adapter(rexec(host, port, cmd="profiles"))
    assert out == out1
