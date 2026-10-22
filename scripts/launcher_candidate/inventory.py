"""Strict, stdlib-only inventory contract for the isolated launcher candidate."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


IDENTITY = {"schema": 1, "python": "3.14.8", "architecture": "x64", "gil": True, "tcl": "9.1.0", "tk": "9.1.0"}


def _local(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("invalid candidate-relative path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(part in ("", ".", "..") for part in name.split("/")):
        raise ValueError("external or noncanonical candidate path")
    path = root.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(root):
        raise ValueError("candidate path escapes root")
    for parent in (path, *path.parents):
        if parent == root:
            break
        if parent.is_symlink() or parent.is_junction():
            raise ValueError("linked candidate resource")
    return path


def validate_inventory(document: dict, root: Path) -> None:
    """Validate exact reviewed identity, resource locality, file set and hashes."""
    if root.is_symlink() or root.is_junction():
        raise ValueError("linked candidate root")
    root = root.resolve(strict=True)
    for key, expected in IDENTITY.items():
        if type(document.get(key)) is not type(expected) or document.get(key) != expected:
            raise ValueError(f"unexpected candidate {key}")
    files = document.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("missing candidate files")
    if len({name.casefold() for name in files}) != len(files):
        raise ValueError("case-insensitive candidate collision")
    actual = set()
    for path in root.rglob("*"):
        name = path.relative_to(root).as_posix()
        _local(root, name)
        if path.is_file() and name != "inventory.json":
            actual.add(name)
    if actual != set(files):
        raise ValueError("candidate file-set mismatch")
    for name, digest in files.items():
        path = _local(root, name)
        if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
            raise ValueError("invalid candidate digest")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"candidate hash mismatch: {name}")
    loaded = document.get("loaded")
    roles = {"python", "_tkinter", "tcl", "tk"}
    if not isinstance(loaded, dict) or set(loaded) != roles:
        raise ValueError("incomplete native resources")
    role_hashes = document.get("loaded_sha256")
    modules = document.get("native_modules")
    if not isinstance(role_hashes, dict) or set(role_hashes) != roles:
        raise ValueError("incomplete native role hash proof")
    if not isinstance(modules, dict) or not modules:
        raise ValueError("missing native module proof")
    for name, digest in modules.items():
        if not isinstance(name, str) or name not in files or digest != files[name]:
            raise ValueError("native module proof disagrees with candidate files")
    for role, name in loaded.items():
        if not isinstance(name, str) or name not in files or not _local(root, name).is_file():
            raise ValueError("unverified native resource")
        if role_hashes[role] != files[name] or modules.get(name) != files[name]:
            raise ValueError("native role proof disagrees with candidate files")
    libraries = document.get("libraries", {})
    if set(libraries) != {"tcl", "tk"}:
        raise ValueError("incomplete script resources")
    for kind, name in libraries.items():
        path = _local(root, name)
        marker = "init.tcl" if kind == "tcl" else "tk.tcl"
        if not path.is_dir() or f"{name}/{marker}" not in files:
            raise ValueError("unverified script library")
    licenses = document.get("licenses", [])
    required = {"licenses/python.txt", "licenses/tcl.txt", "licenses/tk.txt"}
    if not required.issubset(licenses) or any(name not in files for name in licenses):
        raise ValueError("missing runtime license")
    if "python.exe" not in files:
        raise ValueError("missing interpreter")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--probe", type=Path)
    args = parser.parse_args()
    inventory = args.root / "inventory.json"
    if args.probe:
        document = json.loads(args.probe.read_text(encoding="utf-8"))
        document["files"] = {path.relative_to(args.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(args.root.rglob("*")) if path.is_file() and path != inventory}
        document["licenses"] = sorted(name for name in document["files"] if name.startswith("licenses/"))
    else:
        document = json.loads(inventory.read_text(encoding="utf-8"))
    validate_inventory(document, args.root)
    if args.probe:
        inventory.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(document['files'])} candidate files")


if __name__ == "__main__":
    main()


def validate_candidate_report(report: dict, inventory: dict) -> None:
    """Require exact launcher proof independently of the worker profile."""
    if not isinstance(report, dict) or not isinstance(inventory, dict):
        raise ValueError('invalid candidate report')
    for key, expected in {'ok': True, 'credentials_accessed': False,
                          'live_scrape': False, 'worker_python': '3.14.8'}.items():
        if type(report.get(key)) is not type(expected) or report.get(key) != expected:
            raise ValueError('unsafe or incomplete candidate self-test')
    if type(report.get('frozen')) is not bool:
        raise ValueError('missing source/frozen identity')
    proof = report.get('launcher_candidate')
    if not isinstance(proof, dict):
        raise ValueError('missing actual launcher proof')
    for key, expected in IDENTITY.items():
        if (type(proof.get(key)) is not type(expected) or proof.get(key) != expected
                or type(inventory.get(key)) is not type(expected) or inventory.get(key) != expected):
            raise ValueError('unexpected exact launcher identity')
    try:
        expected_resources = candidate_resources(inventory)
        loaded = inventory['loaded']
        expected_hashes = {role: inventory['files'][name] for role, name in loaded.items()}
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('incomplete reference inventory') from error
    if (set(loaded) != {'python', '_tkinter', 'tcl', 'tk'}
            or proof.get('loaded') != loaded
            or proof.get('loaded_sha256') != expected_hashes
            or proof.get('resources') != expected_resources):
        raise ValueError('candidate native or script resource identity mismatch')


def candidate_resources(inventory: dict) -> dict:
    """Exact native roles and complete Tcl/Tk script trees requiring byte proof."""
    files = inventory['files']
    names = set(inventory['loaded'].values())
    names.update(name for name in files if any(name.startswith(prefix + '/')
                 for prefix in inventory['libraries'].values()))
    return {name: files[name] for name in sorted(names)}
