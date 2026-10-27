# Bounded corporate L3-B DOM pagination

The operator's audit identifies corporate L3 table 3 as the slow stage: 4,654
body rows over 47 DOM pages. The existing DOM chooser caps actual dropdown
options at 100. The reviewed corporate bundle with SHA-256
`fcd6d4a9244d6562a294675e802732562a9510621fbb9abbe651fa4de143048d`
sets L3-B `RowsPerPageOptions` to `[10,25,50,100,250,500]` beside its
`WithholdingSlipsDate` ascending sort configuration.

Allow a maximum of 500 only for a selected `PPh Badan` detail, exact `L3` tab,
and the existing structure observer's exact `rshshr-citr-l3-grid2` owner with
the sole group `B. PPh YANG DIPOTONG/DIPUNGUT PIHAK LAIN`. Select only an actual
visible numeric dropdown option; if unavailable retain the existing smaller
option behavior. An already selected maximum must not cause another load.
All other callers keep the existing maximum of 100. Do not add output metadata
or grant native JSON eligibility from this presentation/transport optimization.

Preserve row order, duplicates, zero values, footer-once capture, page limits,
Stop, owned paginator checks, state progress and final source-count reconciliation.
No direct requests, guessed sizes, concurrent pagination or shorter readiness
deadlines are permitted. MPN, PDF, other tax types and workbook layouts are out
of scope. A successful table does not certify capture, PDF or whole-job completion.

Runtime and browser tests run on GitHub runners only, with synthetic local pages.
A paired synthetic test must prove identical rows/footer with 47 default pages
and 10 owned corporate pages. This proves reduced transitions, not a live elapsed
time guarantee; live server timing requires a later operator run.
