"""Compile developer-owned UI XML into an internal module for the frozen EXE."""

import argparse
from pathlib import Path
import ast
from pprint import pformat

from spt_desktop.ui_text_xml import CATALOG_FILE, load_strings


OUTPUT_FILE = Path(__file__).resolve().parent.parent / 'spt_desktop' / '_ui_copy_generated.py'


def _literal_keys(node: ast.AST) -> set[str]:
    """Extract only constant UI IDs, including both sides of a ternary."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, ast.IfExp):
        return _literal_keys(node.body) | _literal_keys(node.orelse)
    return set()


def referenced_ui_keys(root: Path = CATALOG_FILE.parent.parent.parent) -> set[str]:
    """Read checked-in sources without importing or running GUI modules."""
    keys: set[str] = set()
    for relative in ('spt_desktop/app.py', 'spt_desktop/ui_views.py', 'spt_gui.py'):
        path = root / relative
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ('copy_text', 'format_text') and node.args):
                keys.update(_literal_keys(node.args[0]))
    return keys


def validate_referenced_ui_keys(strings: dict[str, str], root: Path) -> None:
    """Fail the build if any statically referenced copy key was removed."""
    missing = referenced_ui_keys(root) - strings.keys()
    if missing:
        raise ValueError('UI XML is missing referenced IDs: ' + ', '.join(sorted(missing)))


def generate(source: Path = CATALOG_FILE, target: Path = OUTPUT_FILE) -> Path:
    """Create Python constants from validated XML; no runtime XML is distributed."""
    strings = load_strings(source)
    validate_referenced_ui_keys(strings, Path(__file__).resolve().parent.parent)
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
