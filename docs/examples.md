# Examples (API)

Luxos exposes an easy to use API, both in sync and async fashion. Here are some 
notable example how to use it, in an HOWTO style.

It is strongly suggested to follow this page as it shows all the details in order
of complexity.

## Quickstart
Before digging into the following examples please note:

:::{tip}
**is better to issues these commands in an `ipython` shell**
```shell
pip install ipython
```
:::

Because some functions like [luxos.utils.rexec](luxos.asyncops.rexec) are async, 
ipython helps instead of wrapping them in an `asyncio.run`.

:::{tip}
**all the command here assume you have imported the `luxos.utils` module**
```python
from luxos import utils
```
:::

In order to make life easier, we gather together all the most used functions
in one module (you can still access them separately).

:::{tip}
**validate the replies from a command**
```python
# the result of rexec is a dict (on success)
res = await utils.rexec(*address, "version")

# we validate the res dictionary, checking that it has a VERSION key, 
# and the result is 1 element only.
print(utils.validate(res, "VERSION", 1, 1))
```
:::

You can use the [luxos.utils.validate](luxos.asyncops.validate) to quickly validate 
the reply form a miner and extracting the relevant information.

## Examples

Below are some API usage examples, listed in order of complexity: they range from 
loading csv files with miners' addresses to run a function across multiple 
miners leveraging asyncio.

### load_ips_from_csv

The [luxos.utils.load_ips_from_csv](luxos.ips.load_ips_from_csv) function
loads ip or addresses (including ports) from a csv file.
It also handles ranges of addresses (eg. start-stop) so you can
describe sparse networks.

This is an example of csv file (eg. **foobar.csv**):
```text
# comment (or empty lines) will be ignored
127.0.0.1 # a single address
127.0.0.2-127.0.0.10 # a range of addresses

# you can specify a port
127.0.0.11:9999
127.0.0.12-127.0.0.20:8888
```

You can load the addresses from it using:
```python
from luxos import utils
addresses = utils.load_ips_from_csv("foobar.csv")
```

### rexec / validate

The [luxos.utils.rexec](luxos.asyncops.rexec) function is the core of the
script <-> miner application: it sends commands and receives answer back from a miner.

This will get a miner [version](https://docs.luxor.tech/firmware/api/cgminer/version):
```python
host, port = ("127.0.0.1", 4028)

# the result of rexec is a dict (on success)
res = await utils.rexec(host, port, "version")

# we validate the res dictionary, checking that it has a VERSION key, 
# and the result is 1 element only.
print(utils.validate(res, "VERSION", 1, 1)["LUXminer"])
```

The validate takes care of validate the message (eg. ensuring the presense of the `STATUS` and `id` fields) 
and the miner didn't reply with an error. Moreover it makes sure the 
**VERSION** key is present and there's only once result in the miner's reply 
(for more details see [luxos.utils.validate](luxos.asyncops.validate)).

[luxos.utils.validate](luxos.asyncops.validate) can handle list results like in:
```python
res = await utils.rexec(host, port, "devdetails")
print(utils.validate(res, "DEVTAILS", 1, None))
```

Using the 1..None range meanss the validation will 
raise an MinerMessageInvalidError if there aren't boards (lower limit is set to `1`).

### parameters handling

[luxos.utils.rexec](luxos.asyncops.rexec) function handles the parameters sent to
the miner, wrapping the arguments in a proper message. It is also smart in a way that
handles:
- parameter encoding
- loging/logoff process (for commands requiring it)
- timeout
- retry and retry delays between retry


This will retrieve the ATM state first:
```python
res = await utils.rexec(host, port, "atm")
atm = utils.validate(res, "ATM", 1, 1)["Enabled"]
```

Then it flips the atm status (enabled <-> disabled):
```python
await utils.rexec(host, port, "atmset", parameters={"enabled": not atm})
```

And it restores back:
```python
await utils.rexec(host, port, "atmset", parameters={"enabled": atm})
```
