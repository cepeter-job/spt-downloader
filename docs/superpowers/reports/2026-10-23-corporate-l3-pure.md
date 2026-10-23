# Source-bound pure corporate L3 projection

[PR107](https://github.com/cepeter-job/spt-downloader/pull/107) merged as
`1081dbf2aee33073af6c3852ae9a3a5f8e74fec3`, tree
`af17962da789629f96933b76369319aec6878f9e`. This supplies the pure current-form
transformation; native observation, source transport and dispatch have separate
implementation and verification gates.

The bounded Rupiah branch consumes current
`ListIncomeTaxWithheldByOtherParties`, complete normalized B pages, an actual
captured footer payload and explicitly bound labels. It preserves leading zeroes,
duplicate rows, original numeric lexemes, typed source paths and page-local
row numbers. Active B uses IncomeTax and plural WithholdingSlipsNumber/Date.
Captured footer TaxBase/IncomeTax/IncomeTaxUsd is authoritative independently
of B body sums and stale saved controls. Ordered integral arithmetic checks
every intermediate, overseas-credit subtraction and visible/hidden total.

Both standalone controls remain canonical and unresolved in the mapping audit;
their template slots have not been approved. The saved compact form retains all
three B footer rows with the approved spans and zero-decimal accounting. Source
captures and the binary reference resource remain unchanged. Whole Induk, PDFs,
other forms, run completion and live corporate acceptance remain independent.

The original35-case tests-first run39966057016 reconciled4961 Windows cases:
4926 baseline passes and35 intended missing-helper failures. Source review then
identified an empty-date distinction. Offline A explicitly converts an empty
date to blank; active B does not. Three new controls were added before correction.
Review-RED39975526656 at merge
`f71dd46e12396ab252c6e447b0b2edbd30a24d82` reconciled5028 Windows cases:
5027 passes and exactly one B-empty-date failure, zero errors/skips. All six
archives were read before the correction, and fresh source review closed it.

[Final run39978370654, attempt1](https://github.com/cepeter-job/spt-downloader/actions/runs/39978370654)
tested published head `d55ad074e3a1b03e187aa914cd742c14256cefdf` as merge
`f9d423cb1be90c545e5028a5d7c2b47675aef211`, with the same tree as the actual
merge. All5028 distinct Windows cases passed in disjoint shards2570+2458,
including all4990 baseline cases and38 continuation cases, zero failures/errors/
skips. The710 portable passes overlap Windows. Complete inventories, outcome
phases, JUnit identities, metadata and all archive hashes were reconciled.

| Downloaded archive | Artifact ID | SHA256 |
| --- | ---: | --- |
| Windows shard0 JUnit | 12513312137 | `3b736e5efb5e5db0a2864dd5e4843ddc3002e95d1c4fd706e712d9906c12b4c2` |
| Windows shard0 inventory | 12513745946 | `88b39c547253c233947e53071b05406cccd12a000af7cb3a29f7449a6dd07b9f` |
| Windows shard1 JUnit | 12513671268 | `b462e462e44e79066b77c65e070929bd14727c5f541ae0bb0eb3ace3a3141cb6` |
| Windows shard1 inventory | 12513042544 | `21464cc0af634890188e701073b07bbdc1300f357cacd529d5c297afb61f7b23` |
| Portable JUnit | 12511959224 | `f1292ec9d4f4f6a9e4ece86f1cf08bf2d8a359b03db992bb23d3d9217b28a56a` |
| Portable inventory | 12512451457 | `c9e22170f3d5566b03f121636aa31bd696f62355675dbf758fc6f585cbca04d6` |
| Windows distribution | 12512977563 | `3a24c9ef2c879de06773673eb0bf2ebc55dfe02cdb2d9ca9a258dd21c31167e1` |
| Bootstrap evidence | 12513606335 | `830988f3d398a0d3559c58a4201899e1db31d3da460c9d51713004f966c25bb8` |

The distribution executable SHA256 is
`4ef5bd4080d98485109d37899ab4a71d4349213f6fee15459cec40ace698885c`.
Downloaded package/manifest/build identity/SBOM/runtime-lock metadata, all45
worker sources and source/frozen/bootstrap evidence match the exact candidate.
Runner cold-install, reuse, cancellation and owned cleanup checks passed. Required
Actions and CodeQL checks passed; existing PR-policy provenance/cleanup skips
were unchanged. No local product/test/EXE execution or live corporate claim was
used. Immediately before merge, main and the preceding other-session PR101
interaction were refreshed; the actual merged tree was independently read back.
