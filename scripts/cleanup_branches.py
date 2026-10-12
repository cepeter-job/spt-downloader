"""Pratinjau atau hapus cabang PR selesai yang seluruh riwayatnya sudah di main."""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener


class CleanupError(RuntimeError):
    """Pembersihan berhenti bila bukti keamanan atau izin tidak mencukupi."""


def valid_branch(name):
    return (isinstance(name, str) and bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]*', name))
            and not any(part.startswith('.') or part.endswith('.lock') or not part
                        for part in name.split('/'))
            and '..' not in name and not name.endswith('.'))


def valid_sha(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[a-f0-9]{40}', value))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Header otorisasi hanya boleh dikirim ke API repositori yang dituju.
        raise CleanupError('API mengalihkan permintaan; periksa nama repositori.')


class GitHubAPI:
    def __init__(self, repository, token=''):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise CleanupError('Nama repositori harus owner/repo.')
        if any(part in ('.', '..') for part in repository.split('/')):
            raise CleanupError('Nama repositori tidak valid.')
        self.repository = repository
        self.root = f'https://api.github.com/repos/{repository}'
        self.token = token
        self.opener = build_opener(NoRedirect)

    def get(self, path=''):
        url = self.root + ('/' + path if path else '')
        headers = {'Accept': 'application/vnd.github+json',
                   'X-GitHub-Api-Version': '2022-11-28',
                   'User-Agent': 'spt-downloader-branch-maintenance'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        try:
            with self.opener.open(Request(url, headers=headers), timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code == 404 and path.startswith('branches/'):
                return None
            raise CleanupError(f'API GitHub gagal dengan HTTP {error.code}.') from None
        except (URLError, ValueError):
            raise CleanupError('API GitHub tidak memberikan respons yang dapat diverifikasi.') from None

    def pages(self, path):
        values = []
        separator = '&' if '?' in path else '?'
        for page in range(1, 101):
            batch = self.get(f'{path}{separator}per_page=100&page={page}')
            if not isinstance(batch, list):
                raise CleanupError('Daftar metadata GitHub tidak valid.')
            values.extend(batch)
            if len(batch) < 100:
                return values
        # Jangan menganggap daftar terpotong sebagai daftar lengkap PR terbuka.
        raise CleanupError('Batas pagination tercapai; tidak ada cabang yang dihapus.')


def same_repository(pr, repository):
    owner = (pr.get('head') or {}).get('repo') or {}
    return owner.get('full_name', '').lower() == repository.lower()


def cleanup(api, *, base, expected_base, apply=False, delete=None):
    if not valid_branch(base) or not valid_sha(expected_base):
        raise CleanupError('Cabang utama dan SHA hasil test wajib valid.')
    repository = api.get()
    if repository.get('default_branch') != base:
        raise CleanupError('Target harus cabang default repositori.')

    def ensure_main():
        current = api.get('branches/' + quote(base, safe=''))
        if not current or current.get('commit', {}).get('sha') != expected_base:
            raise CleanupError(f'{base} berubah dari commit yang telah diuji; pembersihan dihentikan.')

    def open_branches():
        # Base PR aktif juga masih dipakai, termasuk PR dengan head pada fork.
        return {ref.get('ref') for pr in api.pages('pulls?state=open')
                for field in ('head', 'base')
                if (ref := pr.get(field) or {})
                and (ref.get('repo') or {}).get('full_name', '').lower() == api.repository.lower()}

    ensure_main()
    branches = {branch['name']: branch for branch in api.pages('branches')}
    opened = open_branches()
    closed = api.pages('pulls?state=closed')
    candidates = {}
    for pr in closed:
        if pr.get('state') != 'closed' or not same_repository(pr, api.repository):
            continue
        head = pr.get('head') or {}
        name, sha = head.get('ref'), head.get('sha')
        branch = branches.get(name, {})
        if (not valid_branch(name) or not valid_sha(sha) or name == base or name in opened
                or branch.get('protected') is not False or branch.get('commit', {}).get('sha') != sha):
            continue
        candidates[name] = sha

    result = {'deleted': [], 'eligible': []}
    for name, sha in sorted(candidates.items()):
        comparison = api.get(f'compare/{sha}...{expected_base}')
        # PR tertutup saja tidak cukup. SHA cabang harus benar-benar ancestor main,
        # sehingga PR squash/rebase yang belum terbukti aman tetap dipertahankan.
        if (comparison.get('status') not in ('ahead', 'identical')
                or comparison.get('behind_by') != 0
                or comparison.get('merge_base_commit', {}).get('sha') != sha):
            continue
        ensure_main()
        latest = api.get('branches/' + quote(name, safe=''))
        if (not latest or latest.get('protected') is not False
                or latest.get('commit', {}).get('sha') != sha or name in open_branches()):
            continue
        result['eligible'].append(name)
        if apply:
            if delete is None:
                raise CleanupError('Operasi hapus belum disediakan.')
            delete(name, sha)
            result['deleted'].append(name)
    return result


def git_environment(token, repository):
    # Token hanya di environment proses Git, bukan argv, berkas, atau log.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('GIT_TRACE', 'GIT_CONFIG'))
           and key not in ('GH_TOKEN', 'GITHUB_TOKEN', 'GIT_CURL_VERBOSE')}
    authorization = base64.b64encode(f'x-access-token:{token}'.encode()).decode()
    config = [('http.extraheader', ''),
              (f'http.https://github.com/{repository}.git.extraheader', f'AUTHORIZATION: basic {authorization}'),
              ('http.followRedirects', 'false'), ('credential.helper', '')]
    env.update({'GIT_CONFIG_COUNT': str(len(config)), 'GIT_TERMINAL_PROMPT': '0',
                'GCM_INTERACTIVE': 'never'})
    for index, (key, value) in enumerate(config):
        env[f'GIT_CONFIG_KEY_{index}'] = key
        env[f'GIT_CONFIG_VALUE_{index}'] = value
    return env


def delete_with_lease(remote, branch, expected_sha, *, env, cwd=None):
    if not valid_branch(branch) or not valid_sha(expected_sha):
        raise CleanupError('Cabang atau SHA penghapusan tidak valid.')
    ref = 'refs/heads/' + branch
    # Git memeriksa SHA secara atomik di server; push baru tidak boleh ikut hilang.
    command = ['git', 'push', '--porcelain', f'--force-with-lease={ref}:{expected_sha}',
               remote, ':' + ref]
    try:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                                text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise CleanupError(f'Penghapusan {branch} tidak dapat dikonfirmasi; periksa remote.') from None
    if result.returncode:
        # Output Git dapat berisi konteks autentikasi. Cukup laporkan operasi gagal.
        raise CleanupError(f'Penghapusan {branch} ditolak; SHA berubah atau izin tidak mencukupi.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--base', default='main')
    parser.add_argument('--expected-base', required=True)
    parser.add_argument('--apply', action='store_true', help='Hapus kandidat; tanpa opsi ini hanya pratinjau.')
    args = parser.parse_args(argv)
    try:
        token = os.environ.get('GH_TOKEN', '')
        if args.apply and not token:
            raise CleanupError('GH_TOKEN dengan contents:write diperlukan untuk penghapusan.')
        api = GitHubAPI(args.repository, token)
        remote = f'https://github.com/{args.repository}.git'
        env = git_environment(token, args.repository) if args.apply else None
        result = cleanup(api, base=args.base, expected_base=args.expected_base, apply=args.apply,
                         delete=lambda name, sha: delete_with_lease(remote, name, sha, env=env))
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except CleanupError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
