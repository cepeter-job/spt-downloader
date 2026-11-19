"""Compile developer-owned UI XML into an internal module for the frozen EXE."""

import argparse
from pathlib import Path
from pprint import pformat

from spt_desktop.ui_text_xml import CATALOG_FILE, load_strings


OUTPUT_FILE = Path(__file__).resolve().parent.parent / 'spt_desktop' / '_ui_copy_generated.py'


def generate(source: Path = CATALOG_FILE, target: Path = OUTPUT_FILE) -> Path:
    """Create Python constants from validated XML; no runtime XML is distributed."""
    strings = load_strings(source)
    module = ('"""Generated at build time from resources/ui/id-ID.xml. Do not edit."""\n'
              'STRINGS = ' + pformat(strings, width=100, sort_dicts=True) + '\n')
    destination = Path(target)
    destination.write_text(module, encoding='utf-8')
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=CATALOG_FILE)
    parser.add_argument('--output', type=Path, default=OUTPUT_FILE)
    args = parser.parse_args()
    generate(args.source, args.output)


if __name__ == '__main__':
    main()
