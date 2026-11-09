# Corporate schema expansion (525 rebuild follow-up)

Baseline main: 9255e9d (PR #204 merge; pins refreshed).

## Live evidence

Latest Badan runs (build 42570251197, jobs ecdc9089 / 29881502,
2026-11-09 06:24-07:00 UTC):

- CORPORATE: `dom` / `adapter_ineligible`,
  reason `unmapped_corporate_source_subtree` +
  `unbound_corporate_source_response`. Observer passed (no
  `corporate.observe_unavailable`); PPh21/Unifikasi/PPN verified native
  in the same attempts.

Reconciliation of the 58 `CurrentFormData` keys (structure only):

- 5 `_CIT_CONTROLS` (already exempt).
- 16 of 17 declared `FORMS` roots present (`Calculation…`,
  `ListOfOwnership`, `MainFormData`, `FiscalYearIncomeTax`, `L10b/c/d`,
  `L11A/B/C` etc.). `DeclarationTransactionRelatedParties` (L10-A) is
  entirely absent; the 525 chunk still reads it via `?.` (optional
  chaining), so the frontend tolerates the omission.
- 37 extras: 31 `null`, 6 with data (`ActualMonths` int 1–12 equals
  `PeriodMonthEnd−PeriodMonthStart+1`; `AuditOpinion` doc object;
  `FinancialStatement` / `OtherDocuments` doc lists (1 item each);
  `PrefillFromId` 36-char string; `ElectronicReceiptSubmission` bool).

Manifest endpoints (121+ per attempt): the only undeclared call is
`loadcit/l4-table-a-grid/footer` (POST). L3 footer is already declared
as a `dependencies` binding with exact request
`{'ReturnSheetRecordId': record}`; L4 has no footer declaration anywhere.

## Fix (one PR, all bindings explicit)

- Explicit null allowlist: 31 reviewed names permitted only with an
  exact JSON `null` value (omitted rows otherwise refuse). No catch-all.
- Six data keys validated per key as source evidence (types, ranges,
  period/identity relations; doc metadata only — PDF custody stays
  independently gated by `coretax_attachments`):
  `ActualMonths` (1–12, equals derived months), `AuditOpinion` (doc
  object), `FinancialStatement` / `OtherDocuments` (doc lists),
  `PrefillFromId` (UUID format, contradicts nothing), 
  `ElectronicReceiptSubmission` (bool).
- L10-A: absent root is treated as a single null row (backend omits the
  empty section; frontend `?.` proves the read is optional).
- L4 footer: declare `loadcit/l4-table-a-grid/footer` as a `dependencies`
  binding with the exact single-field request and reconcile its totals
  with the L4 projection (missing/changed footer still refuses).

## What does not change

- Observer `TABLE`/grid contracts, PDF download gates, and AMENDMENT/
  balance/choice logic. `L12A/L13/L14` (and other null L-forms) stay
  omitted-but-proven, never granted.

## Tests

- allowlist: null passes, non-null refuses (per key set).
- six keys: shape/range/identity proofs + contrary-shape refusals.
- L10-A: absent root passes as empty; L4 footer: missing/changed footer
  refuses, matching footer reconciles.

## Verification

- CI: full green on the PR head, then merge.
- Live rerun on the merged EXE (SHA256-verified): expect Badan past the
  adapter mapping gates; if another gate refuses, it will be the next
  precise reason.
