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
        page, tmp_path):
    table = fixture(page, total=601, selected=500)
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
    rows = [row for row in records(tmp_path) if row['event'] == 'table.reset_timing']
    steps = {row['table_reset_step']: row for row in rows}
    assert set(steps) == {'size_action', 'first_navigation',
                          'previous_rewind', 'total_pre_read'}
    assert steps['first_navigation']['count'] == 1
    assert steps['previous_rewind']['count'] == 2
    assert steps['previous_rewind']['duration_ms'] > 0
    assert steps['total_pre_read']['duration_ms'] >= steps['previous_rewind']['duration_ms']
    assert all(row['form_ordinal'] == 1 and row['table_ordinal'] == 3 for row in rows)
    assert all(set(row).isdisjoint({'url', 'body', 'marker', 'table_text'}) for row in rows)


def test_small_dom_table_does_not_emit_large_reset_diagnostics(page, tmp_path):
    table = fixture(page, total=101, selected=100)
    with d.session(tmp_path, 'worker') as log:
        captured = driver.capture_table(page, table, 1, 100, max_page_size=100)
        assert log.flush()
    assert_rows(captured, 101)
    assert not [r for r in records(tmp_path) if r['event'] == 'table.reset_timing']


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
    assert any(row['table_reset_step'] == 'previous_rewind'
               and row['count'] == 1 for row in timing)
    assert all(row['duration_ms'] >= 0 for row in timing)
