"""Synthetic runtime inventory contract; no taxpayer or native runtime fixtures."""
import copy
import hashlib
from pathlib import Path

import pytest

from scripts.launcher_candidate.inventory import validate_inventory


@pytest.fixture
def candidate(tmp_path):
    names = ["python.exe", "python314.dll", "DLLs/_tkinter.pyd", "DLLs/tcl91.dll", "DLLs/tcl9tk91.dll", "tcl/tcl9.1/init.tcl", "tcl/tk9.1/tk.tcl", "licenses/python.txt", "licenses/tcl.txt", "licenses/tk.txt"]
    files = {}
    for name in names:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic candidate fixture " + name.encode())
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    document = {
        "schema": 1, "python": "3.14.8", "architecture": "x64", "gil": True,
        "tcl": "9.1.0", "tk": "9.1.0", "files": files,
        "loaded": {"python": "python314.dll", "_tkinter": "DLLs/_tkinter.pyd", "tcl": "DLLs/tcl91.dll", "tk": "DLLs/tcl9tk91.dll"},
        "libraries": {"tcl": "tcl/tcl9.1", "tk": "tcl/tk9.1"},
        "licenses": ["licenses/python.txt", "licenses/tcl.txt", "licenses/tk.txt"],
    }
    document["loaded_sha256"] = {role: files[name] for role, name in document["loaded"].items()}
    document["native_modules"] = {name: files[name] for name in ["python.exe", *document["loaded"].values()]}
    return document, tmp_path


def test_accept_explicit_candidate(candidate):
    validate_inventory(*candidate)


@pytest.mark.parametrize("key,value", [("tcl", "9.0.4"), ("tk", "9.0.4"), ("python", "3.14.7"), ("architecture", "arm64"), ("gil", False)])
def test_reject_runtime_identity(candidate, key, value):
    document, root = candidate
    document[key] = value
    with pytest.raises(ValueError):
        validate_inventory(document, root)


@pytest.mark.parametrize("name", ["DLLs/_tkinter.pyd", "DLLs/tcl91.dll", "DLLs/tcl9tk91.dll"])
def test_reject_wrong_native_hash(candidate, name):
    document, root = candidate
    (root / name).write_bytes(b"different synthetic library")
    with pytest.raises(ValueError):
        validate_inventory(document, root)


@pytest.mark.parametrize("name", ["../outside", "C:/outside", "/outside", "tcl/../../outside"])
def test_reject_external_scripts(candidate, name):
    document, root = candidate
    document["libraries"]["tk"] = name
    with pytest.raises(ValueError):
        validate_inventory(document, root)


def test_reject_missing_license(candidate):
    document, root = candidate
    (root / "licenses/tk.txt").unlink()
    with pytest.raises(ValueError):
        validate_inventory(document, root)


@pytest.mark.parametrize("change", ["extra", "missing", "unlisted", "case_collision"])
def test_reject_file_set_mismatch(candidate, change):
    document, root = candidate
    if change == "extra":
        (root / "unexpected.txt").write_text("synthetic")
    elif change == "missing":
        (root / "python.exe").unlink()
    elif change == "unlisted":
        del document["files"]["python.exe"]
    else:
        document["files"]["PYTHON.EXE"] = document["files"]["python.exe"]
    with pytest.raises(ValueError):
        validate_inventory(document, root)


def test_reject_symlink(candidate):
    document, root = candidate
    path = root / "linked"
    try:
        path.symlink_to(root / "python.exe")
    except OSError:
        pytest.skip("Runner does not permit symlink creation")
    with pytest.raises(ValueError):
        validate_inventory(document, root)

@pytest.mark.parametrize("field", ["loaded_sha256", "native_modules"])
@pytest.mark.parametrize("value", [None, [], {}, "malformed"])
def test_reject_missing_or_malformed_loaded_proof(candidate, field, value):
    document, root = candidate
    document[field] = value
    with pytest.raises(ValueError):
        validate_inventory(document, root)


@pytest.mark.parametrize("field", ["loaded_sha256", "native_modules"])
def test_reject_absent_loaded_proof(candidate, field):
    document, root = candidate
    del document[field]
    with pytest.raises(ValueError):
        validate_inventory(document, root)


@pytest.mark.parametrize("role", ["python", "_tkinter", "tcl", "tk"])
def test_reject_probe_role_hash_disagreement(candidate, role):
    document, root = candidate
    document["loaded_sha256"][role] = "0" * 64
    with pytest.raises(ValueError):
        validate_inventory(document, root)


@pytest.mark.parametrize("digest", [None, 42, "not-a-sha256", "A" * 64])
def test_reject_malformed_role_hash(candidate, digest):
    document, root = candidate
    document["loaded_sha256"]["tk"] = digest
    with pytest.raises(ValueError):
        validate_inventory(document, root)


@pytest.mark.parametrize("role", ["python", "_tkinter", "tcl", "tk"])
def test_reject_role_absent_from_module_proof(candidate, role):
    document, root = candidate
    del document["native_modules"][document["loaded"][role]]
    with pytest.raises(ValueError):
        validate_inventory(document, root)


@pytest.mark.parametrize("name", ["python.exe", "DLLs/_tkinter.pyd"])
def test_reject_candidate_module_hash_disagreement(candidate, name):
    document, root = candidate
    document["native_modules"][name] = "0" * 64
    with pytest.raises(ValueError):
        validate_inventory(document, root)


@pytest.mark.parametrize("name,digest", [("python.exe", None), ("python.exe", "bad"), ("../external.dll", "0" * 64), ("DLLs/unlisted.dll", "0" * 64)])
def test_reject_malformed_or_uninventoried_module_proof(candidate, name, digest):
    document, root = candidate
    document["native_modules"][name] = digest
    with pytest.raises(ValueError):
        validate_inventory(document, root)


def test_probe_mode_rejects_recorded_hash_disagreement(candidate, monkeypatch):
    import json
    import sys
    from scripts.launcher_candidate.inventory import main

    document, root = candidate
    document["loaded_sha256"]["tk"] = "0" * 64
    probe_path = root.with_suffix(".json")
    probe_path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["inventory", "--root", str(root), "--probe", str(probe_path)])
    with pytest.raises(ValueError):
        main()
    assert not (root / "inventory.json").exists()
