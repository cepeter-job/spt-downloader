"""Publish only verified workbooks; recovery data stays in LocalAppData."""
from datetime import datetime
import hashlib
from pathlib import Path
import re
import shutil
import tempfile
import coretax
from coretax_exporter import validate_scope
from .paths import safe_taxpayer_name


def _digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):
            result.update(chunk)
    return result.digest()


def publish_workbooks(run,source,downloads,job_id,check_cancel=None):
    npwp,year = validate_scope(run['npwp'],run['year'])
    if not isinstance(job_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',job_id):
        raise ValueError('Invalid job identifier')
    name = safe_taxpayer_name(run.get('taxpayer_name',''))
    source,downloads = Path(source).resolve(),Path(downloads).resolve()
    coretax.verify_outputs(run,source)
    filenames = run['output_files']
    if any(not isinstance(n,str) or Path(n).name != n or not n.endswith('.xlsx') for n in filenames):
        raise ValueError('Invalid workbook filename')
    parent = (downloads / f'{npwp} - {name}' / str(year)).resolve()
    if not parent.is_relative_to(downloads):
        raise ValueError('Result folder must remain within the resolved Windows Downloads directory')
    parent.mkdir(parents=True,exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    final = parent / f'{stamp}-{job_id[:12]}'
    if final.exists(): raise FileExistsError('Result folder already exists; previous exports are preserved')
    staging = Path(tempfile.mkdtemp(prefix='.spt-',dir=parent))
    try:
        for filename in filenames:
            if check_cancel: check_cancel()
            original = source / filename
            if original.is_symlink() or not original.resolve().is_relative_to(source):
                raise ValueError('Invalid source workbook path')
            target = staging / filename
            shutil.copy2(original,target)
            if _digest(original) != _digest(target):
                raise OSError('Workbook copy verification failed')
        coretax.verify_outputs(run,staging)
        if check_cancel: check_cancel()
        staging.rename(final)
        return final
    finally:
        if staging.exists(): shutil.rmtree(staging)
