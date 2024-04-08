# LuxOS Tools Repository

This repository contains scripts we built to operate and troubleshoot miners running LuxOS.

## Install

There are few ways to install the luxos package:

1. Using pip (suggested for end-users):
   ```shell
   pip install luxos
   pip install git+https://github.com/LuxorLabs/luxos-tooling.git 
   ```
   Using pip gives you access to the cli commands `luxos` and `health-checker` as well
   the ability to import in python the `import luxos.api` api for luxos.

2. A single drop in file (for support):
   ```shell
   curl -LO https://github.com/LuxorLabs/luxos-tooling/raw/luxos.pyz
   ```
   These are two standalone [zipapp](https://docs.python.org/3/library/zipapp.html) files, you can use
   from the command line as `python luxos.pyz`, no dependencies beside a recent-*ish* python
   version (eg. >= 3.10)

3. From the [github](https://github.com/LuxorLabs/luxos-tooling) source checkout (for devs):
   ```shell
   python -m venv venv 
   source venv/bin/activate # for Windows: .\myenv\Scripts\activate)

   pip install -r tests/requirements.txt
   
   export PYTHONPATH=$(pwd)/src # for Windows: SET PYTHONPATH=%CD%\src
   (or)
   pip install -e .
   ```

## LuxOS API Wrapper - luxos

This tool offers a convenient way to interact with LuxOS through a command-line interface (CLI) or as Python packages for more advanced integrations.

**CLI Usage**

The luxos.py script serves as a versatile LuxOS API wrapper, allowing users to interact with LuxOS features directly from the command line. Below are some basic examples:

```bash
python3 -m luxos --ipfile miners.csv --cmd rebootdevice --timeout 2
python3 -m luxos --range_start 192.168.1.0 --range_end 192.168.1.255 --cmd rebootdevice --verbose True
```

> **NOTE** Please don't forget to set the PYTHONPATH.

**Library Usage**

If you prefer to integrate LuxOS functionality into your Python applications or scripts, luxos.py can also be used as a Python package. Here's a quick example:

```python
from luxos.api import (execute_command)

execute_command("192.168.1.1", 4028, 2, "rebootdevice", "", False)
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
