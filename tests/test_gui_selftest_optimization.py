"""Issue #218: packaged GUI release checks must survive Python optimization.

All subprocess cases inject a synthetic failure without creating a Tk root,
opening an account, accessing Coretax, or reading local customer data.
"""
import ast
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_gui_self_test_has_no_optimization_sensitive_assert_statements():
    tree = ast.parse((ROOT / 'spt_gui.py').read_text(encoding='utf-8'))
    target = next(node for node in tree.body
                  if isinstance(node, ast.FunctionDef) and node.name == 'self_test')
    assert not any(isinstance(node, ast.Assert) for node in ast.walk(target))
    checks = [node for node in ast.walk(target)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id == 'require']
    # The frozen self-test already covers many control and resource boundaries;
    # accidental mass-removal would be a regression even if it still exits 0.
    assert len(checks) >= 39


@pytest.mark.parametrize('optimization', [(), ('-O',), ('-OO',)])
def test_failed_explicit_self_test_check_is_never_optimized_away(optimization):
    code = textwrap.dedent("""
        from spt_gui import SelfTestFailure, require
        try:
            require(False, 'synthetic intentional failure')
        except SelfTestFailure as error:
            print(str(error))
            raise SystemExit(23)
        raise SystemExit(0)
    """)
    process = subprocess.run(
        [sys.executable, *optimization, '-c', code],
        cwd=ROOT, capture_output=True, text=True, timeout=35,
        env={**os.environ, 'PYTHONOPTIMIZE': '0'})
    assert process.returncode == 23, (process.stdout, process.stderr)
    assert process.stdout.strip() == 'GUI self-test failed: synthetic intentional failure'


@pytest.mark.parametrize('optimization', [(), ('-O',), ('-OO',)])
def test_gui_self_test_cli_fails_closed_with_sanitized_message(
        optimization, tmp_path):
    report = tmp_path / 'must-not-publish.json'
    code = textwrap.dedent("""
        from spt_gui import main, require
        import spt_gui
        def injected_synthetic_failure(report):
            require(False, 'synthetic release check')
        spt_gui.self_test = injected_synthetic_failure
        raise SystemExit(main(['--self-test', '--report', {report!r}]))
    """).format(report=str(report))
    process = subprocess.run(
        [sys.executable, *optimization, '-c', code],
        cwd=ROOT, capture_output=True, text=True, timeout=35,
        env={**os.environ, 'PYTHONOPTIMIZE': '0'})
    assert process.returncode == 1, (process.stdout, process.stderr)
    assert process.stderr.strip() == 'GUI self-test failed: synthetic release check'
    assert not process.stdout.strip()
    assert not report.exists()


def test_gui_self_test_optimization_via_environment_variable():
    code = textwrap.dedent("""
        import sys
        from spt_gui import require, SelfTestFailure
        if sys.flags.optimize != 2:
            raise SystemExit(72)
        try:
            require(False, 'optimized environment')
        except SelfTestFailure:
            raise SystemExit(23)
        raise SystemExit(0)
    """)
    process = subprocess.run(
        [sys.executable, '-c', code],
        cwd=ROOT, capture_output=True, text=True, timeout=35,
        env={**os.environ, 'PYTHONOPTIMIZE': '2'})
    assert process.returncode == 23, (process.stdout, process.stderr)


def test_frozen_build_still_executes_gui_self_test_release_gate():
    build = (ROOT / 'build_desktop.py').read_text(encoding='utf-8')
    tree = ast.parse(build)
    assert any(isinstance(node, ast.Constant) and node.value == '--self-test'
               for node in ast.walk(tree))
    assert 'validate_report(data, python_profile)' in build
