"""Real negative-L7 + L10-B final-fence regressions; hosted execution only."""
import json

import pytest
from playwright.sync_api import JSHandle

import coretax_corporate as observer
import coretax_corporate_projection as projection
from coretax_json import JsonSafetyError, adapt_corporate_detail, has_audit_dump_tables
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l7_observer_fixture import Fixture as L7Fixture, mutate
from test_corporate_l1d_observer import open_selected
from test_corporate_l7_negative_observer import observe
from test_corporate_l10b_nondisplay import KEYS
from test_json_hybrid_native import browser as browser
import support_json_corpus as corpus


class Fixture(L7Fixture):
    def __init__(self, browser, monkeypatch):
        super().__init__(browser, monkeypatch)
        value = json.loads(self.raw, parse_int=corpus.Number, parse_float=corpus.Number)
        root = json.loads(value['Payload']['CurrentFormData'],
                          parse_int=corpus.Number, parse_float=corpus.Number)
        root['L10bFormData'] = dict.fromkeys(KEYS, False)
        root['MainFormData']['IsTransactionWithRelated'] = corpus.Number('1')
        value['Payload']['IsTransactionWithRelated'] = corpus.Number('1')
        value['Payload']['CurrentFormData'] = corpus.wire(root)
        self.raw = corpus.wire(value).encode()
        monkeypatch.setattr(projection, 'load_build_pins', lambda: dict(self.pins))

    def detail(self):
        markup = super().detail()
        index = list(observer.FORMS).index('L10-B')
        disabled = '<li class="p-disabled"><a role="tab" aria-controls="panel-' + str(index) + '"'
        assert disabled in markup
        markup = markup.replace(disabled, disabled.replace(' class="p-disabled"', ''))
        empty = ('<div class="p-tabview-panel" role="tabpanel" id="panel-' + str(index)
                 + '" style="display:none"></div>')
        assert empty in markup
        return markup.replace(empty, empty.replace('</div>',
            '<rshshr-citr-l10b-form style="display:block"><span>SYNTHETIC STRUCTURE</span>'
            '</rshshr-citr-l10b-form></div>'))


@pytest.mark.parametrize('window', ['unchanged', 'l10b', 'l7', 'parent-after-l7'])
def test_final_dual_profile_snapshot_never_seals_a_stale_sibling(
        browser, tmp_path, monkeypatch, window):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observe(fixture, capture)
            assert forms is not None
            assert any('raw_negative_projection' in form for form in forms)
            assert next(f for f in forms if f['name'] == 'L10-B')['projection']['kind'] == projection.L10B_KIND
            assert capture._l7_requested and capture._l10b_requested
            requests_before = list(fixture.requests)
            # Document is an ElementHandle, histories are plain JSHandles.
            # Patch their shared base, not only the Document subclass.
            original = JSHandle.evaluate
            fired, l7_sampled = [], []

            def evaluate(handle, expression, arg=None):
                # Old separate RPC path injects immediately before the real B
                # sample (or inverse/last parent probe), with no network event.
                # Coordinated path injects queued work before its ONE final RPC;
                # synchronous history samples cannot pump another browser turn.
                final = 'corporate-final-lifetimes' in expression
                sample = 'h.sample()' in expression
                trigger = (window == 'l10b' and handle is capture._l10b_history and sample
                    or window == 'l7' and handle is capture._l7_history and sample
                    or window == 'parent-after-l7' and l7_sampled and handle is capture._component_document)
                if window != 'unchanged' and not fired and (trigger or final):
                    fired.append(window)
                    victim = 'rshshr-citr-l10b-form' if window == 'l7' else 'rshshr-citr-l7-form'
                    guard = capture._l10b_history if window == 'l7' else capture._l7_history
                    try:
                        mutate(page, victim, 'remove-reinsert')
                        changed = original(guard, '(h) => h.sample()')
                    except Exception:
                        # Probe wrappers deliberately swallow driver errors;
                        # a broken injection MUST fail outside that policy.
                        pytest.fail('Real structural mutation injection failed')
                    if changed.get('changed') is not True:
                        pytest.fail('Real history did not witness the injected mutation')
                result = original(handle, expression, arg)
                if handle is capture._l7_history and sample:
                    l7_sampled.append(True)
                return result

            monkeypatch.setattr(JSHandle, 'evaluate', evaluate)
            assert all(handle.evaluate.__func__ is evaluate for handle in (
                capture._component_document, capture._l7_history, capture._l10b_history))
            if window != 'unchanged':
                with pytest.raises(JsonSafetyError, match='child history changed'):
                    capture.drain()
                assert fired == [window]
                assert not list(tmp_path.rglob('manifest.json'))
            else:
                saved = capture.drain()
                assert saved['complete']
                assert saved['corporate_l7_lifetime']['stable_table'] is True
                assert saved['corporate_l10b_lifetime']['stable_form'] is True
                packets = list(capture.iter_bodies())
                fixture.record['detail_url'] = page.url
                assert checkpoint_bodies(tmp_path, saved, fixture.record, corpus.SCOPE) == packets
                result = adapt_corporate_detail(packets, fixture.record, corpus.SCOPE, forms)
                assert result['eligible'], result['reason']
                assert not has_audit_dump_tables(result['sections'], provenance=result['provenance'])
            assert fixture.requests == requests_before and fixture.unexpected == []
            assert page.evaluate('window.businessReads') == 0
    finally:
        fixture.close()
