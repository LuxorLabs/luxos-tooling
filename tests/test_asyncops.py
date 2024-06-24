from __future__ import annotations

import asyncio

import pytest

import luxos.asyncops as aapi
from luxos import exceptions, misc

## NOTE ##
# This tests spawn an underlying server, it might be better not run
# unattended. Some also require a miner, we might not have it handy.
pytestmark = pytest.mark.manual


def test_parameters_to_list():
    assert aapi.parameters_to_list(None) == []
    assert aapi.parameters_to_list(0) == ["0"]
    assert aapi.parameters_to_list([0]) == ["0"]
    assert aapi.parameters_to_list(["0"]) == ["0"]
    assert aapi.parameters_to_list("hello") == ["hello"]
    assert aapi.parameters_to_list(["hello", "world"]) == ["hello", "world"]
    assert aapi.parameters_to_list(["hello", 1]) == ["hello", "1"]
    assert aapi.parameters_to_list({"hello": 1}) == ["hello=1"]
    assert aapi.parameters_to_list({"hello": True}) == ["hello=true"]


def test_validate_message():
    # TODO add more cases
    # 1. when res is not present and limit is 0,None
    # 2. check limits like None/value value/None None/None

    # Avoid to repeat the same code over and over
    def validate(res, extrakey=None, minfields=1, maxfields=1):
        return aapi.validate_message("a-host", 0, res, extrakey, minfields, maxfields)

    res = {}
    pytest.raises(exceptions.MinerCommandMalformedMessageError, validate, res)

    res = {"STATUS": 1, "id": 2}
    assert validate(res)
    assert validate(res, "A-MISSING-KEY", 0, None) == []
    assert validate(res, "A-MISSING-KEY", None, None) == []

    pytest.raises(
        exceptions.MinerCommandMalformedMessageError, validate, res, "A-MISSING-KEY"
    )
    pytest.raises(
        exceptions.MinerCommandMalformedMessageError,
        validate,
        res,
        "A-MISSING-KEY",
        1,
        None,
    )

    res = {"STATUS": 1, "id": 2, "KEY": [1, 2, 3]}
    assert validate(res)
    assert validate(res, "KEY", 0, None) == [1, 2, 3]
    assert validate(res, "KEY", None, None) == [1, 2, 3]
    assert validate(res, "KEY", None, 5) == [1, 2, 3]
    assert validate(res, "KEY", 1, 5) == [1, 2, 3]

    with pytest.raises(exceptions.MinerCommandMalformedMessageError) as excinfo:
        validate(res, "KEY", 4, None)
    assert excinfo.value.args[2] == "found too few items for 'KEY'  (3 < 4)"

    with pytest.raises(exceptions.MinerCommandMalformedMessageError) as excinfo:
        validate(res, "KEY", 1, 2)
    assert excinfo.value.args[2] == "found too many items for 'KEY'  (3 > 2)"


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


@pytest.mark.asyncio
async def test_miner_logon_logoff_cycle(miner_host_port):
    host, port = miner_host_port

    sid = None
    try:
        sid = await aapi.logon(host, port)
    except exceptions.MinerCommandSessionAlreadyActive as e:
        raise RuntimeError("a session is already active on {host}:{port}") from e
    finally:
        if sid:
            await aapi.logoff(host, port, sid)


@pytest.mark.asyncio
async def test_miner_double_logon_cycle(miner_host_port):
    host, port = miner_host_port

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


@pytest.mark.asyncio
async def test_miner_version(miner_host_port):
    host, port = miner_host_port

    res = await aapi.rexec(host, port, "version")
    assert "VERSION" in res
    assert len(res["VERSION"]) == 1
    assert "API" in res["VERSION"][0]


# @pytest.mark.skip("a likely bug in luxminer way to set/delete profiles")
@pytest.mark.asyncio
async def test_miner_profile_sets(miner_host_port):
    from random import choices
    from string import ascii_lowercase

    # random profile name
    profile = f"test-{''.join(choices(ascii_lowercase, k=5))}"

    # get the initial profile list
    host, port = miner_host_port
    profiles = (await aapi.rexec(host, port, "profiles"))["PROFILES"]
    assert profiles and profile not in {p["Profile Name"] for p in profiles}

    # create a new profile
    # TODO there's a bug
    #  when ATM is running you shouldn't be able to create/delete
    #  profiles, the following test should fail at the first try
    # -> to pass this test, you need to disable ATM

    params = f"{profile},{profiles[0]['Frequency']},{profiles[0]['Voltage']}"
    await aapi.rexec(host, port, "profilenew", params)

    try:
        profiles1 = (await aapi.rexec(host, port, "profiles"))["PROFILES"]
        assert profile in {p["Profile Name"] for p in profiles1}
    finally:
        async with aapi.with_atm(host, port, False):
            await aapi.rexec(host, port, "profilerem", profile)

    # verify we restored the same profiles
    profiles2 = (await aapi.rexec(host, port, "profiles"))["PROFILES"]
    expected = {p["Profile Name"] for p in profiles}
    found = {p["Profile Name"] for p in profiles2}
    assert found == expected


@pytest.mark.asyncio
async def test_roundtrip_timeout(miner_host_port):
    # host, port = miner
    """checks roundrtip sends and receive a message (1-listener)"""

    # miner doesn't exist
    host, port = "127.0.0.99", 12345
    try:
        await aapi.rexec(host, port, "hello", timeout=0.5)
        assert False, "didn't raise"
    except aapi.exceptions.MinerCommandTimeoutError as exc:
        exception = exc
    assert isinstance(exception, asyncio.TimeoutError)
    assert isinstance(exception, aapi.exceptions.MinerConnectionError)
    assert isinstance(exception, aapi.exceptions.LuxosBaseException)
    text = f"<{host}:{port}>: MinerCommandTimeoutError, TimeoutError()"
    assert str(exception)[: len(text)] == text

    # not miner on a wrong port
    host, port = miner_host_port
    port = 22
    exception = None
    try:
        await aapi.rexec(host, port, "hello", timeout=0.5)
        assert False, "didn't raise"
    except aapi.exceptions.MinerCommandTimeoutError as exc:
        exception = exc
    assert isinstance(exception, asyncio.TimeoutError)
    assert isinstance(exception, aapi.exceptions.MinerConnectionError)
    assert isinstance(exception, aapi.exceptions.LuxosBaseException)
    texts = [
        f"<{host}:{port}>: MinerCommandTimeoutError, ConnectionRe",
        f"<{host}:{port}>: MinerCommandTimeoutError, TimeoutError",
    ]
    assert str(exception)[: len(texts[0])] in texts


@pytest.mark.asyncio
async def test_bridge_execute_command(miner_host_port):
    from luxos.utils import execute_command, rexec

    # get the initial profile list
    host, port = miner_host_port

    out = execute_command(host, port, 3, "profiles", parameters=[], verbose=True)
    out1 = await rexec(host, port, cmd="profiles")
    assert out["PROFILES"] == out1["PROFILES"]

    port += 1
    pytest.raises(
        ConnectionRefusedError,
        execute_command,
        host,
        port,
        3,
        "profiles",
        parameters=[],
        verbose=True,
    )
