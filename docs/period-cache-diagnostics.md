# Period-cache inspection preparation

## Scope
User requested preparation after the selection dialog expired. Prepare automatic, value-free metadata diagnostics inside the owned worker. Do not change the600-second consent deadline, auto-select returns, navigate extra pages, initiate reference API requests, install a build, or start a live inventory.

## Contract
- Preserve read_period_catalog(page) returning the original projected dictionary or None, and preserve planner/filter decisions.
- Emit finite catalog.read reasons for database/store/record absence and read/shape failures. Keep the existing read-only PERIOD/id-ID transaction and bounded lifetime; never create or mutate a database.
- Emit catalog.validation reasons distinguishing missing catalog, type/language/checksum/details, malformed expiry, expired/unbound time, malformed rows/code/label, duplicate codes and eligible metadata.
- Use the existing safe JSONL sink: finite enums and bounded counts only, no raw catalog, codes, labels, checksum, dates, URLs, identities, tax values, exception messages or credentials.
- Mark planning/recheck checkpoints. After inventory is saved, take exactly one best-effort cache snapshot before the selection dialog begins. This may establish a cache-availability transition, but must not replace the original plan or certify the cause of an earlier miss. Failure is diagnostic only; cancellation must still propagate.

## Verification
GitHub-runner-only RED/GREEN, existing full Windows/portable CI, read-only browser fixtures and privacy sentinels. Check cold/warm cache, database non-creation, mutation traps, no extra network/actions, unchanged inventory selection/filtering, post-snapshot failure and cancellation. Extend the existing frozen diagnostic self-test without changing its report schema. No local product imports/tests/build/EXE execution.

## Independent review constraints
Keep the Python reader signature and dictionary-or-None contract unchanged; any reason envelope stays internal. Cover enumeration/open races and late connection cleanup using real IndexedDB events: upgradeneeded, blocked and versionchange (not the reviewer's nonexistent upgrademaybe). Abort upgrade transactions and never create stores. Read-only transaction failures must remain distinct from missing metadata. Keep arbitrary exception text out of diagnostics, and retain cancellation before/after the final snapshot. A later available cache does not retroactively certify the initial plan.

## Runner evidence
RED run39360934516 at554e272:3170existing Windows tests passed and21new cases failed. Nineteen reached intended missing-diagnostic or missing-cancellation assertions. Two post-inventory cases failed early due to a test-only metric name error; corrected requests to submitted_requests without removing assertions. Those two failures are NOT counted as product RED evidence. Portable442passed. Production implementation follows the valid RED contracts; exact-head GREEN and frozen acceptance remain pending.

## Delivery boundary
A source/test change is not an installed diagnostic. Report exact PR/head/run and build verification; keep merge/install/live retry separate until approved. Do not ask the user to restart the app before the inspection path is verified and ready.
