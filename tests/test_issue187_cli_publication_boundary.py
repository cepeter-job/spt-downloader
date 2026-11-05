"""Issue #187 Phase 4: synthetic tampering inside the offline CLI publication gap.

These tests exercise the public save_output API, not an unowned private helper.
They do not assert power-loss atomicity or authenticate live Coretax data.
"""
from pathlib import Path

import pytest
from openpyxl import load_workbook

import coretax
from support_runs import fixture_run


def published_bytes(folder):
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in folder.rglob("*")
        if path.is_file()
        and not path.relative_to(folder).parts[0].startswith(".spt-export-")
    }


def test_cli_does_not_commit_wrong_taxpayer_workbook_changed_during_replace(
    tmp_path, monkeypatch,
):
    first = fixture_run()
    coretax.save_output(first, tmp_path)
    original = published_bytes(tmp_path)
    replacement = fixture_run()
    replacement["taxpayer_name"] = "SYNTHETIC NEW COMPANY"

    move = Path.replace
    changed = []

    def mutate_after_move(source, target):
        result = move(source, target)
        target = Path(target)
        if target == tmp_path / "resume.xlsx" and not changed:
            book = load_workbook(target)
            book["Ringkasan"]["B2"] = "0000000000000002"
            book.save(target)
            book.close()
            changed.append(target)
        return result

    monkeypatch.setattr(Path, "replace", mutate_after_move)
    with pytest.raises(ValueError, match="digest|NPWP mismatch"):
        coretax.save_output(replacement, tmp_path)

    assert changed == [tmp_path / "resume.xlsx"]
    assert published_bytes(tmp_path) == original
    assert "output_files" not in replacement
    coretax.verify_workbook(tmp_path / 'resume.xlsx', first, include_details=False)


def test_cli_rejects_manifest_mutation_during_final_publish(tmp_path, monkeypatch):
    first = fixture_run()
    coretax.save_output(first, tmp_path)
    before = published_bytes(tmp_path)
    replacement = fixture_run()
    replacement["taxpayer_name"] = "SYNTHETIC NEW COMPANY"

    move = Path.replace
    altered = []

    def change_published_manifest(source, target):
        result = move(source, target)
        target = Path(target)
        if target == tmp_path / "run.json" and not altered:
            import json

            payload = json.loads(target.read_text(encoding="utf-8"))
            payload["npwp"] = "0000000000000002"
            target.write_text(json.dumps(payload), encoding="utf-8")
            altered.append(target)
        return result

    monkeypatch.setattr(Path, "replace", change_published_manifest)
    with pytest.raises(ValueError, match="digest|manifest|run.json"):
        coretax.save_output(replacement, tmp_path)

    assert altered == [tmp_path / "run.json"]
    assert published_bytes(tmp_path) == before
    coretax.verify_workbook(tmp_path / 'resume.xlsx', first, include_details=False)
    assert "output_files" not in replacement


def test_cli_rejects_byte_mutation_that_keeps_xlsx_readable(tmp_path, monkeypatch):
    first = fixture_run()
    coretax.save_output(first, tmp_path)
    before = published_bytes(tmp_path)
    replacement = fixture_run()
    replacement["taxpayer_name"] = "SYNTHETIC NEW COMPANY"

    move = Path.replace
    modified = []

    def append_after_move(source, target):
        result = move(source, target)
        target = Path(target)
        if target == tmp_path / "resume.xlsx" and not modified:
            # ZIP readers tolerate trailing bytes; semantic workbook checks
            # alone must not silently certify an altered published artifact.
            with target.open("ab") as workbook:
                workbook.write(b"SYNTHETIC ALTERED ZIP TRAILER")
            modified.append(target)
        return result

    monkeypatch.setattr(Path, "replace", append_after_move)
    with pytest.raises(ValueError, match="digest|checksum|bytes"):
        coretax.save_output(replacement, tmp_path)

    assert modified == [tmp_path / "resume.xlsx"]
    assert published_bytes(tmp_path) == before
    coretax.verify_workbook(tmp_path / 'resume.xlsx', first, include_details=False)
    assert "output_files" not in replacement


def test_post_publish_staging_exclusion_cannot_hide_arbitrary_files(tmp_path):
    run = fixture_run()
    coretax.save_output(run, tmp_path)
    outside_staging = tmp_path / "unreviewed-folder"
    outside_staging.mkdir()
    (outside_staging / "rogue.xlsx").write_bytes(b"SYNTHETIC UNAPPROVED WORKBOOK")

    with pytest.raises(ValueError, match="staging|file set"):
        coretax.verify_outputs(run, tmp_path, staging=outside_staging)
