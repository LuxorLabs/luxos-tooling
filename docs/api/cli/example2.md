# example 2

On top of simple1.py, a cli might want to define extra arguments and or options, this is the way is done:

```python
import asyncio
import argparse

import luxos.cli.v1 as cli

def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-x", type=int, default=0, help="set the x flag")

def process_args(args: argparse.Namespace) -> argparse.Namespace | None:
    args.x = 2 * args.x

@cli.cli(add_arguments, process_args)
async def main(args: argparse.Namespace):
    """a simple test script with a simple description"""
    print(f"Got for x='{args.x}'")

if __name__ == "__main__":
    asyncio.run(main())
```

Calling the script will result in:
```bash
$> python simple2.py -q
Got for x='0'
```

```bash
$> python simple2.py -q -x 12
Got for x='24'
```

The parser processing works in this way:
```
parser creation
  -> adds default arguments (-q|-v|-c, internal)
  -> can use the add_arguments callback to cli.cli to add more arguments
  -> parser.parse_args() return args: argparse.Namespace()
  -> process_args(args) process args
args then is finally passed down to main(args).  
```

> **NOTE** argparse makes the distintion between options and arguments
> even if both get added to the parser using the same parser.add_argument method.
> 
> Basically it boils down to:
>
> *if it is required to run the script, then it is an argument*
>     -> you can parser.add_argument("argument")
> 
> *if it is NOT required to run the script, then it is an option*
>     -> you can parser.add_argument("--option")


