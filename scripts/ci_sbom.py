"""Inventory the final Windows distribution without executing its native bytes."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import re


NATIVE_COVERAGE = (
    'Bundled native files are hashed and inventoried, not vulnerability-audited by pip-audit. '
    'Python package advisories are audited separately. Microsoft Edge is an external, '
    'user-managed prerequisite and is not bundled. The application hash covers the '
    'PyInstaller bootloader; it is not a separate native vulnerability assessment.'
)


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('SBOM requires a complete SHA-256 digest.')
    return value


def _native_path(value):
    if not isinstance(value, str):
        raise ValueError('Native inventory path is invalid.')
    path = value.replace('\\', '/')
    parts = PurePosixPath(path).parts
    if (not parts or path.startswith('/') or ':' in path
            or any(part in ('', '.', '..') for part in path.split('/'))):
        raise ValueError('Native inventory contains an unsafe path.')
    return path


def _properties(values):
    return [{'name': name, 'value': str(value)} for name, value in values.items()]


def _property_map(values):
    if not isinstance(values, list):
        raise ValueError('SBOM properties are missing.')
    result = {}
    for item in values:
        if (not isinstance(item, dict) or set(item) != {'name', 'value'}
                or not isinstance(item['name'], str) or not isinstance(item['value'], str)
                or item['name'] in result):
            raise ValueError('SBOM properties are malformed or duplicated.')
        result[item['name']] = item['value']
    return result


def make_sbom(*, build_info, executable_digest, native_files, runtime_packages,
              runtime_lock_digest, versions):
    from scripts.ci_artifact import validate_build_info

    validate_build_info(build_info)
    _digest(executable_digest)
    _digest(runtime_lock_digest)
    if any(not re.fullmatch(r'\d+\.\d+\.\d+', str(versions.get(key, '')))
           for key in ('python', 'tcl', 'tk', 'uv', 'pyinstaller')):
        raise ValueError('SBOM requires observed interpreter, Tcl/Tk, uv and builder versions.')
    components, seen, principals = [], set(), set()
    for entry in sorted(native_files, key=lambda item: item['path']):
        path = _native_path(entry['path'])
        if path.casefold() in seen:
            raise ValueError('Native inventory contains duplicate or colliding paths.')
        seen.add(path.casefold())
        if type(entry.get('size_bytes')) is not int or entry['size_bytes'] < 1:
            raise ValueError('Native inventory must record actual nonempty bytes.')
        name = PurePosixPath(path).name
        version, source = entry.get('file_version'), 'PE file version resource'
        if re.fullmatch(r'python\d+\.dll', name, re.IGNORECASE):
            version, source = versions['python'], 'validated frozen CPython self-test'
            principals.add('python')
        elif re.fullmatch(r'tcl\d+t?\.dll', name, re.IGNORECASE):
            version, source = versions['tcl'], 'validated frozen Tcl self-test'
            principals.add('tcl')
        elif re.fullmatch(r'tk\d+t?\.dll', name, re.IGNORECASE):
            version, source = versions['tk'], 'validated frozen Tk self-test'
            principals.add('tk')
        elif path.casefold() == 'tools/uv.exe':
            version, source = versions['uv'], 'builder-verified bundled uv binary'
            principals.add('uv')
        properties = {
            'spt:delivery': 'bundled-native', 'spt:archive_path': path,
            'spt:size_bytes': entry['size_bytes'],
            'spt:version_evidence': source if version else 'not present in PE resources',
        }
        component = {
            'type': 'application' if path.casefold() == 'tools/uv.exe' else 'library',
            'bom-ref': 'native:' + path, 'name': name,
            'hashes': [{'alg': 'SHA-256', 'content': _digest(entry['sha256'])}],
            'properties': _properties(properties),
        }
        if version:
            component['version'] = str(version)
        components.append(component)
    if principals != {'python', 'tcl', 'tk', 'uv'}:
        raise ValueError('Native SBOM is missing bundled CPython, Tcl/Tk or uv.')
    if not {'playwright', 'openpyxl'} <= runtime_packages.keys():
        raise ValueError('SBOM is missing the managed worker dependency scope.')
    for name, version in sorted(runtime_packages.items()):
        if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name)
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+!-]*', version)):
            raise ValueError('Worker package pin is invalid.')
        purl = f'pkg:pypi/{name.lower().replace("_", "-")}@{version}'
        components.append({
            'type': 'library', 'bom-ref': purl, 'name': name, 'version': version, 'purl': purl,
            'properties': _properties({'spt:delivery': 'managed-worker-download'}),
        })
    return {
        'bomFormat': 'CycloneDX', 'specVersion': '1.6', 'version': 1,
        'metadata': {
            'component': {
                'type': 'application', 'bom-ref': 'spt-downloader', 'name': 'SPTDownloader.exe',
                'version': build_info['commit'],
                'hashes': [{'alg': 'SHA-256', 'content': executable_digest}],
            },
            'tools': {'components': [{
                'type': 'application', 'name': 'PyInstaller', 'version': versions['pyinstaller'],
                'scope': 'excluded',
            }]},
            'properties': _properties({
                'spt:run_id': build_info['run_id'], 'spt:run_attempt': build_info['run_attempt'],
                'spt:runtime_lock_sha256': runtime_lock_digest,
                'spt:native_audit_coverage': NATIVE_COVERAGE,
            }),
        },
        'components': components,
        'dependencies': [{'ref': 'spt-downloader',
                          'dependsOn': [item['bom-ref'] for item in components]}],
    }


def validate_sbom(data, *, build_info, executable_digest):
    """Check distribution binding using only stdlib on the provenance runner."""
    from scripts.ci_artifact import validate_build_info

    validate_build_info(build_info)
    if (not isinstance(data, dict) or data.get('bomFormat') != 'CycloneDX'
            or data.get('specVersion') != '1.6' or type(data.get('version')) is not int
            or data['version'] != 1 or not isinstance(data.get('metadata'), dict)):
        raise ValueError('Distribution SBOM format is invalid.')
    metadata = data['metadata']
    component = metadata.get('component', {})
    if (component.get('name') != 'SPTDownloader.exe' or component.get('version') != build_info['commit']
            or component.get('hashes') != [{'alg': 'SHA-256', 'content': _digest(executable_digest)}]):
        raise ValueError('Distribution SBOM does not match the executable and build identity.')
    properties = _property_map(metadata.get('properties'))
    if (properties.get('spt:run_id') != build_info['run_id']
            or properties.get('spt:run_attempt') != str(build_info['run_attempt'])
            or properties.get('spt:native_audit_coverage') != NATIVE_COVERAGE):
        raise ValueError('Distribution SBOM run identity or audit coverage is invalid.')
    _digest(properties.get('spt:runtime_lock_sha256'))
    components = data.get('components')
    if not isinstance(components, list) or not components:
        raise ValueError('Distribution SBOM has no native or worker components.')
    refs, native, worker = set(), [], {}
    for item in components:
        if not isinstance(item, dict) or not isinstance(item.get('bom-ref'), str):
            raise ValueError('Distribution SBOM component is malformed.')
        ref = item['bom-ref']
        if ref in refs:
            raise ValueError('Distribution SBOM component is duplicated.')
        refs.add(ref)
        props = _property_map(item.get('properties'))
        if ref.startswith('native:'):
            path = _native_path(props.get('spt:archive_path'))
            hashes = item.get('hashes')
            if (ref != 'native:' + path or props.get('spt:delivery') != 'bundled-native'
                    or not re.fullmatch(r'[1-9][0-9]*', props.get('spt:size_bytes', ''))
                    or not isinstance(hashes, list) or len(hashes) != 1
                    or hashes[0].get('alg') != 'SHA-256'):
                raise ValueError('Distribution SBOM native evidence is invalid.')
            _digest(hashes[0].get('content'))
            native.append(path.casefold())
        elif props.get('spt:delivery') == 'managed-worker-download':
            worker[item.get('name')] = item.get('version')
        else:
            raise ValueError('Distribution SBOM contains an unknown delivery scope.')
    names = [PurePosixPath(path).name for path in native]
    if (len(native) != len(set(native)) or 'tools/uv.exe' not in native
            or not any(re.fullmatch(r'python\d+\.dll', name) for name in names)
            or not any(re.fullmatch(r'tcl\d+t?\.dll', name) for name in names)
            or not any(re.fullmatch(r'tk\d+t?\.dll', name) for name in names)
            or not {'playwright', 'openpyxl'} <= worker.keys()):
        raise ValueError('Distribution SBOM lacks its required native and worker inventory.')


def native_inventory(executable):
    # These packages already belong to the hash-locked build environment. This
    # parses the CArchive/PE bytes; it never loads a DLL or starts the executable.
    import pefile
    from PyInstaller.archive.readers import CArchiveReader

    archive = CArchiveReader(str(executable))
    result = []
    for name, entry in sorted(archive.toc.items()):
        if entry[-1] != 'b':
            continue
        content = archive.extract(name)
        item = {'path': _native_path(name), 'sha256': hashlib.sha256(content).hexdigest(),
                'size_bytes': len(content)}
        try:
            pe = pefile.PE(data=content, fast_load=True)
            try:
                pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
                fixed = getattr(pe, 'VS_FIXEDFILEINFO', [])
                if fixed:
                    info = fixed[0]
                    item['file_version'] = '.'.join(str(value) for value in (
                        info.FileVersionMS >> 16, info.FileVersionMS & 0xffff,
                        info.FileVersionLS >> 16, info.FileVersionLS & 0xffff))
            finally:
                pe.close()
        except pefile.PEFormatError:
            # Unknown version stays explicit; the actual bytes still have a hash.
            pass
        result.append(item)
    return result


def create(folder, python_version):
    from scripts.ci_artifact import checked_build_info, checked_report
    from spt_desktop.runtime import UV_VERSION

    folder = Path(folder)
    report = checked_report(folder, python_version)
    identity = checked_build_info(folder)
    executable = folder / 'SPTDownloader.exe'
    root = Path(__file__).resolve().parents[1]
    lock = (root / 'locks/runtime.txt').read_bytes()
    packages = {}
    for line in lock.decode('utf-8').splitlines():
        if not line or line.startswith(('#', ' ', '\t')):
            continue
        match = re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.+!-]*)(?: \\)?', line)
        if not match or match[1] in packages:
            raise ValueError('Runtime lock contains an unsupported or duplicated package pin.')
        packages[match[1]] = match[2]
    with executable.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    data = make_sbom(
        build_info=identity, executable_digest=digest,
        native_files=native_inventory(executable), runtime_packages=packages,
        runtime_lock_digest=hashlib.sha256(lock).hexdigest(),
        versions={'python': report['python'], 'tcl': report['tcl'], 'tk': report['tk'],
                  'uv': UV_VERSION, 'pyinstaller': importlib.metadata.version('pyinstaller')})
    validate_sbom(data, build_info=identity, executable_digest=digest)
    (folder / 'distribution-sbom.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('create',))
    parser.add_argument('folder', type=Path)
    parser.add_argument('--python-version', required=True)
    args = parser.parse_args(argv)
    create(args.folder, args.python_version)
    print('Recorded the distribution SBOM with explicit native audit coverage limits.')


if __name__ == '__main__':
    main()
