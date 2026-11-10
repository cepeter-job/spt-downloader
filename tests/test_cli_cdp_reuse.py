"""No-network regressions for explicit, profile-bound CLI CDP reuse."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coretax


def _profile(tmp_path, port=9235, browser_id='ABCDEF123456'):
    profile = tmp_path / 'dedicated-profile'
    profile.mkdir()
    (profile / 'DevToolsActivePort').write_text(
        f'{port}\n/devtools/browser/{browser_id}\n', encoding='ascii')
    return profile


class _Session:
    def __init__(self, arguments, *, error=None):
        self.arguments = arguments
        self.error = error
        self.detached = False

    def send(self, method):
        assert method == 'Browser.getBrowserCommandLine'
        if self.error is not None:
            raise self.error
        return self.arguments

    def detach(self):
        self.detached = True


class _Browser:
    def __init__(self, response, contexts=None, *, error=None):
        self.session = _Session(response, error=error)
        self.contexts = [object()] if contexts is None else contexts

    def new_browser_cdp_session(self):
        return self.session


@pytest.mark.parametrize('origin', [
    'https://localhost:9235', 'http://localhost', 'http://localhost/',
    'http://localhost:0', 'http://localhost:99999',
    'http://user:secret@localhost:9235', 'http://localhost:9235/path',
    'http://localhost:9235?x=1', 'http://localhost:9235#x',
    'http://0.0.0.0:9235', 'http://127.0.0.1.evil.invalid:9235',
    'file:///tmp/DevToolsActivePort',
])
def test_cdp_only_accepts_explicit_http_loopback_port(origin):
    with pytest.raises(ValueError):
        coretax.validate_debug_endpoint(origin)


@pytest.mark.parametrize('origin', [
    'http://127.0.0.1:9235', 'http://localhost:9235/',
    'http://[::1]:9235',
])
def test_cdp_accepts_explicit_loopback_port(origin):
    assert coretax.validate_debug_endpoint(origin) == origin


def test_reuse_option_never_defaults_to_port_9235():
    with pytest.raises(SystemExit) as error:
        coretax.parser().parse_args(['--reuse-browser'])
    assert error.value.code == 2
    assert coretax.parser().parse_args([]).reuse_browser is None


def test_cmd_does_not_probe_or_insert_reuse_option():
    script = (Path(__file__).resolve().parents[1] / 'run.cmd').read_text(encoding='utf-8').lower()
    assert 'json/version' not in script
    assert 'urlopen(' not in script
    assert 'if errorlevel 1 (' not in script
    assert 'coretax.py %*' in script
    assert '--reuse-browser http' not in script


def test_cdp_profile_requires_matching_ephemeral_port(tmp_path):
    profile = _profile(tmp_path)
    assert coretax.validate_cdp_profile('http://127.0.0.1:9235', profile) == profile.resolve()
    with pytest.raises(ValueError, match='does not match'):
        coretax.validate_cdp_profile('http://127.0.0.1:9999', profile)


@pytest.mark.parametrize('contents', [
    '', '9235\n', '9235\nnot-a-browser-path\n',
    'invalid\n/devtools/browser/ABCDEF123456\n',
    '9235\n/devtools/browser/short\n',
    '9235\n/devtools/browser/ABCDEF123456\nextra\n',
    'x' * 513,
])
def test_cdp_profile_rejects_untrusted_marker_contents(tmp_path, contents):
    profile = _profile(tmp_path)
    (profile / 'DevToolsActivePort').write_text(contents, encoding='ascii')
    with pytest.raises(ValueError):
        coretax.validate_cdp_profile('http://localhost:9235', profile)


def test_cdp_profile_without_marker_is_rejected_before_network(tmp_path):
    profile = tmp_path / 'dedicated-profile'
    profile.mkdir()
    with pytest.raises(ValueError, match='marker'):
        coretax.validate_cdp_profile('http://localhost:9235', profile)


def test_cdp_browser_requires_matching_profile_and_random_port(tmp_path):
    profile = _profile(tmp_path).resolve()
    context = object()
    browser = _Browser(
        {'arguments': ['msedge.exe', '--remote-debugging-port=0',
                       f'--user-data-dir={profile}']},
        contexts=[context])
    assert coretax.validate_cdp_browser(browser, profile) is context
    assert browser.session.detached


@pytest.mark.parametrize('arguments', [
    [],
    ['--remote-debugging-port=9235', '--user-data-dir={profile}'],
    ['--remote-debugging-port=0'],
    ['--remote-debugging-port=0', '--user-data-dir={other}'],
    ['--remote-debugging-port=0', '--user-data-dir=relative-profile'],
    ['--remote-debugging-port=0', '--user-data-dir={profile}',
     '--user-data-dir={profile}'],
])
def test_cdp_browser_rejects_wrong_launch_identity(tmp_path, arguments):
    profile = _profile(tmp_path).resolve()
    actual = [argument.format(profile=profile, other=tmp_path / 'personal-profile')
              for argument in arguments]
    browser = _Browser({'arguments': actual})
    with pytest.raises(ValueError, match='dedicated profile'):
        coretax.validate_cdp_browser(browser, profile)
    assert browser.session.detached


@pytest.mark.parametrize('response', [None, {}, {'arguments': 'not-a-list'}, {'arguments': [None]}])
def test_cdp_browser_rejects_misleading_metadata(tmp_path, response):
    profile = _profile(tmp_path).resolve()
    browser = _Browser(response)
    with pytest.raises(ValueError, match='evidence is missing'):
        coretax.validate_cdp_browser(browser, profile)
    assert browser.session.detached


@pytest.mark.parametrize('contexts', [[], [object(), object()]])
def test_cdp_browser_rejects_ambiguous_contexts(tmp_path, contexts):
    profile = _profile(tmp_path).resolve()
    browser = _Browser({'arguments': ['--remote-debugging-port=0',
                                       f'--user-data-dir={profile}']}, contexts=contexts)
    with pytest.raises(ValueError, match='exactly one'):
        coretax.validate_cdp_browser(browser, profile)
    assert browser.session.detached


def test_cdp_browser_rejects_unavailable_command_line(tmp_path):
    profile = _profile(tmp_path).resolve()
    browser = _Browser(None, error=RuntimeError('CDP method blocked'))
    with pytest.raises(ValueError, match='unavailable'):
        coretax.validate_cdp_browser(browser, profile)
    assert browser.session.detached
