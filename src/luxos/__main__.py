# You can package this with:
# python -m zipapp src -m "luxos.__main__:main" -o luxos.pyz

def main():
    from json import dumps
    import luxos
    from luxos.api import COMMANDS
    print(luxos)
    print(dumps(COMMANDS, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()