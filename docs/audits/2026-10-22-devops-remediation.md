# DevOps audit remediation map

Repository: [cepeter-job/spt-downloader](https://github.com/cepeter-job/spt-downloader).
Implementation and current verification: [PR #72](https://github.com/cepeter-job/spt-downloader/pull/72).
Historical baseline: [22 October audit](2026-10-22-devops-audit.md).

The baseline audit is retained unchanged in substance. This document maps its
findings to implementation and acceptance evidence; it does not relabel external
or unobserved controls as passed. The PR checklist and checks on its current head
are the final verification record.

## Finding checklist

| Finding | Repository change | Required acceptance evidence |
| --- | --- | --- |
| F1: interrupted cancellation checkpoint | Worker uses the atomic checkpoint writer; persistence failure preserves previous bytes and CANCELLED. | Actual partial write/ENOSPC and replace failures; old aggregate/detail bytes intact; offline rebuild; one cancellation terminal. |
| F2: abandoned temporary login profiles | `profile_lifecycle.py` records exact ownership and holds an OS lease; bounded parent cleanup runs outside the GUI thread. | Active lease retained; real owned process death recovered; unowned, malformed, shared, redirected, locked and default profiles preserved. |
| F3: ambient packaged bootstrap | Frozen mode requires bundled uv; inherited uv policy/config is removed while reviewed network trust settings remain. | Contaminated PATH/config/env and missing/wrong bundle cases; cold setup and reuse from actual downloaded EXE. |
| F4: artifact expiry and no durable rollback | Opt-in verified promotion retains original ZIP, build coordinates, manifest, component inventory and provenance bundles; rollback verifies retained assets. | Synthetic full promotion preparation, API-compatible draft/readback/publish ordering, tag-change refusal and post-expiry retained-byte verification. Actual first release remains a separate post-merge action. |
| F5: documentation push cancels main build | Main push concurrency includes unique run identity; superseded PR runs still cancel. | Workflow contract validates distinct code/documentation main runs and unchanged required gate. |
| F6: desktop subset widens on CLI resume | `selection.json` binds exact inventory bytes, scope, source order and capture mode; legacy ambiguous desktop continuation fails closed. | Prefix/non-prefix/reordered selections, actual ordinal checkpoint reuse, tampered inventory/mode and no first-detail-before-manifest. |
| F7: frozen GUI check does not exercise real bootstrap | Exact artifact-ID readback EXE runs an explicit account-free cold/reuse/cancellation test in fresh owned storage. | Executable digest, embedded/worker build coordinates, complete resources/imports, managed interpreter and both owned process handles terminated. |
| F8: no restart publication journal | Private backup flush and journal/notice precede every original-file move; explicit native recovery checks scope, directory identities and actual bytes. | Real process death at displacement/install/index, repeat recovery, second death during restoration, changed output/backup/target refusal and handle-held cleanup custody. |

## Other partial controls addressed

The test inventory now requires one successful setup, call and teardown for every
selected test, rejecting skips, xfails, missing and duplicate outcomes. All uv CI
bootstrap downloads carry reviewed platform archive digests. Distribution gains
strict public build metadata and an inventory of actual native components and
locked worker packages; the inventory states its vulnerability-coverage limits.
Diagnostics include only validated public build coordinates. Private disclosure,
storage maintenance, explicit publication recovery and release/rollback procedures
have maintained documentation and named responsibility.

## Verification method

The tests-only checkpoint `ed1df6cd494ee84f49118eabf4845aa6f81f1f4b` ran in
[run 39712684141](https://github.com/cepeter-job/spt-downloader/actions/runs/39712684141).
It reproduced the missing behavior before production implementation: portable
45 failed / 567 passed; Windows partitions 65 failed / 1,826 passed and
43 failed / 1,772 passed. Independent review then added regression coverage for
native cleanup custody, recovery interrupted during backup reconstruction, strict
release API behavior and last-moment tag changes.

All product imports, pytest, native/Tk/browser fixtures, source/frozen tests,
builds and EXE execution run on GitHub runners. Local AST parsing and source/hash
inspection are supporting checks, not behavioral execution evidence. No live
portal account, taxpayer capture, credential or private output is used.

## Controls requiring evidence outside this PR

| Control | Remaining prerequisite |
| --- | --- |
| Authenticode publisher trust | Obtain an approved signing identity and validate timestamping/trust on target Windows endpoints. Current unsigned status remains explicit. |
| First durable production release | Successful trusted-main seven-file build after merge, followed by a separately authorized verified promotion. No release is published by this remediation task. |
| Administrative security and alert handling | Verify private security settings, backlog, routing and actual notification delivery with authorized administrative access. A restricted API response does not establish configuration. |
| Endpoint confidentiality and restore | Validate actual ACLs, encryption, Downloads synchronization, capacity, retention consent and backup restore on approved endpoints. |
| Live source acceptance | An authorized operator checks the supported portal layouts and resulting Excel/PDF scope. Synthetic runner success does not substitute for this acceptance. |

No merge, production release, certificate issuance or endpoint configuration is
claimed merely because implementation and documentation are present.
