"""Temporary, opt-in timing for synthetic browser fixtures on GitHub Windows runners."""
from collections import defaultdict
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter_ns

import pytest


def pytest_addoption(parser):
    group = parser.getgroup('Synthetic browser profiling')
    group.addoption('--browser-profile-output', required=True)
    group.addoption('--browser-profile-label', required=True)


def _git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


class Profile:
    def __init__(self, config):
        self.output = Path(config.getoption('--browser-profile-output'))
        self.nodeid = None
        self.phase = 'session'
        self.stack = []
        self.patches = []
        self.timings = defaultdict(lambda: {'count': 0, 'errors': 0,
                                           'inclusive_ns': 0, 'exclusive_ns': 0})
        self.browser_versions = set()
        self.reports = []
        self.selected = []
        self.started = perf_counter_ns()
        self.metadata = {
            'label': config.getoption('--browser-profile-label'),
            'commit': _git('rev-parse', 'HEAD'),
            'tree': _git('rev-parse', 'HEAD^{tree}'),
            'workflow_commit': os.environ.get('GITHUB_SHA', ''),
            'run_id': os.environ.get('GITHUB_RUN_ID', ''),
            'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT', ''),
            'python': platform.python_version(), 'platform': sys.platform,
            'implementation': sys.implementation.name,
            'gil_enabled': sys._is_gil_enabled(),
            'test_lock_sha256': hashlib.sha256(Path('locks/test.txt').read_bytes()).hexdigest(),
            'profiler_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }

    def wrap(self, owner, name, operation):
        original = getattr(owner, name)

        @wraps(original)
        def measured(*args, **kwargs):
            # Only duration and fixed categories are retained, never API arguments,
            # return values, exception text, URLs, or synthetic captured tax values.
            frame = {'start': perf_counter_ns(), 'children': 0}
            key = (self.nodeid, self.phase, operation, len(self.stack))
            self.stack.append(frame)
            succeeded = False
            try:
                result = original(*args, **kwargs)
                succeeded = True
                if operation == 'browser.launch':
                    try:
                        self.browser_versions.add(result.version)
                    except Exception:
                        # Metadata collection must not replace a successful API result.
                        self.browser_versions.add('unavailable')
                return result
            finally:
                elapsed = perf_counter_ns() - frame['start']
                self.stack.pop()
                if self.stack:
                    self.stack[-1]['children'] += elapsed
                record = self.timings[key]
                record['count'] += 1
                record['errors'] += int(not succeeded)
                record['inclusive_ns'] += elapsed
                record['exclusive_ns'] += elapsed - frame['children']

        setattr(owner, name, measured)
        self.patches.append((owner, name, original))

    def install(self):
        from playwright.sync_api import Browser, BrowserContext, BrowserType, Page, sync_playwright

        # The public context-manager object exposes its normal enter/exit methods;
        # no private Playwright implementation or product clock is replaced.
        manager = type(sync_playwright())
        for owner, name, operation in (
            (manager, '__enter__', 'playwright.start'),
            (manager, '__exit__', 'playwright.stop'),
            (BrowserType, 'launch', 'browser.launch'),
            (Browser, 'new_page', 'browser.new_page_with_context'),
            (Browser, 'new_context', 'browser.new_context'),
            (BrowserContext, 'new_page', 'context.new_page'),
            (BrowserContext, 'close', 'context.close'),
            (Browser, 'close', 'browser.close'),
            (Page, 'close', 'page.close'),
            (Page, 'wait_for_timeout', 'page.fixed_wait'),
            (Page, 'wait_for_function', 'page.condition_wait'),
        ):
            self.wrap(owner, name, operation)

    def restore(self):
        for owner, name, original in reversed(self.patches):
            setattr(owner, name, original)
        self.patches.clear()

    def write(self, exitstatus):
        timings = [dict(nodeid=nodeid, phase=phase, operation=operation, depth=depth, **values)
                   for (nodeid, phase, operation, depth), values in self.timings.items()]
        data = dict(self.metadata, selected_nodeids=self.selected,
                    browser_versions=sorted(self.browser_versions),
                    reports=self.reports, timings=timings,
                    elapsed_seconds=(perf_counter_ns() - self.started) / 1_000_000_000,
                    exitstatus=int(exitstatus))
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def pytest_sessionstart(session):
    if os.environ.get('GITHUB_ACTIONS') != 'true' or sys.platform != 'win32':
        raise pytest.UsageError('Browser profiling is restricted to GitHub Windows runners.')
    profile = Profile(session.config)
    session.config._browser_profile = profile
    profile.install()


def pytest_collection_finish(session):
    session.config._browser_profile.selected = sorted(item.nodeid for item in session.items)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    profile = item.config._browser_profile
    previous = profile.nodeid, profile.phase
    profile.nodeid, profile.phase = item.nodeid, 'protocol'
    try:
        yield
    finally:
        profile.nodeid, profile.phase = previous


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    profile = item.config._browser_profile
    previous, profile.phase = profile.phase, 'setup'
    try:
        yield
    finally:
        profile.phase = previous


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    profile = item.config._browser_profile
    previous, profile.phase = profile.phase, 'call'
    try:
        yield
    finally:
        profile.phase = previous


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    profile = item.config._browser_profile
    previous, profile.phase = profile.phase, 'teardown'
    try:
        yield
    finally:
        profile.phase = previous


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    item.config._browser_profile.reports.append({
        'nodeid': report.nodeid, 'phase': report.when,
        'outcome': report.outcome, 'seconds': report.duration,
    })


def pytest_sessionfinish(session, exitstatus):
    profile = getattr(session.config, '_browser_profile', None)
    if profile is not None:
        profile.write(exitstatus)


def pytest_unconfigure(config):
    profile = getattr(config, '_browser_profile', None)
    if profile is not None:
        profile.restore()
