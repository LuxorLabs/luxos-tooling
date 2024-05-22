"""various argparse `type` attributes"""

from __future__ import annotations

import argparse


def type_range(txt: str) -> list[tuple[str, int | None]]:
    from luxos.ips import iter_ip_ranges

    try:
        return list(iter_ip_ranges(txt))
    except RuntimeError as exc:
        raise argparse.ArgumentTypeError(f"conversion failed '{txt}': {exc.args[0]}")
    except Exception as exc:
        raise argparse.ArgumentTypeError(f"conversion failed for {txt}") from exc
