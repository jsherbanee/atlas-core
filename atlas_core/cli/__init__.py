"""Command line interface package for Atlas Core."""

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    from atlas_core.cli.__main__ import main as cli_main

    return cli_main(list(argv) if argv is not None else None)
