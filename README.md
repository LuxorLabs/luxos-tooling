# LuxOS Tools Repository

This repository contains scripts we built to operate and troubleshoot miners running LuxOS.

## LuxOS API Wrapper - luxos.py

This tool offers a convenient way to interact with LuxOS through a command-line interface (CLI) or as Python packages for more advanced integrations.

**CLI Usage**

The luxos.py script serves as a versatile LuxOS API wrapper, allowing users to interact with LuxOS features directly from the command line. Below are some basic examples:

```bash
python3 luxos.py --ipfile miners.csv --cmd rebootdevice --timeout 2
python3 luxos.py --range_start 192.168.1.0 --range_end 192.168.1.255 --cmd rebootdevice --verbose True
```

**Library Usage**

If you prefer to integrate LuxOS functionality into your Python applications or scripts, luxos.py can also be used as a Python package. Here's a quick example:

```python
from luxos import (execute_command)

execute_command('192.168.1.1', 4028, 2, 'rebootdevice', '', False)
```

## LuxOS HealthChecker - health_checker.py

The HealthChecker script is designed to continuously pull miner data from LuxOS, providing valuable insights into the health of your mining machines.

The HealthChecker uses poetry as a package manager, to install project dependencies run: `poetry install`. You can customize the HealthChecker params using the `config.yaml` file provided. Finally, to run the HealthChecker you can run: `poetry run python health_checker.py`.

---

Feel free to explore and customize these tools to suit your specific needs. If you encounter any issues or have suggestions for improvement, please open an issue or submit a pull request.

You can find LuxOS API documentation [here](https://docs.luxor.tech/firmware/api/intro).
