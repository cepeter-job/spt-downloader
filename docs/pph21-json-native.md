# Native JSON PPh Pasal 21/26

## Approved scope

Extend the existing PPN JSON-first pipeline for the five observed PPh21 forms:
Induk, L-IA, L-IB, L-II and L-III. This is a separate PR based on merged PR #36
(`4482063b9ada37125d1e3d49b83e401a23719cdb`). The user approved the following
bounded design before implementation:

- Source business values only from custody-checked JSON responses, with per-value
  source paths and sequences; use DOM only for read-only navigation and structure.
- Preserve the approved PPh21 template, dynamic body growth and reported totals.
  Monetary slots use native Excel numbers under the existing strict precision
  contract; identifiers, periods and document numbers remain literal text.
- Unsupported JSON shapes/builds may fall back to DOM, explicitly reported as DOM.
  Identity contradictions, authentication failures and privacy violations fail
  closed even when coverage or the public build is unsupported.
- Reuse existing capture, listing identity, projection, observer and export
  infrastructure where the verified PPh21 contract actually matches. Keep
  PPN/Unifikasi behavior unchanged; do not generalize unrelated tax types.
- All product imports, tests, synthetic browser/Tk fixtures and builds run on
  GitHub runners. No real taxpayer captures or identifiers belong in this PR.

## Public-source evidence

Source bytes are inspected as text, never executed. These are public application
bundles, not taxpayer responses. Their existence is not native-data acceptance.

| Source | SHA-256 | Binding |
| --- | --- | --- |
| `/returnsheets/id-ID/main.cccfdb820c20596c.js` | `696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd` | character offset 217305: `article-21-26-tax-return/:taxpayerAggregateId/:recordId/:taxTypeCode/:aggregateIdentifier` loads chunk 803/module 82736 |
| `/returnsheets/id-ID/runtime.ad6c8837930b6ad2.js` | `934f411dec7ead216ca4d936a71c5b6a9ebf100874412b052fa6035e41102c57` | chunk 803 filename suffix `8681206e4827011e` |
| `/returnsheets/id-ID/803.8681206e4827011e.js` | `cd7b51042384a63e1d1fae9b9b284a38a0a942ab9f95a7fceb46b3c76fcd9add` | `ReturnsheetsSharedArticleTwentyoneTwentysixTaxReturnModule` |

All seven grid constructors below bind `GridId={ReturnSheetRecordId:this.recordId}`
and `IdColumn="RecordId"`. Offsets are Unicode string positions in the decoded
public 803 bundle, not inferred API aliases. Paths are relative to the configured
returnsheet API base.

| Form/group | Endpoint | Offset |
| --- | --- | --- |
| L-IA | `/loadarticle2126/l1a-grid` | 2640 |
| L-IB/BPA1 | `/loadarticle2126/l1b-bpa1-grid` | 11994 |
| L-IB/BPA2 | `/loadarticle2126/l1b-bpa2-grid` | 12192 |
| L-II/BPA1 | `/loadarticle2126/l2-bpa1-grid` | 21922 |
| L-II/BPA2 | `/loadarticle2126/l2-bpa2-grid` | 22175 |
| L-III/BP21 | `/loadarticle2126/l3-bp21-grid` | 31529 |
| L-III/BP26 | `/loadarticle2126/l3-bp26-grid` | 31726 |

Chunk 693 is the separate Unifikasi family, not the PPh21 component.

## Implementation and verification order

1. Publish RED safety contracts for every grid's literal record identity,
   cross-family contamination, and dispatch checks before observation, after
   observation and after final response drain. Unknown structure must not hide
   any contradiction. Matching requests alone never grant JSON eligibility.
2. Trace the actual primary response consumer, FormData schema and final Induk
   calculation lifecycle. Verify header and appendix footer source paths,
   reference-label dependencies, read-only visibility and later assignments.
   Do not mistake the `wsarticle2126` update-check method for proof of the primary
   source. Do not copy Unifikasi identity types or aliases without evidence.
3. Add synthetic five-form adapter, per-value provenance, pagination/count,
   repeated-snapshot and identity contracts; implement the specific projections.
   Include empty/optional groups, duplicates, zero/negative values and amendments.
4. Wire value-free observation and dispatch with getter-trap browser tests,
   fallback audit assertions, original-capture immutability, saved-workbook
   numeric/layout checks and unchanged PPN/Unifikasi regression contracts.
5. Verify exact-head runner results and packaged worker resources; publish the
   completed PR without claiming installation or live-account acceptance.

## Current acceptance state

Initial tests-only RED slice. Primary schema, final-state projection and complete
five-form native eligibility are not yet implemented or verified. No new product
behavior is claimed. Public-source evidence and synthetic tests must remain
separate from eventual authorized live acceptance.
