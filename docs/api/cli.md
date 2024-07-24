# luxos.api.cli
```{toctree}
:hidden:
:maxdepth: 2

cli/example1.md
cli/example2.md
cli/example3.md
cli/example4.md
```

Luxos comes with a convenient cli interface generator, similar to
what [click](https://palletsprojects.com/p/click) provides, but simplified for 
easier usage. It uses [argparse](https://docs.python.org/3/library/argparse.html) so no external package is needed.

This is the simplest script:

```python
# script.py
#!/usr/bin/env python3
import logging
import luxos.cli.v1 as cli

log = logging.getLogger(__name__)

@cli.cli()
def main():
    log.debug("Hello debug")
    log.info("Hello info")
    log.warning("Hello warning")

if __name__ == "__main__"
    main()
```

This script takes `-v|--verbose` and `-q|--quiet` flags, controlling the logging
output.

## Starting

The best way to familiarize with it is to following simple examples:

**simple script**
One

**second**
- the simplest basic cli showing how to document the script and using the logging 👉 [simple1](cli/example1.md)
- extend your script and add custom arguments 👉 [simple2](cli/example2)
- using *magic* module-level variable to configure the scrip 👉 [simple3](cli/example3)
- the smallest complete script 👉 [simple4](cli/example4)
