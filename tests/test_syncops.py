import random
from string import ascii_lowercase

import pytest

from luxos import exceptions, syncops

pytestmark = pytest.mark.manual


def test_miner_logon_logoff_cycle(miner_host_port):
    host, port = miner_host_port

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


def test_atm_flip(miner_host_port):
    host, port = miner_host_port

    def getatm():
        res = syncops.rexec(host, port, "atm")
        return syncops.validate_message(host, port, res, "ATM")[0]["Enabled"]

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


def test_miner_profile_sets(miner_host_port):
    host, port = miner_host_port

    # random profile name
    profile = f"test-{''.join(random.choices(ascii_lowercase, k=5))}"
    profiles = syncops.rexec(host, port, "profiles")["PROFILES"]
    # verify profile is not present
    assert profiles and profile not in {p["Profile Name"] for p in profiles}

    # # create a new profile
    # # TODO there's a bug
    # #  when ATM is running you shouldn't be able to create/delete
    # #  profiles, the following test should fail at the first try
    # # -> to pass this test, you need to disable ATM
    #
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
    found = {p["Profile Name"] for p in profiles2}
    expected = {p["Profile Name"] for p in profiles}
    assert found == expected
