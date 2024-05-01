# LuxOS Tools Repository

[![PyPI version](https://img.shields.io/pypi/v/luxos.svg?color=blue)](https://pypi.org/project/luxos)
[![Python versions](https://img.shields.io/pypi/pyversions/luxos.svg)](https://pypi.org/project/luxos)
[![License - MIT](https://img.shields.io/badge/license-MIT-9400d3.svg)](https://spdx.org/licenses/)
[![Build](https://github.com/LuxorLabs/luxos-tooling/actions/workflows/push-main.yml/badge.svg)](https://github.com/LuxorLabs/luxos/actions/runs/0)
![PyPI - Downloads](https://img.shields.io/pypi/dm/luxos)
[![Mypy](https://img.shields.io/badge/types-Mypy-blue.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

This repository contains scripts we built to operate and troubleshoot miners running LuxOS.

This gather togheter tools, script and a library to handle miners supporting operations and maintenance.

## Installation

To install the latest and greatest version:
```bash
   $> pip install -U luxos
```

To install a beta (see [here](https://pypi.org/project/luxos/#history) for the complete list):
```bash
   $> pip install -U luxos==0.0.5b18
```

Finally you can install the latest bleeding edge code as:
```bash
   $> pip install git+https://github.com/LuxorLabs/luxos-tooling.git
```

If you're new to a python `venv`, there are generic instructions [venv](https://docs.python.org/3/library/venv.html).

## Verify

Once installed you can verify the version and the commit the code is from using:
```bash
   $> python -c "import luxos; print(luxos.__version__, luxos.__hash__)"
   0.0.5 08cc733ce8aedf406856c8ad9ccbe44e78917a37
```

## Help

See files under the docs/folder.


## Examples
This is a curated list of examples.

### The LuxOS API - luxos

This package offers a convenient way to interact with LuxOS through a command-line interface (CLI) or as Python packages for more advanced integrations.

**Usage (cli)**

This will reboot all miners in the `miner.csv` file list:
```bash
   $> luxos --ipfile miners.csv --cmd rebootdevice --timeout 2 --verbose
   (same as)
   $> python -m luxos --ipfile miners.csv --cmd rebootdevice --timeout 2 --verbose
```
> **NOTE** You can pass the `--async` flag for async operations (it should be faster if the number of miners is large).

**Usage (api)**

The same operation can be done using the internal api:

```python
   from luxos.api import (execute_command)
   
   execute_command("192.168.1.1", 4028, 2, "version", "", False)
```

There's an alternative (async) api:
```python
   import asyncio
   from luxos.utils import rexec
   
   # note the timeout/retry/retry_delay aren't needed
   asyncio.run(rexec(host="192.168.1.1", port=4028, cmd="version", parameters="", timeout=2., retry=1, retry_delay=3.))
```

## LuxOS HealthChecker - health_checker.py

The HealthChecker script is designed to continuously pull miner data from LuxOS, providing valuable insights into the health of your mining machines.

You can customize the HealthChecker params using the `config.yaml` file provided. 
To run the HealthChecker you can use `health-checker` if you installed using pip, or
the cli `python3 -m luxos.scripts.health_checker`.

---

Feel free to explore and customize these tools to suit your specific needs. 
If you encounter any issues or have suggestions for improvement, please open an issue or submit a pull request.

You can find LuxOS API documentation [here](https://docs.luxor.tech/firmware/api/intro).
