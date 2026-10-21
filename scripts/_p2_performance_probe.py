"""Temporary exact-source candidate preparation; never writes commits or refs."""
import argparse
import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

BASE = 'd9336e382541d30f1fa837e5735b9b748e4c3657'
APP_BLOB = 'ebadb445771e3e27c0d5f5f838e46a80d4aeeab8'


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def prepare(root, out):
    assert git(root, 'rev-parse', 'HEAD').decode().strip() == BASE
    assert git(root, 'rev-parse', 'HEAD:spt_desktop/app.py').decode().strip() == APP_BLOB
    path = root / 'spt_desktop/app.py'
    source = git(root, 'show', 'HEAD:spt_desktop/app.py').decode('utf-8')
    old = '''        def update_scrollregion(event=None):
            if self._interaction_current(interaction):
                canvas.configure(scrollregion=canvas.bbox('all'))
'''
    new = '''        layout_ready = False

        def update_scrollregion(event=None):
            if self._interaction_current(interaction):
                # Wrapping finishes in idle geometry work after reflow returns.
                # Match the measured body so its final lines remain reachable.
                height = max(body.winfo_reqheight(), canvas.winfo_height())
                if int(canvas.itemcget(body_window, 'height') or 0) != height:
                    canvas.itemconfigure(body_window, height=height)
                canvas.configure(scrollregion=canvas.bbox('all'))
'''
    assert source.count(old) == 2
    source = source.replace(old, new)
    old = '''        def reflow():
            interaction['layout_after'] = None
            if not self._interaction_current(interaction):
                return
            width = max(1, canvas.winfo_width())
            canvas.itemconfigure(body_window, width=width)
'''
    new = '''        def reflow():
            nonlocal layout_ready
            interaction['layout_after'] = None
            if not self._interaction_current(interaction):
                return
            width = canvas.winfo_width()
            if width <= 1:
                # Native Map/Configure supplies the first usable viewport.
                # Do not spin idle callbacks while the modal is not mapped.
                return
            layout_ready = True
            canvas.itemconfigure(body_window, width=width)
'''
    assert source.count(old) == 2
    source = source.replace(old, new)
    old = '''            if interaction['layout_after'] is None:
                interaction['layout_after'] = dialog.after(75, reflow)
'''
    new = '''            if event is None or not layout_ready:
                # Initial and content layout must not wait for resize debounce.
                # Reuse the modal's owned token so Stop retires either kind.
                if interaction['layout_after'] is not None:
                    dialog.after_cancel(interaction['layout_after'])
                interaction['layout_after'] = dialog.after_idle(reflow)
            elif interaction['layout_after'] is None:
                interaction['layout_after'] = dialog.after(75, reflow)
'''
    assert source.count(old) == 2
    source = source.replace(old, new)
    ast.parse(source)
    path.write_bytes(source.encode('utf-8'))
    assert git(root, 'diff', '--name-only').decode().splitlines() == ['spt_desktop/app.py']
    subprocess.run(['git', '-C', str(root), 'diff', '--check'], check=True)
    (out / 'candidate.patch').write_bytes(git(root, 'diff'))
    (out / 'app.py').write_bytes(path.read_bytes())
    print('Prepared two local layout closures; no tests or consent logic changed.')


def publish(root, out):
    assert os.environ['GITHUB_REPOSITORY'] == 'cepeter-job/spt-downloader'
    assert git(root, 'rev-parse', 'HEAD').decode().strip() == BASE
    assert git(root, 'diff', '--name-only').decode().splitlines() == ['spt_desktop/app.py']
    subprocess.run(['git', '-C', str(root), 'add', 'spt_desktop/app.py'], check=True)
    data = git(root, 'show', ':spt_desktop/app.py')
    sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    request = urllib.request.Request('https://api.github.com/repos/cepeter-job/spt-downloader/git/blobs',
        data=json.dumps({'content': base64.b64encode(data).decode(), 'encoding': 'base64'}).encode(),
        method='POST', headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
            'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.load(response)
    assert result['sha'] == sha
    proof = {'base_commit': BASE, 'original_app_blob': APP_BLOB, 'candidate_app_blob': sha,
             'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
             'branch_refs_changed': False, 'commits_created': False}
    (out / 'candidate-blob.json').write_text(json.dumps(proof, indent=2), encoding='utf-8')
    print(json.dumps(proof))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'publish'])
    parser.add_argument('--source', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    root, out = Path(args.source).resolve(), Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.mode == 'prepare':
        prepare(root, out)
    else:
        publish(root, out)


if __name__ == '__main__':
    main()
