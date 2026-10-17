# PR30 integration ledger

## Scope

Finish native PPN JSON delivery only after inventory PR34 is merged. Preserve literal source identities/amendments and submitted monetary values. Keep other tax dispatch unchanged. Synthetic tests, builds and self-tests run on GitHub only; previously authorized bounded live acceptance is separate from those tests and must preserve prior outputs.

## Verified prerequisite

PR34 merged as `10b0da677c17dec7619bc5ed6ee36f52228bc614`. Its tree `2367081e4c2cca8eb601481f8f7e27f7da067498` matches final runner head `0375cd4` / merge ref `e0f4d2a`. Build run `39014881946`, serial/sharded benchmark `39014881949`, package artifact `12094755934` and Windows JUnit `12094950215` passed/verified. The bounded live submitted-list comparison selected the same record/period/model set with both candidate partitions as the full baseline. This was source-protocol evidence, not a native Excel completion claim.

## Integration rulings

- Merge main into existing native head `c96bc35`, preserving recovery history rather than rebasing or discarding audited native work.
- Preserve the auto-merged browser changes from both sides: guarded inventory filter/replay from main and native PPN identity binding/dispatch from PR30. Keep both module families in the managed-worker allowlist.
- Resolve the binary template conflict in favor of the current main template, not the older native-branch copy. Read-only ZIP/XML comparison showed that main includes the B2 J7 border fix plus later reviewed A2/B3 last-body-row border fixes and B2 default alignment/non-money format corrections. Its literal values are not replaced by native tax data. Keep matching resource/fixture bytes and their existing main digest/style contracts.
- Retain all main numeric/layout regressions, including 15-digit precision, non-money text/format preservation and body-count contradictions. Native adapter, binding, observer, projection and template-renderer source files remain unchanged from `c96bc35` at this integration.
- Add combined-interface regressions for PPN identity under year-contains and source-code OR filters, preserving literal amendment values and original-body hash, and rejecting contradictory candidate filters before fallback.

## Remaining gates

Fresh combined CI and independent integration review; bounded native acceptance of the previously selected January amendment with actual COMPLETE, used=json and complete seven-form mapping; read-only workbook/source comparison and unchanged prior files; final exact-tree checks, resolved review threads and protected merge. Do not infer a completed native export from the earlier PARTIAL run.
