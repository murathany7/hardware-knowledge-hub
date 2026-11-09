"""Create a local Hardware Knowledge Hub project."""
import argparse
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init"])
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.directory.exists():
        parser.error("Choose a directory that does not exist.")
    shutil.copytree(Path(__file__).parent / "template", args.directory)
    print(f"Open {args.directory} and run python3 hardware/knowledge/kb.py serve")
