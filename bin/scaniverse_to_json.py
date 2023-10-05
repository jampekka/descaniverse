#!/usr/bin/env python3

import descaniverse
from pathlib import Path
from typing_extensions import Annotated
import typer
import sys
import json

ExistingDir = Annotated[Path, typer.Argument(
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True)
]

# TODO: Does typer allow for the scaniverse-argument to be set alternatively
#   as --scaniverse=<dir> (i.e. as option)? This would match the calling convention
#   of Python. And if it would be default, we could use kw-only and positional-only syntax
#   of Python function definitions instead of having Argument and Option as separate things.
def scaniverse_to_json(scaniverse: ExistingDir, output: Annotated[typer.FileTextWrite, typer.Argument()] = sys.stdout):
    """Converts scaniverse metadata as-is to JSON"""
    scan = descaniverse.ScaniverseRawData(scaniverse)
    json.dump(scan.as_dicts(), output, indent=2)

if __name__ == '__main__':
    import typer
    typer.run(scaniverse_to_json)
