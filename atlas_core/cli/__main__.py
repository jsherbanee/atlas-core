import argparse

from atlas_core import __version__


def main() -> None:
    parser = argparse.ArgumentParser(prog="atlas-core", description="Atlas Core CLI")
    parser.add_argument("--version", action="store_true", help="Print package version")
    args = parser.parse_args()

    if args.version:
        print(f"atlas-core {__version__}")
    else:
        print("Atlas Core CLI")
