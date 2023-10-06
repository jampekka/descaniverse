#!/usr/bin/env python3

import descaniverse
from pathlib import Path
import defopt
import sys
import json
from typing import Union, TextIO, Optional

class FakePath:
    def __init__(self, file, name):
        self.file = file
        self.name = name

    def __str__(self):
        return self.name

    def open(self, *args, **kwargs):
        return self.file

def scaniverse_to_json(scaniverse_dir: Path, output: Path = FakePath(sys.stdout, "STDOUT")):
    """Converts Scaniverse metadata as-is to JSON"""
    scan = descaniverse.ScaniverseRawData(scaniverse_dir)
    if output is None:
        output = sys.stdout
    else:
        output = output.open('w')
    json.dump(scan.as_dicts(), output, indent=2)
    output.write('\n')

if __name__ == '__main__':
    import defopt
    defopt.run(scaniverse_to_json, cli_options='has_default')
