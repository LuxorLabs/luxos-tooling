import asyncio
import importlib
import json

import pytest

# health_checker depends on the luxos[extra] packages
for name in ["asyncpg", "pandas", "tqdm"]:
    pytest.importorskip(name)


@pytest.fixture()
def health_checker(tmp_path, monkeypatch):
    # importing the module opens LuxOS-CLI.log in the current directory
    monkeypatch.chdir(tmp_path)
    return importlib.import_module("luxos.scripts.health_checker")


def test_import(health_checker):
    # the health-checker console script entry point
    assert callable(health_checker.main)


def test_generate_ip_range(health_checker):
    assert health_checker.generate_ip_range("127.0.0.1", "127.0.0.1") == ["127.0.0.1"]
    assert health_checker.generate_ip_range("10.0.0.254", "10.0.1.1") == [
        "10.0.0.254",
        "10.0.0.255",
        "10.0.1.0",
        "10.0.1.1",
    ]
    assert health_checker.generate_ip_range("127.0.0.3", "127.0.0.1") == []


def test_protocol_helpers(health_checker):
    res = {"STATUS": [{"STATUS": "S"}], "id": 1, "SESSION": [{"SessionID": "abc"}]}
    assert health_checker.check_res_structure(res, "SESSION", 1, 1) is res
    with pytest.raises(ValueError):
        health_checker.check_res_structure(res, "VERSION", 1, 1)
    assert health_checker.get_str_field(res["SESSION"][0], "SessionID") == "abc"
    params = health_checker.add_session_id_parameter("abc", ["x", "y"])
    assert health_checker.parameters_to_string(params) == "abc,x,y"


@pytest.mark.asyncio
async def test_execute_command_with_logon(health_checker):
    """atmset needs a session: logon, run the command with the sid, logoff"""
    received = []

    async def handle(reader, writer):
        request = json.loads(await reader.readline())
        received.append(request)
        status = [{"STATUS": "S"}]
        if request["command"] == "logon":
            response = {"STATUS": status, "id": 1, "SESSION": [{"SessionID": "42"}]}
        else:
            response = {"STATUS": status, "id": 1}
        writer.write(json.dumps(response).encode() + b"\x00")
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with server:
        res = await health_checker.execute_command(
            "127.0.0.1", port, 2, "atmset", ["enabled=true"], False
        )

    assert res == {"STATUS": [{"STATUS": "S"}], "id": 1}
    assert received == [
        {"command": "logon"},
        {"command": "atmset", "parameter": "42,enabled=true"},
        {"command": "logoff", "parameter": "42"},
    ]
