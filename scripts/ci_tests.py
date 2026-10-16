"""Jalankan subset Linux yang ditinjau dan seluruh pengujian regresi Windows."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time


# Hanya modul portable yang telah ditinjau masuk jalur Linux tambahan. Windows
# selalu menjalankan seluruh tes, termasuk cabang khusus OS di modul portable.
PORTABLE_FILES = frozenset({
    'tests/test_branch_cleanup.py',
    'tests/test_browser_safety.py',
    'tests/test_ci_artifacts.py',
    'tests/test_ci_python_cache.py',
    'tests/test_ci_routing.py',
    'tests/test_ci_sharding.py',
    'tests/test_dependency_locks.py',
    'tests/test_desktop_build.py',
    'tests/test_desktop_credentials.py',
    'tests/test_desktop_gui.py',
    'tests/test_desktop_lifecycle_audit.py',
    'tests/test_desktop_login_binding.py',
    'tests/test_desktop_login_check_transport.py',
    'tests/test_desktop_login_home.py',
    'tests/test_desktop_orchestration.py',
    'tests/test_desktop_output.py',
    'tests/test_desktop_runtime.py',
    'tests/test_desktop_worker.py',
    'tests/test_export_safety.py',
    'tests/test_exporter.py',
    'tests/test_output_safety.py',
    'tests/test_period_layout.py',
    'tests/test_split_output.py',
})
WINDOWS_TESTS = frozenset({
    'tests/test_ci_python_cache.py::test_real_windows_cold_install_and_tar_restore_reuse_the_exact_python',
    'tests/test_desktop_gui.py::test_simple_window_controls_and_partial_progress_are_real_tkinter',
})


def workload_for(nodeid):
    normalized = nodeid.replace('\\', '/')
    test = normalized.split('[', 1)[0]
    return ('portable' if normalized.split('::', 1)[0] in PORTABLE_FILES
            and test not in WINDOWS_TESTS else 'windows')


def shard_for(nodeid, count):
    # Assignment is stable across separately provisioned CI runners.
    digest = hashlib.sha256(nodeid.encode('utf-8')).digest()
    return int.from_bytes(digest[:8], 'big') % count


def pytest_addoption(parser):
    group = parser.getgroup('CI workload routing')
    group.addoption('--ci-workload', choices=('all', 'portable', 'windows'), default='all')
    group.addoption('--ci-manifest', help='Write synthetic node IDs and runner metadata.')
    group.addoption('--ci-benchmark', action='store_true',
                    help='Measure a separate full-suite benchmark without changing production.')
    group.addoption('--ci-shard', choices=('0/2', '1/2'),
                    help='Run one of two Windows benchmark shards.')


def pytest_sessionstart(session):
    config = session.config
    benchmark, shard = config.getoption('--ci-benchmark'), config.getoption('--ci-shard')
    if shard and not benchmark:
        from pytest import UsageError
        raise UsageError('--ci-shard requires --ci-benchmark.')
    if benchmark:
        if config.getoption('--ci-workload') != 'windows' or not config.getoption('--ci-manifest'):
            from pytest import UsageError
            raise UsageError('Benchmark requires Windows workload and an evidence manifest.')
    if config.getoption('--ci-manifest'):
        config._ci_started = time.monotonic()
        config._ci_setup_seconds = None
        # Bootstrap and managed Python can use different Windows monotonic clocks.
        # Only setup crosses interpreters; the pytest session stays monotonic.
        marker = os.environ.get('CI_SETUP_STARTED')
        if marker:
            from pytest import UsageError
            try:
                measured = time.time() - float(marker)
            except ValueError as exc:
                raise UsageError('CI setup marker is not numeric.') from exc
            if not math.isfinite(measured) or measured < 0:
                raise UsageError('CI setup timestamp is invalid or the wall clock moved backwards.')
            config._ci_setup_seconds = measured



def pytest_collection_modifyitems(config, items):
    workload = config.getoption('--ci-workload')
    all_nodes = sorted(item.nodeid for item in items)
    if workload == 'portable':
        selected, excluded = [], []
        for item in items:
            (selected if workload_for(item.nodeid) == workload else excluded).append(item)
        items[:] = selected
        config.hook.pytest_deselected(items=excluded)
    shard = config.getoption('--ci-shard')
    if shard:
        index = int(shard[0])
        selected, excluded = [], []
        for item in items:
            (selected if shard_for(item.nodeid, 2) == index else excluded).append(item)
        items[:] = selected
        config.hook.pytest_deselected(items=excluded)
    manifest = config.getoption('--ci-manifest')
    if manifest:
        cache_hit = os.environ.get('CI_UV_CACHE_HIT')
        python_cache_hit = os.environ.get('CI_PYTHON_CACHE_HIT')
        report = {
            'workload': workload, 'python': platform.python_version(),
            'platform': sys.platform, 'commit': os.environ.get('GITHUB_SHA', ''),
            'run_id': os.environ.get('GITHUB_RUN_ID', ''),
            'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT', ''),
            'setup_seconds': config._ci_setup_seconds,
            'setup_clock': 'unix-wall' if config._ci_setup_seconds is not None else None,
            'cache_hit': cache_hit if cache_hit in {'true', 'false'} else None,
            'python_cache_hit': python_cache_hit if python_cache_hit in {'true', 'false'} else None,
            'all': all_nodes, 'selected': sorted(item.nodeid for item in items),
        }
        if shard:
            report['shard'] = {'index': int(shard[0]), 'count': 2}
        Path(manifest).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def pytest_sessionfinish(session, exitstatus):
    config = session.config
    if not config.getoption('--ci-manifest'):
        return
    path = Path(config.getoption('--ci-manifest'))
    if not path.exists():
        return
    report = json.loads(path.read_text(encoding='utf-8'))
    report['exitstatus'] = int(exitstatus)
    report['elapsed_seconds'] = time.monotonic() - config._ci_started
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def check_inventories(portable, windows, python_version, commit):
    for report, workload, target in ((portable, 'portable', 'linux'), (windows, 'windows', 'win32')):
        expected = {'workload': workload, 'platform': target,
                    'python': python_version, 'commit': commit}
        if any(report.get(key) != value for key, value in expected.items()):
            raise ValueError('Test evidence does not match this commit, Python or workload.')
        for key in ('all', 'selected'):
            nodes = report.get(key)
            if not isinstance(nodes, list) or not all(isinstance(node, str) for node in nodes):
                raise ValueError('Test inventory is absent or malformed.')
            if len(nodes) != len(set(nodes)):
                raise ValueError('Test inventory contains duplicate test IDs.')
    all_nodes = set(portable['all'])
    first, second = set(portable['selected']), set(windows['selected'])
    if not all_nodes or all_nodes != set(windows['all']):
        raise ValueError('Portable and Windows collectors disagree about the full test inventory.')
    if second != all_nodes or not first <= second:
        raise ValueError('Windows did not execute the entire collected regression suite.')
    if first != {node for node in all_nodes if workload_for(node) == 'portable'}:
        raise ValueError('Executed tests do not follow the reviewed workload routing.')
    return len(all_nodes)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Verify full Windows coverage and the extra Linux subset.')
    parser.add_argument('portable', type=Path)
    parser.add_argument('windows', type=Path)
    parser.add_argument('--python-version', required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args(argv)
    count = check_inventories(json.loads(args.portable.read_text(encoding='utf-8')),
                              json.loads(args.windows.read_text(encoding='utf-8')),
                              args.python_version, args.commit)
    print(f'Verified full Windows inventory and matching Linux subset: {count} tests.')


if __name__ == '__main__':
    main()
