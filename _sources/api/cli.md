# luxos.api.cli

Luxos comes with a convenient cli interface generator, similar to what [click](https://palletsprojects.com/p/click) provides,
but simplified for easier usage. It uses [argparse](https://docs.python.org/3/library/argparse.html) underneath, and this is the simplest usage:

```python
import luxos.cli.v1 as cli

@cli.cli()
def main():
    print("Hello")

if __name__ == "__main__"
    main()
```
!!! note
    The tool is in the module `luxos.cli.v1`, and the `v1` denotes the first iteration of it. In future there 
    might be more versions to accomodate different scenarios.

## What the cli package can do for you

In the `v1` version the cli provides some standard flags common to all script leveraging it. By default it provides:

* `-v|--verbose` and `-q|--quiet` flags to increase (decrease)  the logging verbosity level (see [example 1](cli/example1.md))
* `-c/--config` flag to point to a config file path (default to **config.yaml**, configurable as in [example 3](cli/example3.md))

In the design intentions the goal is to provide an easy and fast way to start writing a script, providing 
support for extension, using only the internal python standard library and generally being simple.

There are escape hatches to configure the cli to suit most use cases.

## Starting

The best way to familiarize with it is to following simple examples:

- the simplest basic cli showing how to document the script and using the logging 👉 [simple1](cli/example1.md)
- extend your script and add custom arguments 👉 [simple2](cli/example2)
- using *magic* module-level variable to configure the scrip 👉 [simple3](cli/example3)
- the smallest complete script 👉 [simple4](cli/example4)
