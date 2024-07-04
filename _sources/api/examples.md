# Examples / Tutorial

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

### load miners from a csv file
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

### get a miner version - rexec example

This will load a miner version:
```python
host, port = ("127.0.0.1", 4028)

# the result of rexec is a dict (on success)
res = await utils.rexec(host, port, "version")

# we validate the res dictionary, checking that it has a VERSION key, 
# and the result is 1 element only.
print(utils.validate(res, "VERSION", 1, 1)["LUXminer"])
```

The rexec is a function that sends out a command to a miner and returns (asyncrously)
a result (see [luxos.utils.rexec](luxos.asyncops.rexec)).

The validate makes sure the **VERSION** key is present and there's only once result
in the miner's reply (see [luxos.utils.validate](luxos.asyncops.validate)).


### get a miner boards information - list results

Please note the `validate` using the 1..None range: this means the validation will 
raise an MinerMessageInvalidError if there aren't boards and there's no upper limit
to how many boards are present.

```python
res = await utils.rexec(host, port, "devdetails")
print(utils.validate(res, "DEVTAILS", 1, None))
```

### flip the ATM - parameters handling
This will retrieve the ATM state first:
```python
res = await utils.rexec(host, port, "atm")
atm = utils.validate(res, "ATM", 1, 1)["Enabled"]
```

Then it flips the atm status (enabled <-> disabled):
```python
await utils.rexec(host, port, "atmset", parameters={"enabled": not atm})
```

And restore it back:
```python
await utils.rexec(host, port, "atmset", parameters={"enabled": atm})
```

[rexec](luxos.asyncops.rexec) is able to take care of the loging process and 
dispatch the parameters in the most appropriate way (eg. no need to cast).
