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
    'tests/test_workflow_contracts.py',
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


# Empirical, exact-node rebalancing for the two Windows shards.
# Baseline: successful main run 40449321039 on 2026-10-27; shard-0 was
# 1056.48s, shard-1 968.73s. These four shard-0 cases totalled ~42s.
# Moving ~42s between shards can reduce the ~88s gap without redistributing
# the other 6,375 collected tests or changing serial Windows coverage.
# Update only with measured successful-run evidence; unknown/renamed node IDs
# continue to use the stable hash partition.
_TIMED_SHARD_ONE = frozenset({
    'tests/test_corporate_template_layout.py::test_binding_stage_preserves_reference_geometry_and_approved_styles',
    'tests/test_desktop_dialog_layout.py::test_selection_reflow_preserves_data_and_owned_resources',
    'tests/test_native_panel_readiness.py::test_native_observer_retries_stale_post_click_binding[PPh Pasal 21/26]',
    'tests/test_masa_json_observer.py::test_all_masa_tabs_bind_real_requests_without_reading_tax_values[direct-PPN]',
})


def shard_for(nodeid, count):
    # SHA-256 memberi partisi yang sama di setiap runner; hash() bawaan Python
    # dapat berbeda antarproses dan membuat tes terlewat atau dijalankan ganda.
    # Hanya profil tepat 2-shard yang menerima pengecualian berdasarkan timing.
    if count == 2 and nodeid in _TIMED_SHARD_ONE:
        return 1
    digest = hashlib.sha256(nodeid.encode('utf-8')).digest()
    return int.from_bytes(digest[:8], 'big') % count


def pytest_addoption(parser):
    group = parser.getgroup('CI workload routing')
    group.addoption('--ci-workload', choices=('all', 'portable', 'windows'), default='all')
    group.addoption('--ci-manifest', help='Write synthetic node IDs and runner metadata.')
    group.addoption('--ci-benchmark', action='store_true',
                    help='Measure a separate full-suite benchmark without changing production.')
    group.addoption('--ci-shard', choices=('0/2', '1/2'),
                    help='Run one of two Windows shards with an evidence manifest.')


class _OutcomeRecorder:
    """Retain terminal statuses only, never assertion text or skip reasons."""

    def __init__(self, config):
        self.config = config

    def pytest_runtest_logreport(self, report):
        outcomes = self.config._ci_outcomes
        status = report.outcome
        if hasattr(report, 'wasxfail'):
            status = 'xfailed' if report.skipped else 'xpassed'
        # Lists deliberately preserve duplicate reports. A rerun or duplicate
        # call must not silently replace an earlier skipped or failed phase.
        outcomes.setdefault(report.nodeid, {}).setdefault(report.when, []).append(status)


def pytest_configure(config):
    if config.getoption('--ci-manifest'):
        config._ci_outcomes = {}
        config.pluginmanager.register(_OutcomeRecorder(config), 'ci-terminal-outcomes')


def pytest_sessionstart(session):
    config = session.config
    benchmark, shard = config.getoption('--ci-benchmark'), config.getoption('--ci-shard')
    if benchmark or shard:
        if config.getoption('--ci-workload') != 'windows' or not config.getoption('--ci-manifest'):
            from pytest import UsageError
            raise UsageError('Benchmark or sharding requires Windows workload and an evidence manifest.')
    if config.getoption('--ci-manifest'):
        config._ci_started = time.monotonic()
        config._ci_setup_seconds = None
        # Setup melintasi interpreter dengan clock monotonik Windows yang bisa
        # berbeda; hanya durasi sesi pytest memakai satu clock monotonik.
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
    # Simpan koleksi penuh sebelum filter agar agregator dapat mendeteksi tes
    # yang hilang, bukan sekadar membandingkan jumlah tes yang kebetulan lulus.
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
    report['outcomes'] = dict(sorted(config._ci_outcomes.items()))
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def _checked_inventory(report, workload, target, python_version, commit, run_id, run_attempt):
    if not isinstance(report, dict):
        raise ValueError('Test evidence is not an object.')
    if any(not isinstance(value, str) or not value.strip() for value in (run_id, run_attempt)):
        raise ValueError('Expected workflow run and attempt are required.')
    # Bukti dari rerun/attempt lain tidak boleh dipakai untuk melengkapi shard
    # yang gagal atau belum selesai pada eksekusi workflow ini.
    expected = {'workload': workload, 'platform': target,
                'python': python_version, 'commit': commit,
                'run_id': run_id, 'run_attempt': run_attempt}
    if any(report.get(key) != value for key, value in expected.items()):
        raise ValueError('Test evidence does not match this runner, commit, Python, workload or run.')
    if type(report.get('exitstatus')) is not int or report['exitstatus'] != 0:
        raise ValueError('Test evidence does not record a successful completed pytest session.')
    for key in ('all', 'selected'):
        nodes = report.get(key)
        if (not isinstance(nodes, list)
                or any(not isinstance(node, str) or not node.strip() for node in nodes)):
            raise ValueError('Test inventory is absent or malformed.')
        if len(nodes) != len(set(nodes)):
            raise ValueError('Test inventory contains duplicate test IDs.')
    if not report['all']:
        raise ValueError('The full test inventory is empty.')
    outcomes = report.get('outcomes')
    if not isinstance(outcomes, dict) or set(outcomes) != set(report['selected']):
        raise ValueError('Completed test outcomes do not match the selected inventory.')
    completed = {phase: ['passed'] for phase in ('setup', 'call', 'teardown')}
    if any(phases != completed for phases in outcomes.values()):
        raise ValueError('Every selected test must complete each phase once without skip or xfail.')
    return set(report['all']), set(report['selected'])


def check_windows_inventories(windows, python_version, commit, *, run_id, run_attempt):
    """Validate original serial or shard evidence and return its full collection."""
    reports = [windows] if isinstance(windows, dict) else windows
    if not isinstance(reports, list) or len(reports) not in (1, 2):
        raise ValueError('Expected one serial Windows report or exactly two shard reports.')
    all_nodes = None
    for index, report in enumerate(reports):
        full, selected = _checked_inventory(
            report, 'windows', 'win32', python_version, commit, run_id, run_attempt)
        if all_nodes is None:
            all_nodes = full
        elif full != all_nodes:
            raise ValueError('Windows collectors disagree about the complete test inventory.')
        if len(reports) == 1:
            if 'shard' in report or selected != full:
                raise ValueError('Serial Windows evidence must execute every collected test without sharding.')
            continue
        shard = report.get('shard')
        if (not isinstance(shard, dict)
                or type(shard.get('index')) is not int or type(shard.get('count')) is not int
                or shard != {'index': index, 'count': 2}):
            raise ValueError('Expected ordered Windows shard identities 0/2 and 1/2.')
        # Dua shard harus cocok dengan partisi identitas masing-masing; jumlah
        # total yang sama saja masih dapat menyembunyikan duplikasi dan celah.
        expected = {node for node in full if shard_for(node, 2) == index}
        if not expected or selected != expected:
            raise ValueError('Shard evidence does not match its exact Windows test partition.')
    return all_nodes


def check_inventories(portable, windows, python_version, commit, *, run_id, run_attempt):
    all_nodes, selected = _checked_inventory(
        portable, 'portable', 'linux', python_version, commit, run_id, run_attempt)
    if 'shard' in portable:
        raise ValueError('The portable workload must not be sharded.')
    windows_nodes = check_windows_inventories(
        windows, python_version, commit, run_id=run_id, run_attempt=run_attempt)
    if all_nodes != windows_nodes:
        raise ValueError('Portable and Windows collectors disagree about the full test inventory.')
    if selected != {node for node in all_nodes if workload_for(node) == 'portable'}:
        raise ValueError('Executed tests do not follow the reviewed workload routing.')
    return len(all_nodes)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Verify full Windows coverage and the extra Linux subset.')
    parser.add_argument('portable', type=Path)
    parser.add_argument('windows', type=Path, nargs='+')
    parser.add_argument('--python-version', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--run-attempt', required=True)
    args = parser.parse_args(argv)
    count = check_inventories(json.loads(args.portable.read_text(encoding='utf-8')),
                              [json.loads(path.read_text(encoding='utf-8')) for path in args.windows],
                              args.python_version, args.commit,
                              run_id=args.run_id, run_attempt=args.run_attempt)
    print(f'Verified full Windows inventory and matching Linux subset: {count} tests.')


if __name__ == '__main__':
    main()
