# `luxos-run` command line tool

The `luxos-run` is an alternative to `luxos` command line script, 
allowing to run as **scriptlet** (a small python script) targeting miners:
a scriptlet usually can contain some logic and or longer commands sequences.

**hello-world.py** scriplet:
```python
from luxos import asyncops

async def main(host: str, port: int):
    # async sending to the miner the version command
    res = await asyncops.rexec(host, port, "version")

    # validate will check the message is correct and return the result
    version = asyncops.validate(res, "VERSION", 1, 1)
    return {"address": f"{host}:{port}", "miner": version["LUXminer"]}
```

Running the `luxos-run` will execute the scriptlet aggregating the results in
a dictionary with key set to the miner address:
```bash
luxos-run --range @miners.csv --quiet --json hello-world.py
{
  "127.0.0.1:4028": {
    "address": "127.0.0.1:4028",
    "version": "2021.1.12.202305-nnnn"
  }
}
````
