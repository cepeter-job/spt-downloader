"""Desktop default changes without migrating a user's explicit DOM choice."""
import inspect
import json
import pytest
from spt_desktop.app import DEFAULTS, load_preferences, save_preferences
from spt_desktop.worker import run_job
from coretax_browser import collect_details, read_detail_checkpoint


@pytest.mark.parametrize('raw',[None,'{}','not-json','[]','{"detail_source":"invalid"}',
                               '{"detail_source":null}','{"detail_source":true}'])
def test_new_missing_or_invalid_desktop_preference_defaults_to_json_hybrid(tmp_path,raw):
    if raw is not None:(tmp_path/'preferences.json').write_text(raw,encoding='utf-8')
    assert load_preferences(tmp_path)['detail_source']=='json-first'
    assert DEFAULTS['detail_source']=='json-first'


@pytest.mark.parametrize('mode',['dom','json-first'])
def test_saved_mode_survives_load_save_and_reload(tmp_path,mode):
    (tmp_path/'preferences.json').write_text(json.dumps({'detail_source':mode}),encoding='utf-8')
    preferences=load_preferences(tmp_path)
    assert preferences['detail_source']==mode
    save_preferences(tmp_path,preferences)
    assert load_preferences(tmp_path)['detail_source']==mode


def test_save_without_mode_uses_new_desktop_default(tmp_path):
    save_preferences(tmp_path,{})
    assert load_preferences(tmp_path)['detail_source']=='json-first'


def test_library_worker_and_checkpoint_implicit_dom_contracts_remain_compatible():
    for function in (run_job,collect_details,read_detail_checkpoint):
        assert inspect.signature(function).parameters['detail_source'].default=='dom'
