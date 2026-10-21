"""Temporary RED/GREEN preparation; publishes blobs only, never commits or refs."""
import argparse
import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

BASE = 'd9336e382541d30f1fa837e5735b9b748e4c3657'
APP_BLOB = 'ebadb445771e3e27c0d5f5f838e46a80d4aeeab8'
PATHS = ['spt_desktop/app.py', 'tests/test_desktop_dialog_layout.py', 'tests/test_desktop_dialog_readiness.py']


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def replace(source, old, new, count=1):
    assert source.count(old) == count, (old[:100], source.count(old), count)
    return source.replace(old, new)


def tests_first(root, out):
    assert git(root, 'rev-parse', 'HEAD').decode().strip() == BASE
    path = root / 'tests/test_desktop_dialog_layout.py'
    original = git(root, 'show', 'HEAD:tests/test_desktop_dialog_layout.py').decode('utf-8')
    source = replace(original, 'import gc\n', 'import gc\nimport _tkinter\nimport time\n')
    helper = '''def queue_native_resize(root, app, dialog):
    """Produce an actual viewport resize without executing the owned timer."""
    width, height = dialog.winfo_width(), dialog.winfo_height()
    target = width - 1 if width > dialog.minsize()[0] else width + 1
    dialog.geometry(f'{target}x{height}')
    flags = _tkinter.WINDOW_EVENTS | _tkinter.IDLE_EVENTS | _tkinter.DONT_WAIT
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        root.tk.dooneevent(flags)
        if (dialog.winfo_width() != width
                and app._interaction['layout_after'] is not None):
            return
        time.sleep(.001)
    pytest.fail('A real native resize did not queue owned layout work')


'''
    source = replace(source, 'def label_text(widget):\n', helper + 'def label_text(widget):\n')
    old = "    for _ in range(20):\n        dialog.event_generate('<Configure>')\n"
    source = replace(source, old, '    queue_native_resize(root, app, dialog)\n' + old, 2)
    source = replace(source, "    dialog = open_selection(active_app)\n    dialog.event_generate('<Configure>')\n",
                     '    dialog = open_selection(active_app)\n    queue_native_resize(root, app, dialog)\n')
    source = replace(source, "        modal.event_generate('<Configure>')\n",
                     '        queue_native_resize(root, app, modal)\n', 2)
    old_asserts = [ast.dump(n) for n in ast.walk(ast.parse(original)) if isinstance(n, ast.Assert)]
    new_asserts = [ast.dump(n) for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Assert)]
    assert old_asserts == new_asserts, 'Existing assertions must remain identical'
    path.write_bytes(source.encode())
    path = root / 'tests/test_desktop_dialog_readiness.py'
    source = git(root, 'show', 'HEAD:tests/test_desktop_dialog_readiness.py').decode('utf-8')
    source += '''\n\n@pytest.mark.parametrize('kind', ['selection', 'overwrite'])
def test_duplicate_configure_does_not_queue_redundant_layout(active_window, kind):
    root, app, controller = active_window
    controller.payload = payload(kind, 3)
    app.on_event(consent_event(controller, kind))
    dialog = app._interaction['dialog']
    wait_for_existing_timers(root)
    viewport = named_widget(dialog, 'body_viewport')
    before = (viewport.winfo_width(), viewport.winfo_height(), viewport.cget('scrollregion'))
    for _ in range(20):
        dialog.event_generate('<Configure>')
        viewport.event_generate('<Configure>')
    drain_native_layout_without_timers(root, dialog)
    assert (viewport.winfo_width(), viewport.winfo_height(), viewport.cget('scrollregion')) == before
    assert app._interaction['layout_after'] is None
    assert_body_ready(dialog)
    assert not controller.replies and not controller.stopped
'''
    ast.parse(source)
    path.write_bytes(source.encode())
    subprocess.run(['git', '-C', str(root), 'diff', '--check'], check=True)
    (out / 'tests-first.patch').write_bytes(git(root, 'diff'))
    for name in PATHS[1:]:
        (out / Path(name).name).write_bytes((root / name).read_bytes())
    (out / 'test-proof.json').write_text(json.dumps({'base': BASE,
        'existing_assertions_unchanged': True, 'old_assertion_count': len(old_asserts),
        'fixture_change': 'Real native resizing instead of synthetic unchanged Configure events'}, indent=2))


def observe_red(root, out):
    assert git(root, 'rev-parse', 'HEAD:spt_desktop/app.py').decode().strip() == APP_BLOB
    assert (root / 'spt_desktop/app.py').read_text() == git(root, 'show', 'HEAD:spt_desktop/app.py').decode()
    targets = ['tests/test_desktop_dialog_readiness.py',
        'tests/test_desktop_dialog_layout.py::test_selection_reflow_preserves_data_and_owned_resources',
        'tests/test_desktop_dialog_layout.py::test_old_reflow_cannot_steal_terminal_focus',
        'tests/test_desktop_dialog_layout.py::test_dialog_close_cancels_only_owned_callbacks']
    command = [sys.executable, '-m', 'pytest', '-q', *targets, '--basetemp', str(out.parent/'p2-red-tests'),
               '--junitxml', str(out/'red.xml')]
    result = subprocess.run(command, cwd=root, text=True, encoding='utf-8', errors='replace', capture_output=True, timeout=180)
    (out/'red.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    suites = list(ET.parse(out/'red.xml').getroot().iter('testsuite'))
    assert result.returncode == 1
    assert sum(int(s.get('errors',0)) for s in suites) == 0
    assert sum(int(s.get('failures',0)) for s in suites) == 8
    assert sum(int(s.get('tests',0)) for s in suites) == 13
    for case in ET.parse(out/'red.xml').getroot().iter('testcase'):
        if case.find('failure') is not None:
            assert case.get('classname') == 'tests.test_desktop_dialog_readiness'
    print('Observed 8 readiness/duplicate-event failures; 5 lifecycle cases passed; no setup/collection errors.')


def implement(root, out):
    path = root / 'spt_desktop/app.py'
    source = git(root, 'show', 'HEAD:spt_desktop/app.py').decode('utf-8')
    old = '''        def update_scrollregion(event=None):
            if self._interaction_current(interaction):
                canvas.configure(scrollregion=canvas.bbox('all'))
'''
    new = '''        layout_size = None

        def update_scrollregion(event=None):
            if self._interaction_current(interaction):
                # Wrapping finishes in idle geometry work after reflow returns.
                # Match the measured body so its final lines remain reachable.
                height = max(body.winfo_reqheight(), canvas.winfo_height())
                if int(canvas.itemcget(body_window, 'height') or 0) != height:
                    canvas.itemconfigure(body_window, height=height)
                canvas.configure(scrollregion=canvas.bbox('all'))
'''
    source = replace(source, old, new, 2)
    old = '''        def reflow():
            interaction['layout_after'] = None
            if not self._interaction_current(interaction):
                return
            width = max(1, canvas.winfo_width())
            canvas.itemconfigure(body_window, width=width)
'''
    new = '''        def reflow():
            nonlocal layout_size
            interaction['layout_after'] = None
            if not self._interaction_current(interaction):
                return
            width = canvas.winfo_width()
            if width <= 1:
                # Native Map/Configure supplies the first usable viewport.
                # Do not spin idle callbacks while the modal is not mapped.
                return
            layout_size = (width, canvas.winfo_height())
            canvas.itemconfigure(body_window, width=width)
'''
    source = replace(source, old, new, 2)
    old = '''            if interaction['layout_after'] is None:
                interaction['layout_after'] = dialog.after(75, reflow)
'''
    new = '''            if event is not None and (canvas.winfo_width(), canvas.winfo_height()) == layout_size:
                # Windows can deliver obsolete/duplicate Configure messages
                # after the viewport is already arranged at its actual size.
                return
            if event is None or layout_size is None:
                # Initial and content layout must not wait for resize debounce.
                # Reuse the modal's owned token so Stop retires either kind.
                if interaction['layout_after'] is not None:
                    dialog.after_cancel(interaction['layout_after'])
                interaction['layout_after'] = dialog.after_idle(reflow)
            elif interaction['layout_after'] is None:
                interaction['layout_after'] = dialog.after(75, reflow)
'''
    source = replace(source, old, new, 2)
    ast.parse(source)
    path.write_bytes(source.encode())
    subprocess.run(['git', '-C', str(root), 'diff', '--check'], check=True)
    (out/'candidate.patch').write_bytes(git(root, 'diff'))
    (out/'app.py').write_bytes(path.read_bytes())


def publish(root, out):
    assert os.environ['GITHUB_REPOSITORY'] == 'cepeter-job/spt-downloader'
    assert git(root, 'rev-parse', 'HEAD').decode().strip() == BASE
    assert sorted(git(root, 'diff', '--name-only').decode().splitlines()) == PATHS
    subprocess.run(['git', '-C', str(root), 'add', '--', *PATHS], check=True)
    proof = []
    for path in PATHS:
        data = git(root, 'show', ':' + path)
        sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        request = urllib.request.Request('https://api.github.com/repos/cepeter-job/spt-downloader/git/blobs',
            data=json.dumps({'content': base64.b64encode(data).decode(), 'encoding': 'base64'}).encode(),
            method='POST', headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],
                'Accept':'application/vnd.github+json', 'Content-Type':'application/json'})
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
        assert result['sha'] == sha
        proof.append({'path':path, 'blob':sha, 'sha256':hashlib.sha256(data).hexdigest(), 'bytes':len(data)})
    report = {'base_commit':BASE, 'files':proof, 'branch_refs_changed':False, 'commits_created':False}
    (out/'candidate-blobs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['tests', 'red', 'implement', 'publish'])
    parser.add_argument('--source', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    root,out = Path(args.source).resolve(),Path(args.out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    assert git(root,'rev-parse','HEAD').decode().strip()==BASE
    {'tests':tests_first,'red':observe_red,'implement':implement,'publish':publish}[args.mode](root,out)


if __name__ == '__main__':
    main()
