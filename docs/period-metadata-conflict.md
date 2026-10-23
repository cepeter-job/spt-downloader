# Source-proven period aliases in inventory and restoration

## Problem
The same source RecordId can be displayed as a raw period code in one status list and a textual period label in another. Literal deduplication correctly rejects that mismatch unless independent source evidence establishes equivalence. Never derive a label from code digits, normalize the saved metadata, or ignore other conflicting fields.

## Contract
Allow a code/label pair only through a fresh, valid PERIOD/id-ID catalog using the existing planner validation, with unique code and unique unambiguous label. Preserve the first record and its source location, and retain an independent literal metadata copy for every source occurrence. Record the exact pair and raw/semantic catalog hashes as private checkpoint evidence, never diagnostic values.

Read the existing browser cache only when pending records have differing period literals for the same ID, before deduplication. Save the catalog snapshot privately if a mapping was used; cancellation brackets the read and original inputs/checkpoints remain unchanged. No network request, extra navigation or cache write. Missing, expired, ambiguous or contradictory evidence still rejects the conflict.

For detail restoration, allow the same proven pair only if the current readonly catalog remains valid and matches the recorded semantic binding. Keep RecordId/source-page and all other metadata checks intact. Do not manufacture native source_fields or source_identity for DOM fallback.

A new submitted-only inventory may observe a literal code before the catalog loads and its label when restoring the same return. Without a prior alias proof, this exception requires one unchanged `SPT Dilaporkan` occurrence, matching original source location and metadata, plus a fresh unique catalog pair whose code equals `TaxPeriodCode` on the restored same-ID, same-taxpayer API row. All other checked metadata must still match. Save the full catalog in a new exclusive private restoration snapshot and retain its proof; never rewrite the saved period, occurrence metadata or inventory batches. Missing, stale, ambiguous or contradictory evidence prevents View. A legacy multi-occurrence checkpoint without its original proof does not gain this exception.

If the previous published folder already contains that return ID under a different literal-period filename, validate its physical workbook scope, index links and all declared COMPLETE PDF bytes before choosing a separate final folder. Preserve the entire old folder and publish only the new run's declared files, with its actual COMPLETE/PARTIAL status and relative links. Do not combine duplicate IDs in one resume, normalize period filenames, or treat the separate folders as proof that their periods are equivalent. A changed tax/model identity, corrupt old proof or invalid PDF is still an error. Ordinary same-filename replacement still requires overwrite consent.

## Verification and scope
Synthetic tests only on GitHub runners: both occurrence orders, unmodified literals, deep-copy custody, late catalog availability, missing/changed API period codes, missing/expired/ambiguous catalogs, genuine period/model/receipt conflicts, distinct amendment IDs, collector reconciliation and restored-detail safety/Stop. Publication cases preserve old workbook/PDF bytes and verify separate literal-period links, invalid prior scope/PDF rejection, partial captures and ordinary overwrite consent. No private tax fixtures. Runner validation does not establish live-account acceptance.
