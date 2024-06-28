from string import ascii_lowercase

import pytest

from luxos import exceptions, syncops

pytestmark = pytest.mark.manual


def test__roundtrip(host, port):
    pytest.raises(ConnectionRefusedError, syncops._roundtrip, host, port + 1, "version")
    res = syncops._roundtrip(host, port, "version")
    assert res.startswith("STATUS=S")


def test_roundtrip(host, port):
    pytest.raises(
        exceptions.MinerCommandTimeoutError,
        syncops.roundtrip,
        host,
        port + 1,
        "version",
        retry=2,
    )

    res = syncops.roundtrip(host, port, "version", asjson=False)
    assert res.startswith("STATUS=S")


def test_miner_logon_logoff_cycle(miner_host_port):
    host, port = miner_host_port

    res = syncops.roundtrip(host, port, "kill", asjson=False)
    assert res.startswith("STATUS=S")

    sid = None
    try:
        sid = syncops.logon(host, port)
    except exceptions.MinerCommandSessionAlreadyActive as e:
        raise RuntimeError("a session is already active on {host}:{port}") from e
    finally:
        if sid:
            syncops.logoff(host, port, sid)


def test_miner_double_logon_cycle(miner_host_port):
    host, port = miner_host_port

    res = syncops.roundtrip(host, port, "kill", asjson=False)
    assert res.startswith("STATUS=S")

    sid = syncops.logon(host, port)
    try:
        with pytest.raises(exceptions.MinerCommandSessionAlreadyActive) as excinfo:
            syncops.logon(host, port)
        assert excinfo.value.args[0] == f"session active for {host}:{port}"
    except Exception:
        pass
    finally:
        if sid:
            syncops.logoff(host, port, sid)


def test_miner_version(miner_host_port):
    host, port = miner_host_port

    res = syncops.rexec(host, port, "version")
    assert "VERSION" in res
    assert len(res["VERSION"]) == 1
    assert "API" in res["VERSION"][0]


def test_miner_profile_sets(miner_host_port):
    from random import choices

    # random profile name
    profile = f"test-{''.join(choices(ascii_lowercase, k=5))}"

    # get the initial profile list
    host, port = miner_host_port
    profiles = (syncops.rexec(host, port, "profiles"))["PROFILES"]
    assert profiles and profile not in {p["Profile Name"] for p in profiles}

    # create a new profile
    # TODO there's a bug
    #  when ATM is running you shouldn't be able to create/delete
    #  profiles, the following test should fail at the first try
    # -> to pass this test, you need to disable ATM

    params = f"{profile},{profiles[0]['Frequency']},{profiles[0]['Voltage']}"
    syncops.rexec(host, port, "profilenew", params)

    try:
        profiles1 = (syncops.rexec(host, port, "profiles"))["PROFILES"]
        assert profile in {p["Profile Name"] for p in profiles1}
    finally:
        with syncops.with_atm(host, port, False):
            syncops.rexec(host, port, "profilerem", profile)

    # verify we restored the same profiles
    profiles2 = (syncops.rexec(host, port, "profiles"))["PROFILES"]
    expected = {p["Profile Name"] for p in profiles}
    found = {p["Profile Name"] for p in profiles2}
    assert found == expected


def test_roundtrip_timeout(miner_host_port):
    # host, port = miner
    """checks roundrtip sends and receive a message (1-listener)"""

    # miner doesn't exist
    host, port = "127.0.0.99", 12345
    try:
        syncops.rexec(host, port, "hello", timeout=0.5)
        assert False, "didn't raise"
    except exceptions.MinerCommandTimeoutError as exc:
        exception = exc
    assert isinstance(exception, TimeoutError)
    assert isinstance(exception, exceptions.MinerConnectionError)
    assert isinstance(exception, exceptions.LuxosBaseException)
    text = f"<{host}:{port}>: MinerCommandTimeoutError, TimeoutError("
    assert str(exception)[: len(text)] == text

    # not miner on a wrong port
    host, port = miner_host_port
    port = 22
    exception = None
    try:
        syncops.rexec(host, port, "hello", timeout=0.5)
        assert False, "didn't raise"
    except exceptions.MinerCommandTimeoutError as exc:
        exception = exc
    assert isinstance(exception, TimeoutError)
    assert isinstance(exception, exceptions.MinerConnectionError)
    assert isinstance(exception, exceptions.LuxosBaseException)
    texts = [
        f"<{host}:{port}>: MinerCommandTimeoutError, ConnectionRe",
        f"<{host}:{port}>: MinerCommandTimeoutError, TimeoutError",
    ]
    assert str(exception)[: len(texts[0])] in texts


def test_atm_flip(miner_host_port):
    host, port = miner_host_port

    def getatm():
        res = syncops.rexec(host, port, "atm")
        return syncops.validate_message(host, port, res, "ATM")["ATM"][0]["Enabled"]

    # current status
    status = getatm()
    assert status in {True, False}

    # check we can set the atm to the same status
    syncops.rexec(host, port, "atmset", {"enabled": status})
    assert status == getatm()

    syncops.rexec(host, port, "atmset", {"enabled": not status})
    assert status != getatm()

    syncops.rexec(host, port, "atmset", {"enabled": not getatm()})
    assert status == getatm()
