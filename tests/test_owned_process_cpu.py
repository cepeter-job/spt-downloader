"""Isolated read-only host process CPU accounting, no Coretax/browser access."""
import subprocess  # nosec B404 - Fixed synthetic child process, no shell or user input.
import sys

import pytest

from spt_desktop import owned_process_cpu as cpu


def test_pairing_counts_direct_and_nested_cpu_without_exposing_pid():
    before = {101: (20, 30000, 1), 102: (22, 50000, 2)}
    after = {101: (20, 50000, 1), 102: (22, 90000, 2)}
    assert cpu.paired_cpu_delta(before, after) == (2.0, 4.0)
    assert cpu.paired_cpu_delta({}, after) is None
    assert cpu.paired_cpu_delta(before, None) is None


@pytest.mark.parametrize('changed', [
    {101: (21, 50000, 1), 102: (22, 90000, 2)},  # PID reuse
    {101: (20, 50000, 2), 102: (22, 90000, 2)},  # reparent
    {101: (20, 10000, 1), 102: (22, 90000, 2)},  # impossible CPU drop
    {101: (20, 50000, 1)},                        # child exit
    {101: (20, 50000, 1), 102: (22, 90000, 2),
     103: (23, 10000, 2)},                        # spawned child
])
def test_pairing_refuses_partial_or_reused_processes(changed):
    before = {101: (20, 30000, 1), 102: (22, 50000, 2)}
    assert cpu.paired_cpu_delta(before, changed) is None


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows Toolhelp only')
def test_native_owned_process_snapshot_observes_only_direct_synthetic_child():
    # Fixed executable and arguments; test never opens a user browser.
    p = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(5)'],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)  # nosec B603 - Synthetic worker owned by this test.
    try:
        sample = cpu.snapshot()
        assert sample is not None and p.pid in sample
        created, ticks, depth = sample[p.pid]
        assert created > 0 and ticks >= 0 and depth == 1
    finally:
        p.terminate()
        p.wait(timeout=10)


def test_unsupported_host_does_not_enumerate_processes(monkeypatch):
    monkeypatch.setattr(cpu, 'supported', lambda: False)
    assert cpu.snapshot() is None
