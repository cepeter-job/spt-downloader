# Bounded L8 pure source projection

Continuation of the approved JSON completion program. Add a pure helper in the
existing `coretax_corporate_projection.py`; native eligibility, observers,
dispatch, transport and form discovery stay outside this slice. No additional
live capture or local product execution is authorized.

Baseline: actual main `84928e86bd595c94c844cb5c28643daddf2ced7f`, tree
`9b334855da23e77cf4bb5e1ed57bba80a9e57125`, with the verified 5,589 Windows cases
and 710 overlapping portable cases from
[native L11-A](../reports/2026-10-24-corporate-l11a-native.md).

## Source and admitted branch

Use the existing reviewed corporate and main asset hashes:

| Provider | SHA256 |
| --- | --- |
| Corporate525 | `fcd6d4a9244d6562a294675e802732562a9510621fbb9abbe651fa4de143048d` |
| Main | `696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd` |

Offsets below count UTF16 units. Parent root
`CalculationFacilitiesIncomeTaxRateReduction` appears at corporate 2646176;
form `rshshr-citr-l8-form` at 2475379 and grid
`rsh-citr-l8-form-grid1` at 2466694. Static captions, header, eight physical
body rows and footer occupy 2455650 through 2461260. Preserve their order,
duplicated turnover caption, blank number cells, source typo `peredararan`,
heading spans `[1,2]`, amount-row spans `[1,1,1]` and unit rowspans. The footer
caption is the visible `Jumlah PPh Terutang`, not the unused constants caption.
Keep the approved group, three columns and existing renderer.

Corporate imports `Qe=ye(97893)` at 412. Main module 97893 exports `Rx=>Ln` at
2321940; `Ln` at 2539928 is `I-Number(I%1000)` for Rupiah and
`Math.round(100*I)/100` otherwise. Captured shares pass through this mask in
`setFormData` (2463514). `changeValue` (2464100) recomputes from main taxable
income and research; turnover at most 4.8 billion selects the full-facility
branch. Tax is 11%/22% for 2020 onward and 12.5%/25% for earlier years.

The helper accepts only `ICT_RCIT`, `id-ID`, exact Rupiah headers and footer
spans, and numeric literal integer years 2020 through 2100. The original outer
`PeriodYear` must equal original `MainFormData.TaxYear`. The child uses the
**main** year (2477407), while the header uses the outer year. Missing, older,
encoded differently or mismatching main years stay unsupported.

The five root body operands, root `TotalIncomeTax`, main `TaxableIncome` and
main `TotalGrossIncomeResearch` must be explicit nonnegative integral JSON
numbers within 15 decimal digits. Displayed/calculated signed zero is
unsupported. Turnover must be at most 4.8 billion; research must be zero.
Reject unknown root fields and missing/null/string/boolean/unsafe operands.
Other main fields may remain present and unchanged.

The optional root `ExchangeRateValue` is a JSON number or null retained only
as unused source-control provenance. In this Rupiah branch it never becomes a
business field, an amount, an exchange-rate calculation or a fabricated mapping
count. Strings, booleans and containers remain unsupported.

Require captured granted share to equal `TaxableIncome-(TaxableIncome%1000)`
and captured other share to equal zero. Captured shares must already be mask
fixed points. Require captured granted tax to equal `(maskedMain//100)*11`,
captured other tax to equal zero, and captured total to equal both their sum
and the final consumer result. Never replace a mismatching reported value.

The binary64 constant for 0.11 is
`7926335344172073/72057594037927936`; its positive error from 11/100 is
`1/1801439850948198400`, relative `1/198158383604301824 < 2^-54`. For supported
nonzero multiples of 1,000, exact tax is an integer below `2^47`. The relative
upward half-ULP distance is at least `2^-54`, so nearest-even multiplication
rounds to that exact integer. Handle zero separately. The integer comparison
above keeps every intermediate within the declared precision bound.

## API, provenance and verification

`project_l8(form, *, main_form, period_year, headers, footer_spans, tax_type,
locale)` returns one canonical table and provenance. Keep all eight body rows,
one reported footer, owner/group, spans, pages=1 and truthful source counts.
Preserve original typed numeric tokens and paths for all root/main operands,
both years and an optional exchange control. Each captured amount has its exact
cell destination; both captured tax operands also name the footer total they
support, and contributing main operands declare all affected amount cells.
Outer year provenance is primary payload evidence, outside CurrentFormData.
The helper does not invent identity/header business fields.

The caller must separately prove loaded assets, current source and stable final
consumer inputs. `main_form` must be unchanged original CurrentFormData.MainFormData, never
recomputed values relabeled with original source paths. A native caller must
prove those original operands equal the stable final display inputs. It must
also prove that the effective grid exchange rate remains 1 throughout the
relevant Rupiah lifecycle. Optional captured `ExchangeRateValue` is not that
proof; the native caller graph remains an open requirement.

1. Independently review source proof, arithmetic, optional control and tests.
2. Publish synthetic tests first. Read all six actual test archives against the
   verified 5,589-case baseline; require intended missing-helper RED with no
   baseline/setup/teardown/collection failures before implementation.
3. Implement only this helper; preserve all existing projection functions,
   templates, resources, runtime allowlist, workflows, dependencies and LICENSE.
   Update AGENTS and architecture for the significant projection contract.
4. Run the unchanged full Windows and portable CI. Reconcile collection,
   identities, phases, results, measurements, metadata, hashes and sizes from
   all six archives. Read exact package/bootstrap artifacts and all 45 workers.
5. Obtain fresh independent review and review latest actual main plus the
   preceding other-session merge before merging the exact verified tree.

Saved/reopened tests must exercise final compaction, both literal Normal and
Amendment 002 workbooks, period/filename separation, all eight rows and footer,
three heading merges, exact numeric values, zero-decimal accounting, widths,
page setup, Audit counts, relative links and unchanged canonical sections.
All product imports, tests, fixtures and packages remain GitHub-runner-only.

## Native lifecycle obligations remain open

The independently reviewed pinned graph supports internal grid rate 1 for a
fresh grid that continuously stays on the literal Rupiah route. Grid constructor
2461972 initializes 1; `changeValue` 2464338 only assigns the external input for
non-Rupiah. The other two writes live inside its uncalled rate method. The grid
has no exported/query exposure; the parent exposes its own instance, binds the
separate rate input and never invokes the child's rate method. Inspected Angular
machinery invokes explicit hooks/declared inputs. This conditional source proof
does not supply the future owned-instance/route admission evidence.

Parent async exchange-rate resolution (2474208) still consults PERIOD/date/USD/
cache inputs. Its readiness, initialization/change/output fixed points and
parent/L6 feedback (2694002) need independent proof.
Main `CalculateTaxableIncome` (2827158) writes from fiscal income/carried-forward
without a submitted early return; research may be replaced by L13-B (2794046).
Additional handlers can zero deduction/vocation/carriage/research; their radio
handlers remain outside read-only capture actions. Initial outer and subsequent
current flags independently control L7/L13-A/L13-B visibility, including
IsInvestmentOtherIncome. Hiding these forms does not clear callback caches.
Research/root absence alone is therefore insufficient. These inputs cannot
inherit L7's separate NetIncomeBeforeTax invariant.
This helper alone never enables native L8, nor establishes full corporate
coverage, live acceptance, financial-PDF completion or Excel visual acceptance.

## Actual tests-first evidence

[Run 40017761585, attempt 1](https://github.com/cepeter-job/spt-downloader/actions/runs/40017761585)
tested merge `9a38c537a2ece72007ee3dfd65db3676bc447ecc`, tree
`f04873188b65eec5fb90220fa560efb4c7ac4704`, before any helper implementation.
All six downloaded inventory/JUnit archives reconcile hashes, sizes, run/attempt,
Python/platform/workload, complete collections, disjoint Windows partitions,
setup/call/teardown, full JUnit identities and measurement/suite totals.

The actual collection is 5,781 Windows cases (2,953 plus 2,828): all 5,589 baseline
cases passed, and exactly 192 new cases failed with the intended absent-helper
assertion. There were no errors or skips; all setup/teardown phases passed.
The 710 overlapping portable cases passed. Independent tests source review
accepted the original-year, captured-tax dependency and saved-export controls.
Implementation began only after this full actual RED was read and accepted.
Final GREEN, package readback and whole-branch review remain separate gates.

Implementation review found that a valid JSON exponent such as `1e1000000`
can raise Decimal Overflow in the shared converter before the L8 precision
gate. Add sixteen parsed-wire regression cases across the eight amount inputs
and both signs, plus an unused exchange-control preservation case. Keep all
original 192 tests and existing shared helpers unchanged. Read the actual
17-case extension (sixteen expected refusal-path failures and one pass) before
the narrow L8 repair; the complete expected collection is now 5,798. A candidate
run superseded by these tests does not establish GREEN or package success.
