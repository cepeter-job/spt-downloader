# PR108 corporate formatting review

The requested review found no formatting defect against the approved corporate
presentation design. One stale architecture sentence described three separators;
the implementation and approved saved-export tests require one. PR110 corrected
that sentence without changing the formatter or template.

Reviewed [PR108](https://github.com/cepeter-job/spt-downloader/pull/108),
merged as `374c6da8b494871535e82da430255d95984e3877`, tree
`8b0887012699b8753206bb3ee532bd49452400e3`. The twelve changed files and final
tariff/layout delta were inspected. Independent review accepted the result.

## Checked behavior

| Area | Verified contract |
| --- | --- |
| Induk structure | Two columns, one blank identity separator, populated C/D/E/F captions and the tariff at the end. No empty F caption when F has no content. |
| Headings and borders | C heading is unbordered; D/E/F headings have horizontal rules. Data/tariff cells retain thin borders. |
| Dimensions | Approved column widths A = 110.7109375 and B = 49.7109375. |
| Values and accounting | Literal identifiers and selected choices remain text. Zero-decimal display preserves exact stored amounts, including synthetic 1234.5 and zero. Unsafe or ambiguous amount bindings remain unresolved. |
| L9 | The captured first-table total remains bold and source-authoritative; synthetic 999 is retained although the body contains 20. |
| L10-C | The retained empty E3 monetary slot keeps zero-decimal rupiah accounting. |
| Audit | Reviewed redundant controls/header remnants are annotated additively. Unmapped counts and PARTIAL remain truthful; unresolved L11-B rows and DER operand gates remain. |
| DOM controls | Only actual owned paginator descendants are omitted from business-field capture. An unnamed business control elsewhere remains captured. |

Source captures and checkpoints remain unchanged by these presentation rules.
The approved template contains static styles/captions rather than private sample
taxpayer values. The JSON continuation preserves these renderer/template blobs.

## Runner evidence and limits

[Run 39983317348, attempt 1](https://github.com/cepeter-job/spt-downloader/actions/runs/39983317348)
tested merge `bdf73b23e633083b76d6372b277091a6bbbbda89`, whose tree matches the
actual PR108 merge. All six inventory/JUnit archives were downloaded and their
hashes, sizes, environments, complete collections, phase outcomes, JUnit
identities, measurement results and summary totals reconciled.

There are **5,064 distinct Windows passes**, in disjoint partitions of 2,584 and
2,480, with zero failures/errors/skips. This includes 5,028 baseline cases,
35 reviewed-layout cases and one owned-control case. The 710 portable passes
overlap Windows and are not added to that total.

The checks include saved/reopened synthetic workbook values, styles, borders,
dimensions and mapping/Audit behavior. They do not establish interactive Excel
visual/print acceptance or a new live taxpayer capture. No product tests/imports,
browser fixtures or Excel application were executed locally for this review.

| Downloaded evidence | Artifact ID | SHA256 |
| --- | --- | --- |
| Windows inventory 0 | 12514987834 | `b045aed79ac8d28a806d46daa7c58437741fdb29a158ac12e99d1df4f0accd29` |
| Windows JUnit 0 | 12515446929 | `dfd3f72023b44c4a12f25c9bb69288219fc452f0ef4e67cabbd2c8e17e1457ed` |
| Windows inventory 1 | 12515816406 | `0cf3f799053ef07ef0779bb5b1e97d78092b5775e027de7ae3256af35139db7d` |
| Windows JUnit 1 | 12515911126 | `6a3e11df4d26635093d346b48b83bc8b7c259cf4966ae2ed03202cf126023af6` |
| Portable inventory | 12514173446 | `09dad1cf733e22320315e857cbbd0efce9f8771a6d4e75a49627d3c2224f69ee` |
| Portable JUnit | 12515090381 | `c83ee050ee37953d58b0b0f307bbd8326e5e62c34cc5a9b490463129c0dd4bf8` |
