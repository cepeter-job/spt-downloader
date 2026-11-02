# Bounded MPN reference acquisition

Status: approved by the operator on 2026-11-03, including the bounded live GET,
implementation, review, CI, merge and artifact delivery. Base main:
1dea7445a6b1f522a522419cdf63a2709300503a.

## Problem and observed evidence

The November 2 live job reached the final owned, unfiltered id-ID MPN list, then
failed parent binding with three unavailable reference inventories. The date
clear fix passed its gate; MPN remained incomplete. The complete private job
and sanitized audit are held locally, outside source control.

The operator subsequently opened Accounting for investigation. Ordinary
same-scope search/selection, ledger navigation, first Search, one inspected
date Clear and final Search produced a 200 original list response with only
IsCancelled/equals/0. No Detail, Print, Reconcile or business mutation was used.
The live provider bodies match the existing pins:

- main.fedea3c4d025195e.js:
  7a76f131ac13b124087c4c968154d0f73c26a92069dc8d6dd59791f908d4bdf1
- vendor.5900c4ddec796b87.js:
  b876e4421e8d8caa81b98928f23e672e5da7069fa7ab30ab14318b5f3726af5c

The observed reference GETs were ShowZeroValue, IsDebitIsCredit and
ShowCancelledTransaction; these are preparation dropdowns, not the four
business catalogs. Their presence explains why a broad path_variant diagnostic
does not establish a new business-catalog route. Earlier long CDP histories
were retention-truncated; do not certify them as a complete negative search.
The clear/final-Search response waits were individually untruncated.

Pinned source loadBulkReferenceData/internalLoadBulkReferenceData reads existing
reference entries, removes already-present types, and constructs a GET for the
remaining types, optionally with checksums. Consequently ordinary navigation
does not guarantee a fresh four-type packet. This is source evidence for the
cache branch, not permission to inspect live cache contents. No IndexedDB,
localStorage, sessionStorage, tokens or cached catalog contents were read.

REA MCP tools were absent. These findings come from supported browser/CDP
observation and static original-source inspection, not a fabricated REA result.

## Required explicit boundary decision

AGENTS.md currently requires original same-attempt reference bytes and says:
"no cache clock/version selection or extra catalog fetch is admitted."
This proposal preserves the first requirements and requests one narrow
exception for an adapter-owned reference GET. The operator approved that exception.

## Recommended approach

Keep passive observation as the first source. When a nonempty owned parent
needs labels that have not been captured, permit at most one explicit GET per
MPN attempt to the already reviewed exact endpoint:

`https://coretax.intranet.pajak.go.id/referencedata/api/currentreferencedata/id-ID/ACCOUNTING_TYPE,ACCOUNTING_TYPE_DETAIL,REVENUE_CHART_OF_ACCOUNTS_6_DIGITS_SEGMENT,PERIOD`

The request contains only the fixed locale/type names; no taxpayer identifier,
period, amount, body or arbitrary query. Use the existing owned authenticated
context without extracting credential material. It does not grant any POST,
alternate endpoint, locale, checksum suffix, retry, redirect or document action.

Before issuing it, require the verified owned Service-Worker-blocked context,
both loaded provider pins, retained current Document/attempt/literal ledger,
selected-scope original list query, Stop and no sticky source/observer failure.
Do not duplicate an already pending admitted catalog request. Preserve the
existing pending-source wait before deciding that acquisition is needed.

Use one bounded 5-second transaction and the existing 8 MiB source-body allowance,
with no redirects/retries. Reconcile Stop, Document/source failures and the
deadline around transport/body/validation RPCs, including exceptional exits.
Only status 200 at the exact endpoint and original JSON bytes are candidates.
Reuse the existing exact four-type envelope, id-ID, unique-code, explicit-null
ValidTo, checksum and snapshot validation. Changed snapshots remain fatal.
An unavailable/unsupported acquisition stays PARTIAL and authorizes no Detail.

Keep the final parent comparison intact. Acquisition must precede that
comparison; never catch or demote a genuine MpnSafetyError to obtain a label.
Known identity/field contradictions remain fatal. Preserve raw-code bindings
that are already independently sufficient; do not add a request to empty
inventories or successful existing bindings merely to obtain metadata.

Retain accepted original bytes under the existing private MPN attempt only.
Declare the acquisition actor separately from passively observed app traffic;
do not invent a browser Request or claim a synthetic event was observed.
Missing origin metadata keeps old checkpoints readable; reject unknown explicit
origins. Bind new origin metadata to evidence validation and source projection.
No taxpayer data, raw captures or authentication material belongs in Git.

## Alternative considered

A separate clean Accounting profile with normal reauthentication could reduce
cache reuse, but changes browser/authentication lifecycle and may add operator
login. It also needs proof of exactly when the four catalogs load. Prefer the
bounded fixed GET over profile isolation for this repair. Reading browser cache,
clearing it to force a fetch, guessing labels, or weakening parent identity is
outside both approaches.

## Approval and validation gates

Approval covers the single fixed live GET experiment and this narrowly scoped
implementation, followed by an implementation plan, synthetic runner tests,
independent review, latest-main/preceding-merge review, PR and merge only after
exact-head CI, then verified main-package delivery. It changes the quoted
AGENTS.md boundary only for this declared acquisition.

First verify the actual approved response and compare the three displayed
labels against original same-scope parent codes without exposing private data.
An unsupported response ends that experiment; do not probe alternate URLs.
Runner behavior tests must cover warm-cache missing packets, no unnecessary or
duplicate GET, exact source/endpoint ownership, timeout/redirect/status/size and
payload refusals, callback-pumped Stop/fatal failures, unchanged contradictions,
legacy checkpoint reads, original-byte custody and final publication gates.
CI/package success does not establish build-matched live MPN acceptance.
L3-B performance remains a separate active task.

## Approved live experiment

The single approved GET returned status 200 at the exact endpoint in 1025.1 ms,
with 5,742,869 original bytes and application/json content type. It supplied
exactly the four required groups, valid checksums, no explicit locale
contradictions and no duplicate codes. The retained Accounting Document and
literal ledger remained current. All seven parent-binding columns matched on
all ten displayed original-response rows after applying these labels.
No Detail action, cache read/clear, token extraction, alternate GET or retry
was performed. The manual page had no controlling Service Worker; this is
diagnostic browser evidence, not proof of the product's blocked-context gate,
full capture, publication or build-matched live acceptance.
