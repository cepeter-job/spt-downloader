"""Owned synthetic Edge UI only; no live accounts, endpoints or captured values."""
from math import ceil

import pytest

import coretax_browser as driver
from spt_desktop import diagnostics as d
from support_isolated_browser import browser as browser, context as context
from test_diagnostics import records


CAPTION = 'B. PPh YANG DIPOTONG/DIPUNGUT PIHAK LAIN'
COMPONENT = 'rshshr-citr-l3-grid2'
FORM = 'rshshr-citr-l3-form'


@pytest.fixture
def page(context):
    owned = context.new_page()
    owned.route('**/*', lambda route: route.abort())
    owned.set_default_timeout(500)
    return owned


def fixture(page, *, total=4654, sizes=(10, 25, 50, 100, 250, 500), selected=100,
            component=COMPONENT, caption=CAPTION, form=FORM, tab='L3', reported=None):
    # DOM installation is test setup, not a capture readiness condition.
    # On a loaded Windows shard it can exceed the 500 ms locator/action bound.
    page.set_content('''<main class="main-content"><div class="p-tabview">
      <ul class="p-tabview-nav"><li><a role="tab" aria-controls="l3">L3</a></li></ul>
      <div class="p-tabview-panels"><p-tabpanel><div class="p-tabview-panel" id="l3">
      <rshshr-citr-l3-form><p-accordiontab><div class="p-accordion-header"><a></a></div>
      <div class="p-accordion-content"><rshshr-citr-l3-grid2>
      <p-table><div class="p-datatable"><table><thead><tr><th>Ordinal</th><th>Value</th></tr></thead>
      <tbody></tbody><tfoot><tr><td>TOTAL</td><td>0</td></tr></tfoot></table>
      <div class="p-paginator"><button class="p-paginator-first" type="button">First</button>
      <span class="p-paginator-page p-highlight"></span>
      <button class="p-paginator-next" type="button">Next</button><span class="p-paginator-current"></span>
      <div class="p-paginator-rpp-options"><span class="p-dropdown-label"></span>
      <button class="p-dropdown-trigger" type="button">Size</button></div></div></div></p-table>
      </rshshr-citr-l3-grid2></div></p-accordiontab></rshshr-citr-l3-form>
      </div></p-tabpanel></div></div></main><ul class="p-dropdown-items" hidden></ul>
      <script>(()=>{
      window.at=0;window.moves=0;window.sizeChanges=[];window.noAdvance=false;
      window.draw=()=>{
        document.querySelector('tbody').innerHTML=Array.from(
          {length:Math.min(size,total-at*size)},(_,i)=>'<tr><td>'+String(Math.floor((at*size+i)/2)+1)+
          '</td><td>0</td></tr>').join('');
        document.querySelector('.p-highlight').textContent=String(at+1);
        document.querySelector('.p-paginator-first').disabled=at===0;
        document.querySelector('.p-paginator-next').disabled=(at+1)*size>=total;
        document.querySelector('.p-paginator-current').textContent='Showing '+(at*size+1)+' of '+reported+' entries';
        document.querySelector('.p-dropdown-label').textContent=String(size);
      };
      document.querySelector('.p-paginator-first').onclick=()=>{moves++;at=0;draw();};
      document.querySelector('.p-paginator-next').onclick=()=>{moves++;if(!noAdvance){at++;draw();}};
      const options=document.querySelector('.p-dropdown-items');
      document.querySelector('.p-dropdown-trigger').onclick=()=>options.hidden=false;
      document.addEventListener('keydown',e=>{if(e.key==='Escape')options.hidden=true;});
      window.configure=(c)=>{
        window.total=c.total;window.reported=c.reported;window.size=c.selected;
        options.innerHTML=c.sizes.map(n=>'<li>'+n+'</li>').join('');
        options.querySelectorAll('li').forEach(li=>li.onclick=()=>{
          sizeChanges.push(Number(li.textContent));size=Number(li.textContent);at=0;
          options.hidden=true;draw();
        });
        document.querySelector('[role=tab]').textContent=c.tab;
        document.querySelector('.p-accordion-header a').textContent=c.caption;
        const rename=(selector,name)=>{
          const old=document.querySelector(selector),replacement=document.createElement(name);
          replacement.append(...old.childNodes);old.replaceWith(replacement);
        };
        rename('rshshr-citr-l3-grid2',c.component);rename('rshshr-citr-l3-form',c.form);draw();
      };
      })();</script>''', wait_until='domcontentloaded', timeout=10000)
    page.evaluate('c=>configure(c)', dict(total=total, sizes=list(sizes), selected=selected,
                  component=component, caption=caption, form=form, tab=tab,
                  reported=total if reported is None else reported))
    return page.locator('table')


def capture(page, **kwargs):
    return driver.capture_detail(page, record={'meta': {'Jenis Pajak': 'PPh Badan'}}, **kwargs)


def captured_table(result):
    table = result['sections'][0]['tables'][0]
    # This fixture intentionally has no Induk/PDF; table success never certifies a job.
    assert not result['capture_complete']
    assert result['attachments'][0]['status'] == 'PARTIAL'
    return table


def assert_rows(table, total):
    assert table['complete'], table.get('warning')
    assert table['source_total'] == table['body_row_count'] == total
    assert table['rows'] == [[str(i // 2 + 1), '0'] for i in range(total)] + [['TOTAL', '0']]
    assert table['footer'] == [['TOTAL', '0']]
    assert 'source_structure' not in table  # No new output/eligibility declaration.


def test_corporate_l3_b_4654_rows_cap_at_500_without_losing_rows_or_footer(page):
    fixture(page)
    captured = captured_table(capture(page))
    assert captured['pages'] == 10
    assert_rows(captured, 4654)
    assert page.evaluate('({sizeChanges,moves,size})') == {'sizeChanges': [500], 'moves': 9, 'size': 500}
    # A previous 1000-row selection must be downsized via the inspected UI.
    table = fixture(page, sizes=(10, 25, 50, 100, 250, 500, 1000), selected=1000)
    reduced = driver.capture_table(page, table, 1, max_pages=1000, max_page_size=500)
    assert_rows(reduced, 4654)
    assert reduced['pages'] == 10
    assert page.evaluate('({sizeChanges,moves,size})') == {'sizeChanges': [500], 'moves': 9, 'size': 500}
    assert captured['rows'] == reduced['rows']


@pytest.mark.parametrize('sizes,selected,chosen,changes', [
    ((10, 100, 250, 500, 1000), 100, 500, [500]),
    ((10, 100, 250), 100, 250, [250]),
    ((10, 100, 250), 250, 250, []),
    ((10, 100), 100, 100, []),
    ((10, 100, 500, 1000), 1000, 500, [500]),
])
def test_corporate_size_uses_only_available_bounded_options_and_avoids_reload(page, sizes, selected, chosen, changes):
    fixture(page, total=601, sizes=sizes, selected=selected)
    result = captured_table(capture(page))
    assert_rows(result, 601)
    assert result['pages'] == ceil(601 / chosen)
    assert page.evaluate('sizeChanges') == changes
    assert page.locator('.p-dropdown-items').is_hidden()


def test_guarded_500_cap_refuses_unbounded_current_ui_option(page):
    table = fixture(page, total=1001, sizes=(1000,), selected=1000)
    with pytest.raises(RuntimeError, match='page size'):
        driver.capture_table(page, table, 1, max_pages=1000, max_page_size=500)
    assert page.evaluate('({sizeChanges,moves,size})') == {
        'sizeChanges': [], 'moves': 0, 'size': 1000}


@pytest.mark.parametrize('override', [
    {'component': 'unknown-grid'},
    {'caption': 'OTHER GROUP'},
    {'component': 'rsh-citr-l3-grid1', 'caption': 'A. PENGHASILAN DARI LUAR NEGERI'},
    {'form': 'foreign-form'},
    {'tab': 'L4'},
])
def test_unproved_or_other_corporate_table_keeps_existing_hundred_row_cap(page, override):
    fixture(page, total=201, **override)
    result = captured_table(capture(page))
    assert_rows(result, 201)
    assert result['pages'] == 3
    assert page.evaluate('sizeChanges') == []


@pytest.mark.parametrize('record', [None, {'meta': {'Jenis Pajak': 'PPh Pasal 21/26'}}])
def test_noncorporate_detail_keeps_existing_hundred_row_cap(page, record):
    fixture(page, total=201)
    result = driver.capture_detail(page, record=record)
    table = result['sections'][0]['tables'][0]
    assert_rows(table, 201)
    assert table['pages'] == 3
    assert page.evaluate('sizeChanges') == []


def test_large_page_capture_preserves_partial_count_and_page_limit(page):
    fixture(page, total=601)
    limited = captured_table(capture(page, max_pages=1))
    assert not limited['complete'] and limited['pages'] == 1
    assert limited['body_row_count'] == 500 and limited['source_total'] == 601
    assert page.evaluate('moves') == 0
    fixture(page, total=601, reported=602)
    mismatch = captured_table(capture(page))
    assert not mismatch['complete'] and mismatch['body_row_count'] == 601
    assert mismatch['source_total'] == 602


def test_large_page_capture_stop_after_first_move_propagates(page):
    fixture(page, total=1201)

    def stop():
        if page.evaluate('moves'):
            raise driver.CaptureCancelled('synthetic stop')

    with pytest.raises(driver.CaptureCancelled):
        capture(page, check_cancel=stop)
    assert page.evaluate('sizeChanges') == [500]
    assert page.evaluate('moves') == 1


def test_large_dom_reset_timings_attribute_first_and_previous_without_extra_clicks(
        page, tmp_path, monkeypatch):
    from playwright.sync_api import ElementHandle

    table = fixture(page, total=601, selected=500)
    real_query = ElementHandle.query_selector
    real_handle = ElementHandle.evaluate_handle
    real_evaluate = ElementHandle.evaluate
    calls = {'owned': 0, 'legacy': 0, 'final_limit': 0}
    selector = '.p-paginator-prev:not([disabled]):not(.p-disabled)'

    def track_query(self, value):
        if value == selector:
            calls['legacy'] += 1
        return real_query(self, value)

    def track_handle(self, expression, arg=None):
        if expression == driver.OWNED_PREVIOUS_CONTROL_JS:
            assert arg == selector
            calls['owned'] += 1
        return real_handle(self, expression, arg)

    def track_evaluate(self, expression, arg=None):
        if expression == driver.OWNED_PREVIOUS_PRESENT_JS:
            assert arg == selector
            calls['final_limit'] += 1
        return real_evaluate(self, expression, arg)

    monkeypatch.setattr(ElementHandle, 'query_selector', track_query)
    monkeypatch.setattr(ElementHandle, 'evaluate_handle', track_handle)
    monkeypatch.setattr(ElementHandle, 'evaluate', track_evaluate)
    # Synthetic page: First legitimately lands on page 3 and the existing
    # inspected Previous fallback must restore page 1. Never skip source pages.
    page.evaluate("""() => {
        const first = document.querySelector('.p-paginator-first');
        const prev = document.createElement('button');
        prev.className = 'p-paginator-prev';
        prev.textContent = 'Previous';
        first.after(prev);
        const previousDraw = window.draw;
        window.draw = () => { previousDraw(); prev.disabled = at === 0; };
        first.onclick = () => { moves++; at = 2; draw(); };
        prev.onclick = () => { moves++; at--; draw(); };
        at = 4;
        draw();
    }""")
    with d.session(tmp_path, 'worker') as log:
        captured = driver.capture_table(page, table, 3, 100, max_page_size=500)
        assert log.flush()
    assert_rows(captured, 601)
    assert captured['pages'] == 2
    # First (one), Previous (two), Next (one) are the original required actions.
    assert page.evaluate('moves') == 4
    # Two Previous controls + final absent probe, without extra handle lookup.
    assert calls == {'owned': 3, 'legacy': 0, 'final_limit': 1}
    rows = [row for row in records(tmp_path) if row['event'] == 'table.reset_timing']
    steps = {row['table_reset_step']: row for row in rows}
    assert set(steps) == {'size_action', 'pilot_guard', 'first_lookup',
                          'first_click', 'first_idle', 'first_navigation',
                          'previous_stop_check', 'previous_lookup',
                          'previous_state', 'previous_click',
                          'previous_idle', 'previous_verify',
                          'previous_limit_lookup', 'previous_rewind',
                          'total_pre_read'}
    assert steps['previous_stop_check']['count'] == 3
    assert steps['previous_lookup']['count'] == 3
    assert steps['previous_state']['count'] == 2
    assert steps['previous_click']['count'] == 2
    assert steps['previous_idle']['count'] == 2
    assert steps['previous_verify']['count'] == 2
    assert steps['previous_limit_lookup']['count'] == 1
    assert steps['pilot_guard']['count'] == 1
    assert steps['first_lookup']['count'] == 1
    assert steps['first_click']['count'] == 1
    assert steps['first_idle']['count'] == 1
    assert steps['first_navigation']['count'] == 1
    assert steps['first_navigation']['duration_ms'] >= steps['first_idle']['duration_ms']
    assert steps['previous_rewind']['count'] == 2
    assert steps['previous_rewind']['duration_ms'] > 0
    assert steps['total_pre_read']['duration_ms'] >= steps['previous_rewind']['duration_ms']
    assert all(row['form_ordinal'] == 1 and row['table_ordinal'] == 3 for row in rows)
    assert all(set(row).isdisjoint({'url', 'body', 'marker', 'table_text'}) for row in rows)


def test_large_dom_first_click_stop_preserves_cancel_and_zero_click_timing(
        page, tmp_path, monkeypatch):
    table = fixture(page, total=601, selected=500)
    page.evaluate('at=1; draw()')

    def cancel_during_first_click(_control, _container, _check_cancel):
        raise driver.CaptureCancelled('synthetic stop during First click')

    monkeypatch.setattr(driver, '_click_table_paginator', cancel_during_first_click)
    with d.session(tmp_path, 'worker') as log:
        with pytest.raises(driver.CaptureCancelled,
                           match='synthetic stop during First click'):
            driver.capture_table(page, table, 3, 100, max_page_size=500)
        assert log.flush()

    assert page.evaluate('moves') == 0
    events = records(tmp_path)
    reset_events = [row for row in events
                    if row['event'] == 'table.reset_timing']
    steps = {row['table_reset_step']: row for row in reset_events}
    assert set(steps) == {'size_action', 'pilot_guard', 'first_lookup',
                          'first_click', 'first_navigation'}
    assert steps['first_lookup']['count'] == 1
    assert steps['first_click']['count'] == 0
    assert steps['first_navigation']['count'] == 0
    assert all(row['duration_ms'] >= 0 for row in reset_events)
    assert not any(row['event'] == 'table.page_timing' for row in events)


def test_large_dom_first_idle_timeout_preserves_original_failure_and_timing(
        page, tmp_path, monkeypatch):
    table = fixture(page, total=601, selected=500)
    page.evaluate('at=1; draw()')
    def original_wait_times_out(_page):
        raise driver.PlaywrightTimeoutError('synthetic first idle timeout')

    monkeypatch.setattr(driver, 'wait_idle', original_wait_times_out)
    with d.session(tmp_path, 'worker') as log:
        with pytest.raises(driver.PlaywrightTimeoutError):
            driver.capture_table(page, table, 3, 100, max_page_size=500)
        assert log.flush()
    # No retry, Previous, Next, DOM snapshot or altered source acceptance.
    assert page.evaluate('moves') == 1
    records_for_reset = [row for row in records(tmp_path)
                         if row['event'] == 'table.reset_timing']
    steps = {row['table_reset_step']: row for row in records_for_reset}
    assert set(steps) == {'size_action', 'pilot_guard', 'first_lookup',
                          'first_click', 'first_idle', 'first_navigation'}
    assert steps['first_idle']['count'] == 1
    assert steps['first_navigation']['count'] == 1
    assert steps['first_navigation']['duration_ms'] >= steps['first_idle']['duration_ms']
    assert not any(row['event'] == 'table.page_timing'
                   for row in records(tmp_path))
    assert all('error' not in row for row in records_for_reset)


def test_small_dom_table_does_not_emit_large_reset_diagnostics(page, tmp_path):
    table = fixture(page, total=101, selected=100)
    with d.session(tmp_path, 'worker') as log:
        captured = driver.capture_table(page, table, 1, 100, max_page_size=100)
        assert log.flush()
    assert_rows(captured, 101)
    assert not [r for r in records(tmp_path) if r['event'] == 'table.reset_timing']


def test_large_dom_zero_previous_clicks_attributes_lookup_without_retry(
        page, tmp_path):
    table = fixture(page, total=601, selected=500)
    # First is disabled on page 1 and the synthetic table has no Previous.
    with d.session(tmp_path, 'worker') as log:
        result = driver.capture_table(page, table, 3, 100, max_page_size=500)
        assert log.flush()
    assert_rows(result, 601)
    assert page.evaluate('moves') == 1  # The original Next only.
    events = records(tmp_path)
    timing = {row['table_reset_step']: row for row in events
              if row['event'] == 'table.reset_timing'}
    assert timing['previous_rewind']['count'] == 0
    assert timing['previous_stop_check']['count'] == 1
    assert timing['previous_lookup']['count'] == 1
    assert timing['previous_limit_lookup']['count'] == 1
    assert set(timing).isdisjoint({'previous_state', 'previous_click',
                                   'previous_idle', 'previous_verify'})
    assert timing['previous_rewind']['duration_ms'] >= timing['previous_lookup']['duration_ms']


@pytest.mark.parametrize('limit,expected_legacy,expected_owned', [
    (500, 0, 1),  # No handle lookup or extra probe on the large-table path.
    (100, 2, 0),  # Small DOM tables retain their two original lookups.
])
def test_absent_previous_uses_one_owned_lookup_and_bounded_final_check(
        page, monkeypatch, limit, expected_legacy, expected_owned):
    from playwright.sync_api import ElementHandle

    table = fixture(page, total=601, selected=100)
    old_query = ElementHandle.query_selector
    old_eval_handle = ElementHandle.evaluate_handle
    old_evaluate = ElementHandle.evaluate
    old_dispose = driver._dispose_table_handle
    legacy_queries, owned_handles, final_checks, disposed = [], [], [], []
    selector = '.p-paginator-prev:not([disabled]):not(.p-disabled)'

    def track_query(self, value):
        if value == selector:
            legacy_queries.append(value)
        return old_query(self, value)

    def track_handle(self, expression, arg=None):
        result = old_eval_handle(self, expression, arg)
        if expression == driver.OWNED_PREVIOUS_CONTROL_JS:
            assert arg == selector
            owned_handles.append(result)
        return result

    def track_evaluate(self, expression, arg=None):
        if expression == driver.OWNED_PREVIOUS_PRESENT_JS:
            assert arg == selector
            final_checks.append(arg)
        return old_evaluate(self, expression, arg)

    def track_dispose(handle):
        if any(handle is item for item in owned_handles):
            disposed.append(handle)
        return old_dispose(handle)

    monkeypatch.setattr(ElementHandle, 'query_selector', track_query)
    monkeypatch.setattr(ElementHandle, 'evaluate_handle', track_handle)
    monkeypatch.setattr(ElementHandle, 'evaluate', track_evaluate)
    monkeypatch.setattr(driver, '_dispose_table_handle', track_dispose)
    result = driver.capture_table(page, table, 3, 100, max_page_size=limit)
    assert_rows(result, 601)
    assert len(legacy_queries) == expected_legacy
    assert len(owned_handles) == expected_owned
    assert len(disposed) == expected_owned
    assert len(final_checks) == (1 if limit >= 250 else 0)
    assert page.evaluate('moves') == ceil(601 / limit) - 1


def test_large_previous_owned_handle_refuses_disappearing_control_before_click(
        page, monkeypatch):
    table = fixture(page, total=601, selected=500)
    page.evaluate("""() => {
        const first = document.querySelector('.p-paginator-first');
        const previous = document.createElement('button');
        previous.className = 'p-paginator-prev';
        first.after(previous);
    }""")
    original = driver._click_table_paginator
    original_dispose = driver._dispose_table_handle
    disposed = []

    def disappear_before_click(control, container, check_cancel):
        if control.evaluate("(e)=>e.matches('.p-paginator-prev')"):
            page.evaluate("document.querySelector('.p-paginator-prev').remove()")
        return original(control, container, check_cancel)

    def tracked_dispose(handle):
        disposed.append(handle)
        return original_dispose(handle)

    monkeypatch.setattr(driver, '_click_table_paginator', disappear_before_click)
    monkeypatch.setattr(driver, '_dispose_table_handle', tracked_dispose)
    with pytest.raises(RuntimeError, match='Unavailable or unsupported pagination control'):
        driver.capture_table(page, table, 3, 100, max_page_size=500)
    assert page.evaluate('moves') == 0  # Neither speculative click nor retry.
    assert len(disposed) >= 3  # Original table, owner and owned Previous.


def test_large_previous_probe_rejects_nested_foreign_control(page):
    table = fixture(page, total=601, selected=500)
    page.evaluate("""() => {
        const foreign = document.createElement('p-table');
        const previous = document.createElement('button');
        previous.className = 'p-paginator-prev';
        foreign.append(previous);
        document.querySelector('p-table').append(foreign);
    }""")
    # A nested paginator may match the selector, but cannot belong to
    # the original owner. The old guarded click must still reject it.
    with pytest.raises(RuntimeError, match='Unavailable or unsupported pagination control'):
        driver.capture_table(page, table, 3, 100, max_page_size=500)
    assert page.evaluate('moves') == 0


def test_large_previous_owned_handle_disappearing_at_panel_omits_table(
        page, monkeypatch):
    fixture(page, total=601, selected=500)
    page.evaluate("""() => {
        const first = document.querySelector('.p-paginator-first');
        const previous = document.createElement('button');
        previous.className = 'p-paginator-prev';
        first.after(previous);
    }""")
    original = driver._click_table_paginator

    def disappear_before_click(control, container, check_cancel):
        if control.evaluate("(e)=>e.matches('.p-paginator-prev')"):
            page.evaluate("document.querySelector('.p-paginator-prev').remove()")
        return original(control, container, check_cancel)

    monkeypatch.setattr(driver, '_click_table_paginator', disappear_before_click)
    result = capture(page)
    assert not result['capture_complete']
    assert result['sections'][0]['tables'] == []
    assert any(e['message'] == 'capture_failed' and
               e['object'] == 'L3/table 1' for e in result['errors'])
    assert page.evaluate('moves') == 0


def test_large_previous_owned_lookup_rejects_detached_owner(page):
    from playwright.sync_api import Error as PlaywrightError

    table = fixture(page, total=601, selected=500)
    owner = table.element_handle().evaluate_handle(
        "e=>e.closest('p-table')")
    try:
        page.evaluate("document.querySelector('p-table').remove()")
        with pytest.raises(PlaywrightError):
            owner.evaluate_handle(driver.OWNED_PREVIOUS_CONTROL_JS,
                                  '.p-paginator-prev:not([disabled]):not(.p-disabled)')
        with pytest.raises(PlaywrightError):
            owner.evaluate(driver.OWNED_PREVIOUS_PRESENT_JS,
                           '.p-paginator-prev:not([disabled]):not(.p-disabled)')
    finally:
        owner.dispose()


def test_large_previous_owned_handle_disposed_on_cancel(page, monkeypatch):
    from playwright.sync_api import ElementHandle

    table = fixture(page, total=601, selected=500)
    page.evaluate("""() => {
        const first = document.querySelector('.p-paginator-first');
        const prev = document.createElement('button');
        prev.className = 'p-paginator-prev';
        first.after(prev);
        const drawOriginal = window.draw;
        window.draw = () => {drawOriginal();prev.disabled = at === 0;};
        first.onclick = () => {moves++;at=2;draw();};
        prev.onclick = () => {moves++;at--;draw();};
        at=4;draw();
    }""")
    old_eval_handle = ElementHandle.evaluate_handle
    old_dispose = driver._dispose_table_handle
    old_click = driver._click_table_paginator
    owned, disposed = [], []

    def track_handle(self, expression, arg=None):
        h = old_eval_handle(self, expression, arg)
        if expression == driver.OWNED_PREVIOUS_CONTROL_JS:
            owned.append(h)
        return h

    def track_dispose(h):
        if any(h is x for x in owned):
            disposed.append(h)
        return old_dispose(h)

    def stop_during_previous_click(control, container, check_cancel):
        if control.evaluate("(e)=>e.matches('.p-paginator-prev')"):
            raise driver.CaptureCancelled('synthetic stop before Previous click')
        return old_click(control, container, check_cancel)

    monkeypatch.setattr(ElementHandle, 'evaluate_handle', track_handle)
    monkeypatch.setattr(driver, '_dispose_table_handle', track_dispose)
    monkeypatch.setattr(driver, '_click_table_paginator', stop_during_previous_click)
    with pytest.raises(driver.CaptureCancelled, match='synthetic stop before Previous click'):
        driver.capture_table(page, table, 3, 100, max_page_size=500)
    assert page.evaluate('moves') == 1  # First dispatched, no Previous click.
    assert len(owned) == len(disposed) == 1


def test_large_previous_page_limit_retains_guard_with_owner_bool_lookup(page):
    table = fixture(page, total=1501, selected=500)
    page.evaluate("""() => {
        const first = document.querySelector('.p-paginator-first');
        const prev = document.createElement('button');
        prev.className = 'p-paginator-prev';
        first.after(prev);
        const drawOriginal=window.draw;
        window.draw=()=>{drawOriginal();prev.disabled=at===0;};
        first.onclick=()=>{moves++;at=2;draw();};
        prev.onclick=()=>{moves++;at--;draw();};
        at=2;draw();
    }""")
    with pytest.raises(RuntimeError, match='Table reset page limit 1 reached'):
        driver.capture_table(page, table, 3, max_pages=1, max_page_size=500)
    assert page.evaluate('moves') == 2  # First + bounded Previous only.


def test_large_dom_reset_stop_preserves_original_cancel_and_emits_bounded_elapsed(
        page, tmp_path):
    table = fixture(page, total=601, selected=500)
    page.evaluate("""() => {
        const first = document.querySelector('.p-paginator-first');
        const prev = document.createElement('button');
        prev.className = 'p-paginator-prev';
        first.after(prev);
        const drawOriginal = window.draw;
        window.draw = () => { drawOriginal(); prev.disabled = at === 0; };
        first.onclick = () => { moves++; at = 2; draw(); };
        prev.onclick = () => { moves++; at--; draw(); };
        at = 4;
        draw();
    }""")

    def cancel_after_first_previous():
        if page.evaluate('moves') >= 2:
            raise driver.CaptureCancelled('synthetic stop')

    with d.session(tmp_path, 'worker') as log:
        with pytest.raises(driver.CaptureCancelled):
            driver.capture_table(page, table, 3, 100,
                                 check_cancel=cancel_after_first_previous,
                                 max_page_size=500)
        assert log.flush()
    assert page.evaluate('moves') == 2
    timing = [row for row in records(tmp_path)
              if row['event'] == 'table.reset_timing']
    steps = {row['table_reset_step']: row for row in timing}
    assert steps['previous_rewind']['count'] == 1
    assert steps['previous_stop_check']['count'] == 2
    assert steps['previous_lookup']['count'] == 1
    assert steps['previous_click']['count'] == 1
    assert steps['previous_verify']['count'] == 1
    assert 'previous_limit_lookup' not in steps
    assert all(row['duration_ms'] >= 0 for row in timing)
