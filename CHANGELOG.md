# LUXOS TOOLING CHANGELOG

- [LUXOS TOOLING CHANGELOG](#luxos-tooling-changelog)
  - [\[Unreleased\]](#unreleased)
  - [\[0.0.2\]](#0.0.2)

<!--
All notable changes to this project will be documented in this file.
Please, use the format:

## [Unreleased]

 - <module>: short description

-->
## [Unreleased]

 - ci: fix daily workflow, update sq token

## [0.2.5]

- added new commands to api.json

## [0.2.5]

- api: added hashboardopts, hashboardoptsset, ledset, minerstatus, and tunableswitch commands
- ips: splitip improvements
- misc: loadmod loads from web
- syncops: fix message handling for \0 terminated msgs
- cli.v1: mae cli output less verbose

## [0.2.4]

- adds --version flag to luxos.cli scripts
- luxos is a namespaced project
- version information is now from luxos.version module

## [0.2.2]

- major documentation refactor
- better flags handling


## [0.1.0]

- cli: added many new flags, including --range and --db


## [0.0.9]

- asyncops: standardize module level variables TIMEOUT/RETRIES/RETRIES_DELAY
- asyncops: re-raise timeouts with the correct exception MinerCommandTimeoutError
- cli: handle flags for rexec (TIMEOUT/RETRIES/RETRIES_DELAY)
- cli: new log format
- cli: better support for exceptions captured in cli.cli
- utils: launch uses a base LuxosLaunchError for all exceptions


## [0.0.8]

- added a new cli.flags module to handle range flags (eg. allowing 127.0.0.1-127.0.0.9 ranges)
- add luxos.utils.ip_ranges to list ip addresses from a text
- remove *pyz files
- update pyproject.toml with latest ruff settings and pplied ruff to the codebase


## [0.0.7]

- add to the cli.cli decorated function an 'attributes' attribute


## [0.0.6]

- support for misc.launch batched uperations
- fix timing report issue hor-1155

## [0.0.5]

- new cli support for epilog/description
- add new iter_ip_ranges function

## [0.0.2]

- beta-builder: automatically publish beta packages into pypi from main branch
- improve debug logging
- adds a new luxos.cli package
