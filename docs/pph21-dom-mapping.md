# PPh21 DOM mapping repair

## Scope and evidence

Repair only PPh Pasal 21/26 presentation, using the approved sanitized reference and observed DOM structure. The user's downloaded workbook was matched byte-for-byte to one local checkpoint and backed up outside Git. No private workbook, taxpayer identity, capture, monetary value or receipt belongs in this PR. PPN, Unifikasi and their source modes remain unchanged.

The source uses generic table names with separate `group` captions. Existing PPh21 matching reads only `name`. Source `rows` also includes condensed footer cells; `body_row_count`, `footer` and `footer_spans` distinguish these from employee rows. Source footer physical widths need not equal visible header count. Do not reuse a PPN width assumption or distribute values by row occurrence.

## Five form contracts

1. **Induk:** source rows corresponding to 47–52 belong in 12–17; the DTP row corresponding to 55 belongs in 21. Match all remaining labels within their PPh21/PPh26 and withheld/DTP groups, never across groups. Handle only the observed exact tooltip suffix and explicit DTP label variants. Keep template labels unchanged. Duplicate/conflicting identities are unresolved, not reassigned by position.
2. **L-IA:** keep employee rows in their named columns; reported totals go to G/I, not condensed C/E. For the reviewed 132-row shape, preserve its blank source spacer so totals occupy 138–140. Treat the spacer as layout, never as an employee; grow styles and total labels together. Omit the redundant displayed extra-source block.
3. **L-IB:** BPA1 begins at 6; optional BPA2 at 12; reported totals at 16–18 in G/H before body growth. Bind by actual group, not capture order or generic table numbering.
4. **L-II:** BPA1 begins at 5; optional BPA2 at 11; reported total at 15 in G/H before growth. The observed `MASA PEEROLEHAN PENGHASILAN` column has no reference slot; retain it in source custody, not an unrelated facility column.
5. **L-III:** BP21 begins at 5, optional BP26 at 11; the reference's Pasal26 totals and overall total occupy 15–17 in G/H before growth. Do not replace Pasal26 subtotals with Pasal21 subtotals. Source-only tax/object columns and BP21 subtotal details remain in the unchanged checkpoint.

Coordinates identify reference slots and the user's reviewed case, not universal source row numbers. Genuine body growth shifts later blocks and totals together. Preserve duplicates, literal identifiers/dates/source amounts, negative totals, styles, dimensions, print settings and workbook scope. Never replace reported totals with sums or fabricate missing optional rows.

## Omission and error semantics

The user authorizes removal of redundant extra-source presentation. Do not call the raw display renderer for PPh21. Return a mapping report to the existing `resume.xlsx` Audit mechanism instead; unknown fields/headers/groups, ambiguous labels, invalid body counts, contradictory footer copies, unexpected span patterns, duplicate totals and incomplete capture must remain explicitly unresolved/PARTIAL. Removing displayed raw data is not permission to certify it as mapped. Known source-only fields/columns may be omitted only by narrow approved rules, retaining the complete unchanged checkpoint.

## Verification and rejected investigation suggestions

Publish synthetic RED before product changes; run all product tests/builds on GitHub only. Preserve the existing body-growth tests, captions-not-order tests and cross-tax isolation. Three older tests intentionally change from visible raw extras to unchanged source plus explicit unresolved reports. Add actual-shape group, tooltip, footers, empty optional groups, reordered headers, negative totals, source immutability and invalid-evidence contracts.

Static investigation suggestions to fix total row numbers permanently or assign repeated labels by order are rejected: they would overwrite growing bodies or mix tax/DTP groups. The observed primary group-binding defect is `name` versus `group`, not proven duplicate source rows.

After GREEN: independent review, exact-tree package verification and a separately staged read-only-source workbook correction/audit. Do not rerun live collection without authorization or modify the original Downloads workbook. No CI changes to obtain GREEN.

## Review decisions and RED evidence

- Verified Windows RED at `4cfaedb2ccff69f1ec2e2259372d09874fb6c64f` (run `39039904851`, artifact `12103996716`): 2,653 collected cases, 28 failures in the changed PPh21 tests. Supplemental tests at `f507032833765179c5476b64a4a7ae225cbb6334` (run `39053916655`, artifact `12108813409`) exercise bounded control and BP21 subtotal omissions. The duplicate-row fixture increment of a null paginator total was corrected without changing its duplicate-row assertion; the earlier RED exercised that assertion with a numeric fixture total.
- Preserve conflicting-identity tests: generic `Tabel 1` is not a semantic group, but recognized `name=BPA1` contradicting `group=BPA2` must be unresolved. Do not replace those tests with mere unknown-group cases.
- Induk has no paginator total (`source_total=null`); validate the observed body/footer boundary, not an invented zero total.
- Reported L-IB/L-II totals bind only to the observed terminal BPA2 group. L-III reference totals bind only to BP26. The two exact BP21 subtotal labels and their physical spans are approved presentation omissions, not substitutes for BP26 values. Unobserved footer ownership stays PARTIAL; speculative position-based fallback is intentionally rejected.
- The core static review found no confirmed regression but is not execution evidence. Only an exact-tree GREEN runner and subsequent artifact/workbook verification establish readiness.
- The first implementation run (`39056618376`, Windows artifact `12109204460`) exposed six existing integration fixtures that expected raw PPh21 marker rows to remain visible. Move isolation/overwrite markers into supported status/body slots rather than weakening their file/model/link assertions. Generic `L-Z` duplicate rows remain visible; unsupported Induk duplicate rows remain unchanged in source custody, now asserted explicitly. No PPN/Unifikasi fixture semantics or CI routing are changed.
