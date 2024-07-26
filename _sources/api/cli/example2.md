# basic usage (flags)
[download](_static/simple2.py)

You can add new flags to a script, and processing the values to parse them.

```python
...

import luxos.cli.v1 as cli

# here only for display, as it is the default
CONFIGPATH = "config.yaml"

def add_arguments(
    parser: cli.ArgumentParser,
):
    parser.add_argument("-x", type=int, dest="mult", default=1, help="set the x flag")
    parser.add_argument("number", type=int)

    parser.add_argument("--time", type=cli.flags.type_hhmm)
    cli.flags.add_arguments_config(parser)

def process_args(args: argparse.Namespace) -> argparse.Namespace | None:
    # we double anything we receive from user
    args.number *= args.mult

@cli.cli(add_arguments, process_args)
async def main(args: argparse.Namespace):
    print(f"the args.mult is args.mult={args.mult}")
    print(f"the final result is args.number={args.number}")
    print(f"args.config={args.config}")

if __name__ == "__main__":
    asyncio.run(main())

```

:::{note}
See [luxos.cli.flags](luxos.cli.flags) for a complete list.
:::

The parser processing works in this way:
```
parser creation
  -> adds default arguments (-q|-v|-c, internal)
  -> add_arguments(parser) callback to cli.cli is called to add more arguments
  -> parser.parse_args() return args: argparse.Namespace()
  -> process_args(args) callback to cli.cli is called to process args
args then is finally passed down to main(args).  
```


## examples

Calling the script will result in:
```bash
python simple2.py -q 99
the args.mult is args.mult=1
the final result is args.number=99
args.config=/Users/antonio/Projects/LuxorLabs/luxos-tooling/config.yaml
```

```bash
python simple2.py -q 99 -x 2
the args.mult is args.mult=2
the final result is args.number=198
args.config=/Users/antonio/Projects/LuxorLabs/luxos-tooling/config.yaml
```



