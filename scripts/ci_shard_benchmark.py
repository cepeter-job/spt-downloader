"""Compare complete Windows pytest evidence from one serial and two shard runs."""
import argparse
import json
import math
from pathlib import Path

from scripts.ci_tests import shard_for


def _nodes(report, key):
    value = report.get(key)
    if (not isinstance(value, list) or not value
            or any(not isinstance(node, str) or not node for node in value)
            or len(value) != len(set(value))):
        raise ValueError(f'Benchmark {key} collection is empty or malformed.')
    return set(value)


def _seconds(report):
    value = report.get('elapsed_seconds')
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Benchmark elapsed time is missing or invalid.')
    if not math.isfinite(value) or value <= 0:
        raise ValueError('Benchmark elapsed time is not positive and finite.')
    return float(value)


def verify(baseline, shards, python_version, commit):
    """Fail closed unless both successful shard inventories exactly partition baseline."""
    if not isinstance(baseline, dict) or not isinstance(shards, list) or len(shards) != 2:
        raise ValueError('Expected one baseline and exactly two shard reports.')

    full_nodes = _nodes(baseline, 'all')
    serial_nodes = _nodes(baseline, 'selected')
    if serial_nodes != full_nodes or 'shard' in baseline:
        raise ValueError('Baseline must execute every collected Windows test without sharding.')

    durations = []
    for index, report in enumerate([baseline, *shards]):
        if not isinstance(report, dict):
            raise ValueError('Benchmark evidence is not an object.')
        expected = {
            'workload': 'windows', 'platform': 'win32',
            'python': python_version, 'commit': commit, 'exitstatus': 0,
        }
        if any(report.get(field) != value for field, value in expected.items()):
            raise ValueError('Benchmark evidence has a mismatched runner, version, commit or exit status.')
        if _nodes(report, 'all') != full_nodes:
            raise ValueError('Windows collectors disagree about the complete test inventory.')
        durations.append(_seconds(report))
        if index == 0:
            continue
        if report.get('shard') != {'index': index - 1, 'count': 2}:
            raise ValueError('Benchmark shard identity is missing or incorrect.')
        expected_nodes = {node for node in full_nodes if shard_for(node, 2) == index - 1}
        if not expected_nodes or _nodes(report, 'selected') != expected_nodes:
            raise ValueError('Shard evidence omits or duplicates Windows tests.')

    return {
        'total_tests': len(full_nodes),
        'shard_counts': [len(shard['selected']) for shard in shards],
        'serial_seconds': durations[0],
        'parallel_seconds': max(durations[1:]),
        'saved_seconds': durations[0] - max(durations[1:]),
    }


def summary_text(result):
    serial = result['serial_seconds']
    parallel = result['parallel_seconds']
    return (
        '## Windows 2-shard benchmark (non-production)\n\n'
        f"- Serial suite: **{serial:.2f}s** ({result['total_tests']} tests)\n"
        f"- Parallel shards: **{parallel:.2f}s** critical path "
        f"({result['shard_counts'][0]} + {result['shard_counts'][1]} tests)\n"
        f"- Observed pytest-phase saving: **{result['saved_seconds']:.2f}s** "
        f"({100 * (serial - parallel) / serial:.1f}%)\n\n"
        'This compares pytest time on independently provisioned Windows runners; '
        'it excludes setup/queue, packaging and provenance. Production remains '
        'serial and retains its existing required gate and artifact checks.\n'
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('shard_zero', type=Path)
    parser.add_argument('shard_one', type=Path)
    parser.add_argument('--python-version', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--summary', type=Path)
    args = parser.parse_args(argv)

    baseline, shard_zero, shard_one = (
        json.loads(path.read_text(encoding='utf-8'))
        for path in (args.baseline, args.shard_zero, args.shard_one)
    )
    result = verify(baseline, [shard_zero, shard_one],
                    args.python_version, args.commit)
    text = summary_text(result)
    print(text)
    if args.summary:
        with args.summary.open('a', encoding='utf-8') as out:
            out.write(text)


if __name__ == '__main__':
    main()
