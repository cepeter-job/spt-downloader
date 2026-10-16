"""Summarize synthetic pytest evidence without copying assertion values or logs."""
import argparse
import html
import json
import math
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET


def _seconds(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Measured seconds must be numeric.')
    if not math.isfinite(value) or value < 0:
        raise ValueError('Measured seconds must be finite and non-negative.')
    return float(value)


def summarize(inventory, junit):
    """Missing evidence stays unknown; a diagnostic report never substitutes for a gate."""
    inventory = inventory or {}
    data = {key: inventory.get(key) for key in (
        'workload', 'python', 'commit', 'run_id', 'run_attempt', 'exitstatus',
        'cache_hit', 'python_cache_hit',
    )}
    data.update(
        setup_seconds=_seconds(inventory.get('setup_seconds')),
        pytest_seconds=_seconds(inventory.get('elapsed_seconds')),
        results=None, slowest=[],
    )
    if junit is None:
        return data
    root = ET.fromstring(junit)
    suites = [root] if root.tag == 'testsuite' else root.findall('testsuite')
    if not suites:
        raise ValueError('JUnit contains no test suite.')
    counts = {key: sum(int(suite.get(key, '0')) for suite in suites)
              for key in ('tests', 'failures', 'errors', 'skipped')}
    counts['passed'] = counts['tests'] - sum(counts[key] for key in ('failures', 'errors', 'skipped'))
    if any(value < 0 for value in counts.values()):
        raise ValueError('JUnit outcome counts are inconsistent.')
    data['results'] = counts
    # Only synthetic test identities and durations leave the JUnit document.
    timings = [
        {'test': f"{case.get('classname', '')}::{case.get('name', '')}",
         'seconds': _seconds(float(case.get('time', '0')))}
        for case in root.iter('testcase')
    ]
    data['slowest'] = sorted(timings, key=lambda item: item['seconds'], reverse=True)[:10]
    return data


def summary_text(data):
    def seconds(value):
        return 'unavailable' if value is None else f'{value:.2f}s'

    exitstatus = data.get('exitstatus')
    counts = data.get('results')
    lines = [
        '## Synthetic test measurements', '',
        f"- Pytest exit status: **{exitstatus if exitstatus is not None else 'unavailable'}**",
        f"- Setup after checkout: **{seconds(data.get('setup_seconds'))}**",
        f"- Pytest session: **{seconds(data.get('pytest_seconds'))}**",
        f"- uv cache hit: {data.get('cache_hit') or 'unavailable'}; "
        f"Python cache hit: {data.get('python_cache_hit') or 'unavailable'}",
    ]
    if counts is None:
        lines.append('- Test outcomes: unavailable; inspect the failed test/collection step.')
    else:
        lines.append('- JUnit outcomes: ' + ', '.join(f'{key}={value}' for key, value in counts.items()))
    lines.extend(['', 'Timing excludes runner queue, checkout, packaging and provenance. '
                  'Missing measurements do not imply success. Assertions and captured logs '
                  'are not copied into this summary.', ''])
    if data['slowest']:
        lines.extend(['| Slowest synthetic tests | Seconds |', '| --- | ---: |'])
        for item in data['slowest']:
            label = html.escape(item['test']).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ')
            lines.append(f"| {label} | {item['seconds']:.2f} |")
        lines.append('')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('start', 'report'))
    parser.add_argument('--directory', type=Path)
    args = parser.parse_args(argv)
    if args.command == 'start':
        with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as output:
            output.write(f'CI_SETUP_STARTED={time.monotonic()}\n')
        return
    directory = args.directory or Path(os.environ['RUNNER_TEMP'])
    inventory, junit = directory / 'test-inventory.json', directory / 'test-results.xml'
    data = summarize(
        json.loads(inventory.read_text(encoding='utf-8')) if inventory.is_file() else None,
        junit.read_text(encoding='utf-8') if junit.is_file() else None,
    )
    (directory / 'test-measurements.json').write_text(
        json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    text = summary_text(data)
    print(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as output:
            output.write(text)


if __name__ == '__main__':
    main()
