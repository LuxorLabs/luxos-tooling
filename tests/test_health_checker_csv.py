from __future__ import annotations

import asyncio
import importlib
import sys
import types

import pytest

MISSING_NAMES = [
    "generate_ip_range",
    "add_session_id_parameter",
    "parameters_to_string",
    "check_res_structure",
    "get_str_field",
]


@pytest.fixture()
def health_checker(tmp_path, monkeypatch):
    # importing the module opens LuxOS-CLI.log in the current directory
    monkeypatch.chdir(tmp_path)
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        monkeypatch.setitem(sys.modules, "asyncpg", types.ModuleType("asyncpg"))
    # health_checker imports names luxos.scripts.luxos no longer defines
    import luxos.scripts.luxos as lx

    for name in MISSING_NAMES:
        if not hasattr(lx, name):
            monkeypatch.setattr(lx, name, lambda *a, **k: None, raising=False)
    monkeypatch.delitem(sys.modules, "luxos.scripts.health_checker", raising=False)
    module = importlib.import_module("luxos.scripts.health_checker")
    yield module
    for handler in module.LOGGING_CONFIG["handlers"]:
        handler.close()
    sys.modules.pop("luxos.scripts.health_checker", None)


@pytest.fixture()
def load(health_checker, tmp_path):
    def _load(text: str, encoding: str = "utf-8"):
        path = tmp_path / "miners.csv"
        path.write_bytes(text.encode(encoding))
        return health_checker.load_ip_list_from_csv(str(path))

    return _load


@pytest.mark.parametrize(
    "text, expected",
    [
        ("hostname,model\n10.0.0.1,S19\n10.0.0.2,S21\n", ["10.0.0.1", "10.0.0.2"]),
        (
            "hostname,model\r\n10.0.0.1,S19\r\n10.0.0.2,S21\r\n",
            ["10.0.0.1", "10.0.0.2"],
        ),
        (
            'hostname,note\n"10.0.0.1","a, b"\n"miner-2.lan",x\n',
            ["10.0.0.1", "miner-2.lan"],
        ),
        ("hostname\n10.0.0.1\n\n10.0.0.2\n", ["10.0.0.1", "10.0.0.2"]),
        ("\nhostname\n10.0.0.1\n", ["10.0.0.1"]),
        ("model,hostname\nS19,10.0.0.1\nS21\n", ["10.0.0.1"]),
        ("hostname\n 10.0.0.1 \n", [" 10.0.0.1 "]),
        ("hostname\n", []),
    ],
)
def test_reads_hostname_column(load, text, expected):
    assert load(text) == expected


def test_utf8_bom(load):
    assert load("hostname,model\n10.0.0.1,S19\n", encoding="utf-8-sig") == [
        "10.0.0.1"
    ]


def test_drops_values_pandas_reads_as_missing(load, health_checker):
    values = sorted(health_checker.CSV_NA_VALUES - {""})
    text = "hostname,model\n" + "".join(f"{v},S19\n" for v in values)
    text += ",S19\n10.0.0.1,S19\n"
    assert load(text) == ["10.0.0.1"]


def test_duplicate_hostname_column_first_wins(load):
    assert load("hostname,hostname\na,b\n,c\n") == ["a"]


def test_numeric_hostnames_stay_strings(load):
    assert load("hostname\n1\n2\n") == ["1", "2"]


def test_extra_fields_are_ignored(load):
    assert load("hostname\n10.0.0.1,extra\n10.0.0.2\n") == ["10.0.0.1", "10.0.0.2"]


def test_missing_hostname_column_exits(load):
    with pytest.raises(SystemExit):
        load("ip,model\n10.0.0.1,S19\n")


def test_missing_file_exits(health_checker, tmp_path):
    with pytest.raises(SystemExit):
        health_checker.load_ip_list_from_csv(str(tmp_path / "nope.csv"))


def test_complete_all_awaits_every_task(health_checker):
    done = []

    async def job(i):
        await asyncio.sleep(0.001 * (25 - i))
        done.append(i)

    async def run():
        await health_checker.complete_all([job(i) for i in range(25)], "test")
        await health_checker.complete_all([], "empty")

    asyncio.run(run())
    assert sorted(done) == list(range(25))
