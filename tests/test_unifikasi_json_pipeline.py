"""Connected source adapter and allowlisted-worker contracts for Unifikasi."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from coretax_masa_json import adapt_masa_detail
from unifikasi_projection_fixture import case


@pytest.mark.parametrize('populated', [False, True])
@pytest.mark.parametrize('model', ['Normal', 'Amendment 002'])
def test_full_native_projection_includes_source_labels_and_all_forms(populated, model):
    fixture = case(populated=populated, model=model)
    before = deepcopy(fixture)
    result = adapt_masa_detail(fixture['packets'], record=fixture['record'], scope=fixture['scope'],
                              observed_forms=fixture['forms'])
    assert result['eligible'], result['reason']
    assert result['coverage']['complete'] and len(result['coverage']['grids']) == 5
    assert [s['name'] for s in result['sections']] == ['INDUK', 'DAFTAR-I', 'DAFTAR-II', 'LAMPIRAN-I']
    values = {f['label']: f['value'] for f in result['sections'][0]['fields']}
    assert values['Masa Pajak'] == 'Januari 2025'
    assert values['NPWP Penandatangan'] == '0000000000000001'
    assert values['Wajib Pajak'] == '0' and 'Kuasa Wajib Pajak' not in values
    declarations = [f for f in result['sections'][0]['fields'] if f['field'] == 'DeclarationBy']
    assert len(declarations) == 1 and declarations[0]['value'] == '0'
    assert values['Pernyataan'] == 'true'
    assert values['Status Penyampaian'] == 'Submitted'
    for section in result['sections'][1:]:
        for table in section['tables']:
            assert table['complete'] and table['source_total'] == int(populated)
            if populated:
                assert 'SYNTHETIC LABEL' in table['rows'][0]
    assert any(b['sequence'] == fixture['packets'][-1]['context']['sequence']
               and b['container_path'] == ['Payload'] for b in result['provenance']['bindings'])
    assert fixture == before


@pytest.mark.parametrize('defect', ['missing-selected', 'duplicate-selected', 'wrong-option-label'])
def test_incomplete_declaration_options_cannot_claim_native_coverage(defect):
    fixture = case()
    fields = fixture['forms'][0]['fields']
    selected = next(f for f in fields if f['field'] == 'DeclarationBy' and f['option'] == '0')
    if defect == 'missing-selected':
        fields.remove(selected)
    elif defect == 'duplicate-selected':
        fields.append(deepcopy(selected))
    else:
        selected['label'] = 'UNREVIEWED OPTION'
    result = adapt_masa_detail(fixture['packets'], record=fixture['record'], scope=fixture['scope'],
                              observed_forms=fixture['forms'])
    assert not result['eligible'] and not result['coverage']['complete']


@pytest.mark.parametrize('defect', ['missing', 'wrong-endpoint', 'wrong-sequence'])
def test_missing_reference_custody_never_grants_native_coverage(defect):
    fixture = case()
    if defect == 'missing':
        fixture['forms'][0].pop('references')
    elif defect == 'wrong-endpoint':
        fixture['forms'][0]['references'][0]['endpoint'] += '?other=1'
    else:
        fixture['forms'][0]['references'][0]['sequences'] = [9999]
    result = adapt_masa_detail(fixture['packets'], record=fixture['record'], scope=fixture['scope'],
                              observed_forms=fixture['forms'])
    assert not result['eligible'] and not result['coverage']['complete']


def test_allowlisted_worker_runs_native_unifikasi_without_repository_imports(tmp_path):
    from spt_desktop.runtime import WORKER_FILES
    root = Path(__file__).resolve().parents[1]
    worker = tmp_path / 'worker'
    for name in WORKER_FILES:
        target = worker / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    fixture = case()
    for item in fixture['packets']:
        item['body'] = item['body'].decode('utf-8')
    script = '''import json,sys
from pathlib import Path
worker=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(worker))
from coretax_masa_json import adapt_masa_detail
x=json.load(sys.stdin)
for item in x['packets']: item['body']=item['body'].encode('utf-8')
r=adapt_masa_detail(x['packets'],record=x['record'],scope=x['scope'],observed_forms=x['forms'])
assert r['eligible'],r['reason']
assert r['coverage']['complete'] and len(r['coverage']['grids'])==5
assert len(r['sections'])==4
for name in ('coretax_masa_json','coretax_masa_projection','coretax_unifikasi_json'):
    assert Path(sys.modules[name].__file__).resolve().is_relative_to(worker)
print('isolated native Unifikasi verified')
'''
    result = subprocess.run([sys.executable, '-I', '-c', script, str(worker)], cwd=tmp_path,
                            input=json.dumps(fixture), text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stdout.strip() == 'isolated native Unifikasi verified'
