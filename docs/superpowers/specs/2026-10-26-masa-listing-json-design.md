# Submitted Masa listing metadata

The latest private job reconciled its four detail captures and all selected
output bytes. Terminal publication was ERROR after a transient workbook-set
mismatch; the operator confirms opening/previewing output during publication.
No retained evidence identifies the temporary file. Keep publication verification
and recovery unchanged. Do not equate capture COMPLETE with terminal success.

## Intent and boundary

Extend the existing source-bound submitted-list adapter from ordinary Rupiah
corporate returns to PPN, PPh21/26 and Unifikasi, including mixed supported pages.
The same inspected `returnsheetssubmitted` response remains authoritative. Retain
original bytes, source fields, record IDs, literal model/period and pagination.

Known pairs and captions are `ICT_RCIT/ICT_RCITR` (PPh Badan / SPT PPh Badan
Rupiah), `VAT_VAT/VAT_VATR` (PPN / SPT Masa PPN), `ICT_WIT/ICT_WITR` (PPh Pasal
21/26 / SPT Masa PPh Pasal 21/26), and `ICT_WT/ICT_WTR` (PPh Unifikasi / SPT
Masa PPh Unifikasi). They agree with the reference workbook route catalog and
the current privately captured list. No private record is a test fixture.

Accept only eight ASCII period digits: corporate January-to-December, or a
same-month Masa code with month 01..12 and nonzero four-digit year. The bound
cell may contain the exact literal code or its exact reviewed Indonesian
caption (`Januari - Desember YYYY` or `Desember YYYY`, etc.). Retain that observed
caption as metadata; do not normalize the source. Monthly ranges, dollar forms,
unknown types, missing codes and unsupported layouts use whole-page DOM fallback.

Read only six reference/model caption cells, removing controls without reading
their values or checked state. Require flat, unspanned body rows. Preserve the
current exact model, count, filter, taxpayer, status, origin and sequence gates.
Known contradictory type pairs, reordered known family captions and period/model
contradictions are fatal. Inspect all rows for known contradictions before any
unsupported-shape fallback can hide them. Conflicting captions for one code
remain fatal. Unknown locale/caption or null channel remains unsupported.

## Approaches and decision

Reconstructing labels from the workbook alone would lose current UI binding.
Reading the complete DOM grid works today but discards native source fields.
Extend the existing narrow caption binding instead; this is the implementation
choice under the user's instruction to continue autonomously.

Do not modify detail projectors, catalog access, request permissions, export
layout, publication guards, CI, dependencies, resources or worker packaging.
Do not claim faster live execution or broader detail COMPLETE from synthetic
listing verification. All product execution stays on GitHub runners.

## Acceptance

Runner tests prove all twelve months with literal/reviewed captions, mixed pages
across real synthetic pagination, preserved raw metadata and IDs, no full-grid
reads on supported pages, audited fallback for unsupported pages, fatal known
contradictions even behind unknown rows, control-value exclusion and Stop.
Retain existing full Windows/portable, build and package gates. Before merge,
review latest main and the preceding other-session merged PR and interactions.
