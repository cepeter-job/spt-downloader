"""Selected PPN refund controls; synthetic DOM, no network or taxpayer data."""
import pytest
from support_isolated_browser import browser, isolated_context
import coretax_browser as driver
from support_templates import section
from support_templates import export_ppn

CHOICES = [('CARRY_FORWARD', '1. dikompensasikan'),
           ('FAST_REFUND', '2. dikembalikan melalui pengembalian pendahuluan'),
           ('FORWARD_REFUND', '3. dikembalikan melalui pemeriksaan')]


@pytest.mark.parametrize('selected', [None, 0, 1, 2])
@pytest.mark.parametrize('input_named', [False, True])
def test_only_checked_asked_to_option_reaches_induk(browser, tmp_path, selected, input_named):
    controls = []
    for i, (code, label) in enumerate(CHOICES):
        controls.append(
            f'<p-radiobutton style="display:inline-block" formcontrolname="AskedTo" '
            f'name="AskedTo" value="{code}" label="{label}">'
            f'<span><input type="radio" id="choice-{i}" value="{code}" '
            + ('name="AskedTo" ' if input_named else '')
            + ('checked ' if selected == i else '')
            + f'disabled></span><label for="choice-{i}">{label}</label></p-radiobutton>')
    html = '<div class="p-tabview-panel"><div class="p-accordion-content">' + ''.join(controls) + '</div></div>'
    with isolated_context(browser) as context:
        page = context.new_page()
        page.route('**/*', lambda route: route.abort())
        page.set_content(html)
        fields = page.locator('.p-tabview-panel').evaluate(driver.FIELDS_JS)
    assert len(fields) == (0 if selected is None else 1)
    if selected is not None:
        assert fields[0]['field'] == 'AskedTo'
        assert fields[0]['value'] == CHOICES[selected][0]
        assert fields[0]['label'] == CHOICES[selected][1]
    workbook, _, _ = export_ppn(tmp_path, [section('Induk', fields=fields)])
    try:
        expected = None if selected is None else CHOICES[selected][1][3:]
        assert workbook['Induk']['D48'].value == expected
    finally:
        workbook.close()


@pytest.mark.parametrize('fields', [
    [{'field': 'AskedToPrevious', 'label': CHOICES[0][1], 'value': CHOICES[0][0]}],
    [{'field': 'AskedTo', 'label': 'UNKNOWN CHOICE', 'value': CHOICES[0][0]}],
    [{'field': 'AskedTo', 'label': CHOICES[0][1], 'value': CHOICES[1][0]}],
    [{'field': 'AskedTo', 'label': label, 'value': code} for code, label in CHOICES[:2]],
])
def test_unverified_or_multiple_selected_refund_controls_never_default(tmp_path, fields):
    workbook, reports, _ = export_ppn(tmp_path, [section('Induk', fields=fields)])
    try:
        assert workbook['Induk']['D48'].value is None
        assert not all(report['complete'] for report in reports)
    finally:
        workbook.close()
