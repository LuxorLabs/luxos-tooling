# same as luxor-firmware/integration-tests/utils/luxminer.py
from __future__ import annotations

import contextlib
import datetime
import logging
import re
from typing import Any, Literal, overload

import dateutil.parser

from luxos import asyncops


def getlog(host: str, port: int) -> logging.Logger:
    return logging.getLogger(f"script.{host}:{port}")


def camel_to_snake_case(txt: str) -> str:
    """convert AVariableCamelCased -> a_variable_camel_cased"""
    pattern = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
    return pattern.sub("_", txt).lower()


# GENERAL


async def get_version(host: str, port: int) -> dict[str, Any]:
    res = await asyncops.rexec(host, port, "version")
    return asyncops.validate(res, "VERSION", 1, 1)


async def get_limits(host: str, port: int) -> dict[str, Any]:
    res = await asyncops.rexec(host, port, "limits")
    return asyncops.validate(res, "LIMITS", 1, 1)


async def get_config(host: str, port: int) -> dict[str, Any]:
    res = await asyncops.rexec(host, port, "config")
    return asyncops.validate(res, "CONFIG", 1, 1)


# ATM COMMANDS


async def get_atm(host: str, port: int) -> dict[str, Any]:
    res = await asyncops.rexec(host, port, "atm")
    return asyncops.validate(res, "ATM", 1, 1)


async def set_atm(host: str, port: int, parameters: dict[str, Any]) -> dict[str, Any]:
    new_parameters = {
        camel_to_snake_case(key): value for key, value in parameters.items()
    }
    res = await asyncops.rexec(host, port, "atmset", new_parameters)
    return asyncops.validate(res)


@contextlib.asynccontextmanager
async def with_atm(host: str, port: int, enabled: bool):
    """disable ATM and restore it afterward"""
    current = await get_atm(host, port)
    atm = current.copy()
    atm["Enabled"] = enabled
    if current["Enabled"] != enabled:
        parameters = {camel_to_snake_case(key): value for key, value in atm.items()}
        await asyncops.rexec(host, port, "atmset", parameters)
    try:
        yield current
    finally:
        if current["Enabled"] != enabled:
            parameters = {
                camel_to_snake_case(key): value for key, value in current.items()
            }
            await asyncops.rexec(host, port, "atmset", parameters)


async def get_boards(host: str, port: int) -> dict[str, dict[str, Any]]:
    # boards/chips info
    res = await asyncops.rexec(host, port, "devdetails")
    boards = asyncops.validate(res, "DEVDETAILS", 1, None)
    result = {}
    for board in boards:
        bid = board["ID"]
        res = await asyncops.rexec(host, port, "healthchipget", bid)
        chips = asyncops.validate(res, "CHIPS", 1, None)
        result[bid] = {
            "board": board,
            "chips": chips,
        }
    return result


async def get_devs(host: str, port: int) -> dict[int, dict[str, Any]]:
    res = await asyncops.rexec(host, port, "devs")
    result = {}
    for dev in asyncops.validate(res, "DEVS", 1, None):
        if dev["ASC"] in result:
            raise RuntimeError(f"duplicate entry {dev=}")
        result[dev["ASC"]] = dev
    return result


# PROFILES COMMANDS


async def get_profiles(host: str, port: int) -> dict[str, Any]:
    res = await asyncops.rexec(host, port, "profiles")
    return {
        profile["Profile Name"]: profile
        for profile in asyncops.validate(res, "PROFILES", 0, None)
    }


async def set_profile(host: str, port: int, board: int, profile: str) -> dict[str, Any]:
    async with with_atm(host, port, enabled=False):
        res = await asyncops.rexec(host, port, "profileset", [board, profile])
        return asyncops.validate(res, "PROFILE", 1, 1)


async def get_autotuner(host: str, port: int) -> dict[str, Any]:
    res = await asyncops.rexec(host, port, "autotunerget")
    return asyncops.validate(res, "AUTOTUNER", 1, 1)


async def get_state(host: str, port: int) -> dict[str, dict[str, Any]]:
    result = {}

    result["config"] = await get_config(host, port)
    result["profiles"] = await get_profiles(host, port)
    result["version"] = await get_version(host, port)

    res = await asyncops.rexec(host, port, "groups")
    result["groups"] = asyncops.validate(res, "GROUPS", 0, None)

    res = await asyncops.rexec(host, port, "pools")
    result["pools"] = asyncops.validate(res, "POOLS", 0, None)

    result["atm"] = await get_atm(host, port)
    result["autotuner"] = await get_autotuner(host, port)

    return result


## LOG RELATED


class Log:
    def __init__(
        self, entries: list[tuple[datetime.datetime, str, str, list[str]]] | None = None
    ):
        self.entries = entries or []

    @staticmethod
    def parse(lines: list[str]) -> Log:
        header = re.compile(
            r"(?P<tstamp>\d{4}-\d{2}-\d{2}.?\d{2}:\d{2}:\d{2}[.]\d{6}.?)\s+"
            r"(?P<level>[^ ]+)\s+"
            r"+(?P<thread>ThreadId[(]\d+[)])\s+"
            r"(?P<name>\w+(::\w+)*:)\s+"
        )
        out = Log()
        block = None
        for line in lines:
            if match := header.search(line):
                if block is not None:
                    out.entries.append(block)
                block = (
                    dateutil.parser.parse(match.group("tstamp")),
                    match.group("level").strip(),
                    match.group("name").strip(),
                    [line[match.span()[1] :]],
                )
                continue
            if block:
                block[-1].append(line)
        out.entries.sort()
        return out


@overload
async def get_log(host: str, port: int, raw: Literal[True]) -> str: ...


@overload
async def get_log(host: str, port: int, raw: Literal[False]) -> Log: ...


@overload
async def get_log(host: str, port: int, raw: bool) -> str | Log: ...


async def get_log(host: str, port: int = 8080, raw: bool = False) -> str | Log:
    from httpx import AsyncClient

    async with AsyncClient() as client:
        res = await client.get(
            f"http://{host}:8080/log/download?file=current/luxminer.log"
        )
        if raw:
            return res.text
        return Log.parse(res.text.split("\n"))
