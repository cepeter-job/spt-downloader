# DOM L7 period binding and list recovery

The operator requested fixes, a reviewed PR and merge after the private audit
found a captured L7 table missing from its workbook and one return skipped when
the submitted list did not emit a verifiable response. Private captures stay
outside Git; fixtures use synthetic records and amounts only.

## Bounded approach

- Keep the current L7 renderer and approved resource. Accept the exact annual
  source code `0112YYYY` alongside the existing exact `Januari - Desember YYYY`
  caption. Require the captured year header and every existing table/footer
  binding check. Preserve literal period/model metadata and source values.
  Monthly, partial-year and malformed codes remain unsupported.
- Retry the initial inspected submitted-list navigation once, only when the
  list observer times out without a new verifiable response. Use a distinct
  RuntimeError subtype to avoid retrying other failures. Each attempt retains
  the existing 60-second navigation and 45-second response bounds, a fresh
  monotonic response marker, the same source URL/filter and Stop checks.
  Recheck the owned taxpayer/list route before retrying. A known identity or
  authorization contradiction, unsuccessful response, navigation error or Stop
  is never converted into a retry. Exhaustion remains PARTIAL.

The existing exact record, metadata, paginator/page-size/filter and selected
View checks still run after a successful response. No retry of a detail action,
financial POST or document download is introduced. The 30-second panel budget,
native eligibility, authentication permissions and approved clean layouts stay
unchanged. The user has classified extra Induk fields as redundant; adding their
destinations is outside this change.

The initial CI dependency audit independently found six filelock advisories and
one setuptools advisory in the existing locks. Add only the patched exact pins
filelock4.2.1 (audit) and setuptools84.1.0 (build), regenerate universal hashed
locks with uv0.13.4 and retain the existing strict audit/freshness jobs. Runtime
and test dependency versions and all CI policies stay unchanged.

## Alternatives considered

Increasing every timeout leaves a one-off missing response unrecovered and adds
delay to unrelated operations. Retrying all RuntimeError failures can conceal
identity or authorization failures. Reusing cached list rows cannot establish
fresh ownership. The narrow timeout subtype and one fresh navigation preserve
the existing verification gates while recovering the observed failure class.

## Evidence

First observe failing synthetic saved-export and browser-protocol regressions
on GitHub runners; then implement and run the unchanged full Windows suite and
portable subset. Review the preceding other-session merges and latest main,
obtain one fresh whole-branch review, and merge only the tested green candidate.
Local work is source/AST and artifact/OOXML metadata inspection only. No private
capture is uploaded and no live scrape is claimed by synthetic CI.
