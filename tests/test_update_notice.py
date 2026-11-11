"""Offline tests for the manually deployed Cloudflare Worker update manifest."""
from email.message import Message
import json

import pytest

from spt_desktop import update_notice as updates


LOCAL = {'schema': 1, 'commit': 'a' * 40, 'run_id': '410', 'run_attempt': 1}
REMOTE = {'schema': 1, 'commit': 'b' * 40, 'run_id': '420', 'run_attempt': 1}
URL = 'https://divine-hill-13fc.punzer4.workers.dev/'


class FakeResponse:
    def __init__(self, data, *, url=URL, status=200, content_type='application/json'):
        self.body, self.url, self.status = data, url, status
        self.headers = Message()
        self.headers['Content-Type'] = content_type

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def read(self, size):
        return self.body[:size]


class FakeOpener:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def open(self, req, timeout):
        self.calls.append((req, timeout))
        return self.response


def manifest(**changes):
    return json.dumps(dict(REMOTE, **changes)).encode('utf-8')


def test_valid_notice_only_when_published_run_newer_and_commit_changed():
    notice = updates.parse_manifest(manifest())
    assert notice.commit == REMOTE['commit']
    assert updates.newer_than_installed(notice, LOCAL)
    for installed in (dict(LOCAL, commit='b' * 40),
                      dict(LOCAL, run_id='420'), dict(LOCAL, run_id='421'),
                      dict(LOCAL, run_id=420), None):
        assert not updates.newer_than_installed(notice, installed)


@pytest.mark.parametrize('bad', [
    dict(run_id='0'), dict(run_id=420), dict(run_attempt=True),
    dict(schema=True), dict(commit='A' * 40), dict(commit='not-a-commit'),
    dict(version='2026.11.1'), dict(notes='Release notes'),
    dict(download_url='https://example.com/untrusted.exe'),
])
def test_rejects_unsafe_or_ambiguous_manifest(bad):
    with pytest.raises(updates.UpdateLookupError):
        updates.parse_manifest(manifest(**bad))


def test_rejects_duplicate_keys_and_non_object_json():
    for source in (b'{"schema":1,"schema":1}', b'[]', b'not-json', b''):
        with pytest.raises(updates.UpdateLookupError):
            updates.parse_manifest(source)


@pytest.mark.parametrize('url', [
    'http://divine-hill-13fc.punzer4.workers.dev/',
    'https://divine-hill-13fc.punzer4.workers.dev/latest.json',
    'https://divine-hill-13fc.punzer4.workers.dev/?source=private',
    'https://divine-hill-13fc.punzer4.workers.dev/#x',
    'https://evil.example/',
    'https://kemenkeu-my.sharepoint.com/',
    'https://divine-hill-13fc.punzer4.workers.dev.evil.example/',
])
def test_only_exact_owned_worker_endpoint_accepted(url):
    with pytest.raises(updates.UpdateLookupError):
        updates.validate_url(url)
    assert updates.validate_url(URL) == URL


def test_fetch_uses_named_user_agent_and_capped_timeout():
    opener = FakeOpener(FakeResponse(manifest()))
    result = updates.fetch_notice(URL, LOCAL, opener=opener)
    assert result.commit == REMOTE['commit']
    req, timeout = opener.calls[0]
    assert req.full_url == URL
    assert req.get_header('User-agent') == 'SPTDownloader-UpdateCheck/1.0'
    assert req.get_header('Accept') == 'application/json'
    assert timeout == updates.HTTP_TIMEOUT_SECONDS


@pytest.mark.parametrize('response', [
    FakeResponse(manifest(), status=403, content_type='text/html'),
    FakeResponse(manifest(), url='https://evil.example/'),
    FakeResponse(manifest(), content_type='text/html'),
    FakeResponse(b'x' * (updates.MAX_BYTES + 1)),
    FakeResponse(b'<html>blocked by Fortinet</html>'),
    FakeResponse(b''),
])
def test_untrusted_blocked_or_empty_response_refuses_notification(response):
    with pytest.raises(updates.UpdateLookupError):
        updates.fetch_notice(URL, LOCAL, opener=FakeOpener(response))


def test_unknown_local_build_never_performs_network_access():
    opener = FakeOpener(FakeResponse(manifest()))
    assert updates.fetch_notice(URL, None, opener=opener) is None
    assert not opener.calls


def test_non_installing_manifest_has_no_remote_link():
    remote = dict(REMOTE, download_url='https://untrusted.test/file.exe')
    with pytest.raises(updates.UpdateLookupError):
        updates.parse_manifest(json.dumps(remote).encode('utf-8'))
