"""Mode validation and GUI import boundaries; synthetic runner processes only."""
import subprocess
import sys

import pytest


def test_gui_import_does_not_require_tax_adapter_or_worker_dependencies():
    script = '''
import importlib.abc
import sys

blocked = ('coretax', 'coretax_json', 'coretax_browser', 'coretax_exporter',
           'spt_desktop.worker', 'playwright', 'openpyxl')
class RefuseBackend(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == root or fullname.startswith(root + '.') for root in blocked):
            raise AssertionError('GUI imported a backend dependency: ' + fullname)
sys.meta_path.insert(0, RefuseBackend())
from spt_desktop import app, controller
assert app.validate_detail_source is controller.validate_detail_source
assert controller.validate_detail_source('dom') == 'dom'
assert controller.validate_detail_source('json-first') == 'json-first'
assert not any(root in sys.modules for root in blocked)
'''
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_legacy_and_consumer_validator_names_keep_one_object():
    import coretax_browser
    import coretax_json
    import coretax_resume
    from spt_desktop import app, controller, worker

    expected = coretax_json.validate_detail_source
    assert all(module.validate_detail_source is expected
               for module in (coretax_browser, coretax_resume, app, controller, worker))


@pytest.mark.parametrize('value', ['dom', 'json-first'])
def test_literal_mode_returns_the_original_string(value):
    from coretax_json import validate_detail_source

    assert validate_detail_source(value) is value


@pytest.mark.parametrize('value', ['', 'DOM', 'JSON-FIRST', ' dom ', None, True, 1, {}, ['dom']])
def test_invalid_mode_retains_the_exact_error(value):
    from coretax_json import validate_detail_source

    with pytest.raises(ValueError) as error:
        validate_detail_source(value)
    assert str(error.value) == 'Detail source must be dom or json-first.'


def test_validator_refuses_subclasses_and_coercion_without_using_them():
    from coretax_json import validate_detail_source

    class UntrustedString(str):
        def __eq__(self, other):
            raise AssertionError('Mode must not compare a string subclass')

    class Untrusted:
        def __str__(self):
            raise AssertionError('Mode must not coerce an object')
        def __eq__(self, other):
            raise AssertionError('Mode must not compare an object')

    for value in (UntrustedString('dom'), Untrusted()):
        with pytest.raises(ValueError, match='^Detail source must be dom or json-first\\.$'):
            validate_detail_source(value)


def test_controller_still_uses_its_local_validator_patch_before_worker_launch(tmp_path, monkeypatch):
    from spt_desktop import controller

    class Refusal(ValueError):
        pass

    seen = []
    def refuse(value):
        seen.append(value)
        raise Refusal('Synthetic mode refusal')
    def unexpected_launch(*args, **kwargs):
        pytest.fail('Invalid mode reached worker launch')

    job = controller.JobController(tmp_path, lambda event: None)
    monkeypatch.setattr(controller, 'validate_detail_source', refuse)
    monkeypatch.setattr(job, '_start_worker', unexpected_launch)
    with pytest.raises(Refusal, match='Synthetic mode refusal'):
        job.start('0000000000000001', '2025', detail_source='json-first')
    assert seen == ['json-first'] and job.active is False
