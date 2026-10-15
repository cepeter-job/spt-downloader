"""Synthetic explicit-overwrite/selected-file publication contracts."""
from copy import deepcopy
import pytest
import coretax
from spt_desktop import output
from test_split_output import fixture_run


def test_decline_overwrite_preserves_all_old_bytes(tmp_path):
    run=fixture_run()
    coretax.save_output(run,tmp_path/'source')
    first=output.publish_workbooks(run,tmp_path/'source',tmp_path/'Downloads','first-job')
    before={p.relative_to(first).as_posix():p.read_bytes() for p in first.rglob('*.xlsx')}
    assert output.existing_outputs(run,tmp_path/'Downloads')
    with pytest.raises(FileExistsError,match='overwrite|consent'):
        output.publish_workbooks(run,tmp_path/'source',tmp_path/'Downloads','second-job',overwrite=False)
    assert {p.relative_to(first).as_posix():p.read_bytes() for p in first.rglob('*.xlsx')}==before


def test_overwrite_replaces_only_selected_periods(tmp_path):
    run=fixture_run()
    coretax.save_output(run,tmp_path/'first-source')
    final=output.publish_workbooks(run,tmp_path/'first-source',tmp_path/'Downloads','first-job')
    untouched=final/'SPT Masa 21/SPT_21_Februari 2025_Normal.xlsx'
    before=untouched.read_bytes()
    selected=deepcopy(run)
    selected['records']=selected['records'][2:3]
    selected['records'][0]['sections'][0]['fields'][0]['value']='NEW SYNTHETIC MARKER'
    coretax.save_output(selected,tmp_path/'second-source')
    second=output.publish_workbooks(selected,tmp_path/'second-source',tmp_path/'Downloads','second-job',overwrite=True)
    assert second==final
    assert untouched.read_bytes()==before
    coretax.verify_outputs(selected,second,allow_extra=True)


def test_unknown_foreign_scope_is_not_overwritten_even_with_consent(tmp_path):
    run=fixture_run()
    coretax.save_output(run,tmp_path/'first-source')
    final=output.publish_workbooks(run,tmp_path/'first-source',tmp_path/'Downloads','first-job')
    from openpyxl import load_workbook
    path=final/'resume.xlsx'
    wb=load_workbook(path)
    wb['Ringkasan']['B4']='0000000000000002'
    wb.save(path);wb.close()
    before=path.read_bytes()
    with pytest.raises(ValueError,match='scope|NPWP'):
        output.publish_workbooks(run,tmp_path/'first-source',tmp_path/'Downloads','second-job',overwrite=True)
    assert path.read_bytes()==before