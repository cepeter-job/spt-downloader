"""Native PPh21 projection must run from the exact packaged worker allowlist."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from masa_json_fixtures import SCOPE
from pph21_projection_fixture import case


def test_allowlisted_worker_projects_all_five_pph21_forms_without_repository_imports(tmp_path):
    from spt_desktop.runtime import WORKER_FILES
    root = Path(__file__).resolve().parents[1]
    worker = tmp_path / 'worker'
    for name in WORKER_FILES:
        target = worker / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    record, packets, forms = case()
    for packet in packets:
        packet['body'] = packet['body'].decode('utf-8')
    fixture = {'record': record, 'packets': packets, 'forms': forms, 'scope': SCOPE}
    script = """import json,sys
from pathlib import Path
worker=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(worker))
import coretax_browser
from coretax_masa_json import adapt_masa_detail
x=json.load(sys.stdin)
for packet in x['packets']: packet['body']=packet['body'].encode('utf-8')
r=adapt_masa_detail(x['packets'],record=x['record'],scope=x['scope'],observed_forms=x['forms'])
assert r['eligible'],r['reason']
assert r['coverage']['complete'] and len(r['coverage']['grids'])==7
assert [s['name'] for s in r['sections']]==['Induk','L-IA','L-IB','L-II','L-III']
for name in ('coretax_browser','coretax_masa_json','coretax_pph21_projection',
             'coretax_pph21_json_bindings','coretax_pph21_observer'):
    assert Path(sys.modules[name].__file__).resolve().is_relative_to(worker),name
print('isolated PPh21 native projection verified')
"""
    result = subprocess.run([sys.executable, '-I', '-c', script, str(worker)], cwd=tmp_path,
                            input=json.dumps(fixture), text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stdout.strip() == 'isolated PPh21 native projection verified'
