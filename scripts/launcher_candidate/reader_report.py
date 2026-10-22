"""Validate retained reader evidence bytes without promoting blocked observations."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.launcher_candidate.inventory import validate_reader_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    args = parser.parse_args()
    root = args.directory.resolve(strict=True)
    report = json.loads((root / 'report.json').read_text(encoding='utf-8-sig'))
    inventory = json.loads(args.inventory.read_text(encoding='utf-8-sig'))
    validate_reader_report(report, inventory)
    for evidence in report['evidence'].values():
        path = root / evidence['path']
        if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root):
            raise ValueError('unowned evidence path')
        if hashlib.sha256(path.read_bytes()).hexdigest() != evidence['sha256']:
            raise ValueError('evidence byte mismatch')
    cleanup = json.loads((root / 'cleanup.json').read_text(encoding='utf-8-sig'))
    if cleanup != {'host_exited': True, 'reader_exited': True}:
        raise ValueError('owned cleanup incomplete')
    owned = json.loads((root / 'owned-tree.json').read_text(encoding='utf-8'))
    if owned.get('contained_before_resume') is not True or owned.get('cleanup_complete') is not True:
        raise ValueError('reader descendant cleanup incomplete')
    print(json.dumps({'reader': report['reader'], 'mode': report['mode'],
                      'activation_timing': report['activation_timing'], 'outcomes': report['outcomes']}))


if __name__ == '__main__':
    main()
