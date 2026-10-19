# Native JSON PPh Unifikasi

Status: design approved by the user; implementation and runner verification pending.

## Scope and existing architecture

Extend the existing PPN/PPh21 JSON-first path, not a parallel capture system.
The prerequisite Accounting Rp change is merged in PR #39 at
`e6d5f71b3cbcc3e644e08a68b4a1e8ef981b46cd`.

Use the current inventory proof -> selected identity -> DetailJsonCapture ->
value-free observer -> Masa adapter -> business sections -> approved Excel
renderer pipeline. Bind the four literal forms INDUK, DAFTAR-I, DAFTAR-II and
LAMPIRAN-I. Existing source bindings describe five paginated appendix grids and
one Induk tree; the tree is not a sixth paginated endpoint.

Only source-proven controls, enums, model/period transformations and reference
catalogs may be admitted. The existing projection helpers are groundwork, not
proof of production completeness. Verify final lifecycle assignments, reference
label consumers and source evidence before enabling each new binding.

## Safety and compatibility

- Tax values come from captured JSON bytes, never input values, selected labels,
  business cells or footer text in the DOM. DOM remains navigation/structure.
- Reuse packet custody, selected record/taxpayer/model/period verification,
  request checks before and after observation/drain, and source-count checks.
  Contradictions and authorization failures remain fatal before fallback.
- Unknown safe schemas may explicitly fall back to DOM. Such results remain
  `used=dom` and cannot satisfy native acceptance. Native success requires
  `used=json`, complete coverage and source/path/sequence provenance.
- Keep Unifikasi's approved templates and Accounting Rp display. Monetary slots
  are Excel numbers under existing locale/precision guards; identities and
  period/year stay text. Keep source-only evidence rather than importing PPN's
  display-omission policy. Do not alter PPN/PPh21 resources or contracts.
- Do not create guessed endpoints or extract credentials. No live account
  requests, installation, release or native-PR merge are authorized by this task.

## Verification and delivery

1. Commit coherent synthetic regression contracts first and obtain actual RED
   results from the existing GitHub workflows, without changing those workflows.
2. Implement listing/primary binding, observer and projection gaps using existing
   abstractions. Add only narrowly necessary modules and explicit worker entries.
3. Obtain exact-head Windows full-suite, portable, build and frozen evidence;
   exercise isolated allowlisted worker imports and connected JSON-to-Excel.
4. Cover all forms/grids, empty and populated pages, retained pagination,
   contradictory identity, missing source, explicit fallback, getter traps,
   source footers, numeric storage and layout. Preserve all existing negatives.
5. Publish a focused PR with exact commits/runs/artifacts and remaining live
   acceptance clearly separated. Synthetic output is never taxpayer output.

All product execution, browser fixtures, tests, imports and builds are
GitHub-runner-only. Local inspection is source/AST/stdlib metadata only.
