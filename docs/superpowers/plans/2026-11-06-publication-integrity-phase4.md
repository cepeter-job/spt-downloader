# Issue #187 Phase 4 — Offline CLI publication re-verification

Date: 2026-11-06. Base: `6687708b25c605eee85fece3a194781f9040076c`
(PR #191 merged). Test data and fault injection are invented and local.

## Existing coverage audited

- `tests/test_publication_crash_recovery.py`: actual process-death
  recovery at displacement, installation and index boundaries; changed
  targets and backups fail closed, restart is repeatable.
- `tests/test_desktop_overwrite_safety.py` and
  `tests/test_publication_recovery_custody.py`: native Windows
  replacement races, one-volume guarded paths, rollback and retained
  recovery bytes; no desktop publication changes are needed.
- `tests/test_json_output_folder.py`, `tests/test_mpn_publication.py`,
  `tests/test_financial_publication.py`: source JSON, MPN, PDF and
  selective overwrite publication/recovery are separately covered.
- `tests/test_output_safety.py`: offline CLI verification failure,
  incomplete selected set, locked replacement, case collisions,
  rollback interruption and retained backups already have negative tests.

## Actual uncovered gap (reproduced RED)

`coretax.save_output` verified staged XLSX files but its CLI
`_publish_output` did **not** recheck the installed files before
returning success. The following mutations were accepted before the fix:

1. A readable `resume.xlsx` had its synthetic NPWP changed immediately
   after the actual rename, after staging verification.
2. The published `run.json` had its synthetic NPWP changed after rename.
3. A readable XLSX had extra bytes appended to the ZIP after rename:
   openpyxl semantic checks can accept this, but its artifact digest changed.
4. The newly added staging-exclusion parameter initially permitted an
   arbitrary folder of extra unapproved XLSX files to be hidden.

All first failed against the observed behavior with the new contracts.

## Bounded fix and contracts

- Immediately after verifying the staged XLSX set, capture SHA-256
  digests of each selected XLSX/JSON. Pin the newly serialized `run.json`
  digest after writing its exact checked manifest.
- During the existing rollback-protected CLI sequence, check each
  staged digest before moving and each destination digest after moving.
- While original backups remain accessible, independently revalidate
  the installed workbook identities/proofs/links and compare all
  published digests plus the literal manifest. Failures enter the
  **existing** exception rollback and preserve previous bytes.
- Skip only the current same-parent `.spt-export-*` directory during
  post-publication workbook scanning. Reject arbitrary or redirected
  staging exclusions; normalize harmless lexical `folder/../target`
  paths for comparison.
- `tests/test_issue187_cli_publication_boundary.py` checks all three
  mutation cases and the staging-exclusion guard using real
  `coretax.save_output`, real openpyxl and exact byte snapshots
  across all old published files.

## Limits

This is an integrity fix for **normal CLI publication failures**, not
a guarantee of atomic multi-file publication during process death or
power loss. The desktop's private journal and restart-recovery tests
remain the owner of process-death recovery. It grants no new live
Coretax, tax data, MPN or PDF evidence authorization.

The SHA-256 contract protects against mutation after the verified
staging snapshot. This is not a digital signature or a guarantee
against malicious software that can modify files after the publication
operation returns.

## Verification

- [x] Four new synthetic contracts demonstrated RED where applicable
  and GREEN after the bounded fix.
- [x] Existing offline CLI output safety suite GREEN on puntoap/Windows.
- [ ] GitHub-hosted exact-head Windows shards, portable tests,
  locked dependency audit, Windows package and final aggregate gate.
- [ ] Private reviewed-PR `puntoap-wsl` supplemental validation.
- [ ] Review latest merged predecessor (#191) and source diff before merge.

Issue #187 remains open until the final acceptance checklist and other
approved-template/shape contracts have been reconciled. Do not reopen
previously covered crash/recovery tests merely to increase test counts.
