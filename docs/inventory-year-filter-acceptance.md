# Inventory year-filter acceptance

Production implementation `023744d` passed Windows integration (1675 JUnit cases without failures), portable tests, dependency audit and source/frozen packaging in run `39010597956`. The downloaded Windows package and JUnit archive digests, package payload manifest and frozen safety metadata were checked without executing the product locally. Subsequent test-only review cleanup requires fresh final-head checks.

## Source-protocol comparison

An authorized bounded comparison reconciled a complete 600-record submitted baseline against both candidate partitions for one requested period year. Both selected the exact same 57 record identities, literal period codes and amendment models. At the observed 50-row page size, baseline pagination needed 12 listing requests and optimized candidates needed 3. The full source cache held 12989 unique codes; its 66-value extra partition returned HTTP 200 with zero matching records. All response taxpayer bindings matched. The catalog stayed unchanged, and the original displayed January filter remained accurate. The comparison issued 17 list requests plus two restoration requests; no details or exports were opened.

This is source-protocol acceptance, not local execution of the shipped collector or proof that every status endpoint is optimized. Nonempty cross-year partitions, fallback, cancellation and selected-row restoration are covered by synthetic runner contracts; the extra partition was empty in this live dataset. Private identifiers, captures and original outputs remain outside the repository.

## Review and remaining final-revision gate

Independent integration review found no blocker. A second reviewer timed out and is not counted as an approval; the parent inspected the planner and validator contracts directly. Two automated review comments identified unused imports in the new tests; the cleanup changes no production behavior.

A separate serial benchmark at `023744d` reported `test_blocked_post_login_requests_are_counted_without_private_values` failing its diagnostic-category deduplication assertion, despite passing primary Windows and both shard runs. This result is not hidden or treated as passed: inspect the failure and require fresh final-revision evidence before merge. Preserve repository protections and resolve only review threads whose findings are actually addressed.
