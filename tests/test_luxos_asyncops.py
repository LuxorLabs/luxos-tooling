import os
import asyncio
import pytest
import luxos.asyncops as aapi
from luxos import exceptions
from luxos import misc

## NOTE ##
# This tests spawn an underlying server, it might be better not run
# unattended. Some also require a miner, we might not have it handy.
pytestmark = pytest.mark.manual



def getminer() -> None | tuple[str, int]:
    if not (minerd := os.getenv("LUXOS_TEST_MINER")):
        return None
    host, port = minerd.split(":")
    return host.strip(), int(port)


def test_validate_message():
    pytest.raises(exceptions.MinerCommandMalformedMessageError, aapi.validate_message, "a", 0, {})
    host, port = "a", 0

    assert aapi.validate_message(host, port, {"STATUS": 1, "id": 2})

    pytest.raises(
        exceptions.MinerCommandMalformedMessageError,
        aapi.validate_message,
        host, port,
        {
            "STATUS": 1,
            "id": 2,
        },
        "wooow",
    )

    assert aapi.validate_message(host, port, {"STATUS": 1, "id": 2, "wooow": [1, 2]}, "wooow")

    with pytest.raises(exceptions.MinerCommandMalformedMessageError) as excinfo:
        aapi.validate_message(host, port,
            {"STATUS": 1, "id": 2, "wooow": [1, 2]}, "wooow", minfields=9
        )
    assert excinfo.value.args[2] == "found 2 fields for wooow invalid: 2 <= 9"

    with pytest.raises(exceptions.MinerCommandMalformedMessageError) as excinfo:
        aapi.validate_message(host, port,
            {"STATUS": 1, "id": 2, "wooow": [1, 2]}, "wooow", maxfields=1
        )
    assert excinfo.value.args[2] == "found 2 fields for wooow invalid: 2 >= 1"

    with pytest.raises(exceptions.MinerCommandMalformedMessageError) as excinfo:
        aapi.validate_message(host, port,
            {"STATUS": 1, "id": 2, "wooow": [1, 2]}, "wooow", minfields=9, maxfields=10
        )
    assert excinfo.value.args[2] == "found 2 fields for wooow invalid: 2 <= 9"

    assert aapi.validate_message(host, port,
        {"STATUS": 1, "id": 2, "wooow": [1, 2]}, "wooow", minfields=2, maxfields=10
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
