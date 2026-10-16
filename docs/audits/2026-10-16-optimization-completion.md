# SPT Downloader optimization completion — 2026-10-16

## Disposition

The approved optimization batch comprises fixture ownership, executable workflow
contracts and a Windows two-shard evaluation. Fixture work is merged in
[#27](https://github.com/cepeter-job/spt-downloader/pull/27); [#28](https://github.com/cepeter-job/spt-downloader/pull/28) owns the contracts and this evaluation.
The finished decision is **retain serial Windows production tests**. Five
same-source comparisons establish a pytest-phase benefit, not the required 20%
complete-pipeline benefit. They also use more combined Windows runner time and
do not establish warm-cache behavior. No speculative production matrix is enabled.
This closes this evaluation with a conservative operating decision; it does not
claim that parallel execution can never be useful or that no future optimization
is possible.

No application behavior, runtime lock, native ownership/cancellation policy,
credential boundary, taxpayer handling, reference workbook or distribution
allowlist was changed by this batch. The separate native Masa work in #20 remains
independent. PR #26 merged during this work; its PPN implementation and added
behavioral tests were preserved rather than overwritten by a stale checkout.

## Shared fixture ownership

Before extraction, current-main tests had 58 direct imports from other test
modules, including module aliases. Fourteen focused `tests/support_*.py` owners
now hold those reusable builders and fixtures. Cross-test imports are zero.
The 733 existing source test definitions preserve their bodies, parameters,
decorators and assertions after import redirection. Reused GUI/Edge fixtures keep
their scopes and teardown; indirect browser dependencies remain explicitly
registered. Distinct PDF byte families, mutable simulator owner identity and
resource paths are preserved. Data-only helpers do not acquire Tk/Playwright
imports through unrelated GUI infrastructure.

The main integration at `1586eb970147be6ff871b1a582401a6d07f118ad` passed
[run 38867407074](https://github.com/cepeter-job/spt-downloader/actions/runs/38867407074): 1,477 Windows and 405 portable
cases, matching the pre-extraction inventories exactly. Its package artifact
`12031144332` was downloaded and verified against the
GitHub digest `sha256:9c4bdcd63882fe776321c9ce7f4321b2107b5762d2e79a7c2f074670ada556b9`, its SHA256SUMS and the exact
five-file allowlist. Source/frozen GUI, worker bootstrap and strict audit gates
passed. This is synthetic runner evidence, not authorized live taxpayer acceptance.

## Structural workflow contracts

Four whole-file YAML substring tests were replaced, not merely renamed. Their
surviving responsibilities are explicit: package dependency/order and artifact
identity, required aggregate execution, isolated benchmark scope, and per-job
failure diagnostics. Thirty-seven contract cases include current workflows,
invalid mutations and equivalent YAML formatting. All other behavioral test IDs
remain; Windows inventory is 1,510 and portable inventory is 438.

The removed-to-surviving contract mapping is explicit:

| Removed substring check | Surviving structural contract |
| --- | --- |
| `test_desktop_build.py::test_workflow_tests_builds_and_verifies_before_explicit_artifact_upload` | `test_current_production_workflow_preserves_real_gate_and_artifact_order` plus the broken-pipeline mutations |
| `test_ci_sharding.py::test_production_gate_and_artifact_validation_stay_in_place` | The same production contract checks the actual owning jobs, dependencies and step order |
| `test_ci_sharding.py::test_benchmark_workflow_is_opt_in_except_for_scoped_pr_validation` | `test_current_benchmark_is_isolated_and_keeps_the_complete_windows_contract` plus benchmark mutations |
| `test_ci_sharding.py::test_measurement_workflows_keep_production_serial_and_publish_failed_diagnostics` | `test_diagnostics_survive_attempted_test_failure_in_every_test_job`, per-upload guard mutations and actual-argv diagnostic cases |

The parser retains `on` as an event key and recognizes actual true/false booleans.
Duplicate keys are rejected, including merge overrides. Job checks bind to the
actual owner, not a matching string elsewhere. Critical Python commands must
execute directly without dead control flow or masked exits. Benchmark argv,
shard branch, matrix-mode binding and native exit propagation are one reviewed
PowerShell shape. Diagnostic arguments must reach the actual pytest invocation,
and each evidence upload retains its own failure guard. Permissions, source
self-test, build, checksum, upload and exact-ID readback order stay enforced.

Equivalent YAML block/flow layout, mapping order, dependency-list order and
expression wrappers are accepted. Quoted literal contents remain significant.
This is deliberately not a general Bash, PowerShell or Actions expression
interpreter; changing the reviewed command shape requires an explicit contract
review. Actionlint and the actual runner remain the execution authorities.

PyYAML 6.0.3 is pinned and hash-locked in test/build environments only. All existing
pins are preserved. Runtime and audit locks are byte-identical to the baseline;
PyYAML is not added to the application's runtime dependency contract. The new
contract file is explicitly included in the portable test manifest.

Initial contracts failed before implementation in run `38864730084`, portable
job `116854869296`, with `Structured workflow contracts are missing`.
Independent review counterexamples were then reproduced in run `38866000709`
and the matrix-binding case in `38866892606` before their fixes. Superseded RED
runs are never counted as successful verification or benchmark observations.
Final source review approved the corrected contracts. The reviewed main-merge
head `ea464d0e5aa27b0ce805f74927fcbedfa4a7e4e6` has exactly the same tracked tree
as benchmark implementation `ea5f0da1093cd85c567b9ebedfe5793abafa05a5`.

## Five matched-source Windows comparisons

All five comparisons use the exact source commit
`ea5f0da1093cd85c567b9ebedfe5793abafa05a5`, CPython 3.14.8, Windows 2022 and the
same test lock and existing benchmark workflow. At most three comparisons ran
concurrently. Each comparison uses three independent runners: full serial suite,
shard 0 and shard 1; each runner still uses a single serial pytest process.
No live accounts, tax records or private browser profiles are used.

Every comparison passed. Each serial run executes 1,510 cases; each shard executes
755. The shard sets are disjoint and their union equals the serial inventory,
which is also identical across all five comparisons. JUnit has no failures,
errors or skips. Archive digests were checked before reading each manifest,
measurement report and JUnit file. Exact artifact/run/source identity is retained
in the evidence metadata.

| Run | Cache requested | Serial pytest (s) | Longest shard pytest (s) | Phase reduction | Serial job (s) | Both shard jobs, sum (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| [38867218437](https://github.com/cepeter-job/spt-downloader/actions/runs/38867218437) | restore | 326.72 | 198.52 | 39.2% | 354 | 428 |
| [38867217987](https://github.com/cepeter-job/spt-downloader/actions/runs/38867217987) | cold | 263.23 | 220.30 | 16.3% | 282 | 466 |
| [38867218475](https://github.com/cepeter-job/spt-downloader/actions/runs/38867218475) | restore | 334.74 | 197.26 | 41.1% | 359 | 423 |
| [38867824735](https://github.com/cepeter-job/spt-downloader/actions/runs/38867824735) | cold | 334.94 | 192.90 | 42.4% | 356 | 391 |
| [38867941690](https://github.com/cepeter-job/spt-downloader/actions/runs/38867941690) | restore | 314.38 | 173.10 | 44.9% | 340 | 395 |

The following medians retain the requested modes separately. The reduction
column is the median of per-comparison percentages, not a percentage calculated
from two independent medians.

| Requested mode | Comparisons | Serial setup + pytest (s) | Shard setup + pytest critical path (s) | Median phase reduction | Median runner-time increase |
| --- | ---: | ---: | ---: | ---: | ---: |
| all | 5 | 333.26 | 202.70 | 40.3% | +17.8% |
| restore | 3 | 333.26 | 202.70 | 40.3% | +17.8% |
| cold | 2 | 304.01 | 212.60 | 28.5% | +37.5% |

**Cache limitation:** all requested restore jobs reported `cache_hit=false` and
`python_cache_hit=false`. Cold jobs disabled uv restore and also reported no
Python cache hit. Therefore these are cache-miss observations under different
requested modes, not a controlled warm-versus-cold comparison. Runner hardware,
network and queue variation were not controlled. Five observations do not prove
a latency service-level objective or absence of intermittent failures.

Setup + pytest excludes queue/checkout, evidence upload, fresh-worker bootstrap,
packaging, exact artifact readback and main-only provenance. Serial job durations
and summed shard job durations include their own setup/checkout/upload, but do
not turn the optional benchmark into the complete production pipeline. The full
benchmark elapsed time also includes the serial control and comparison job, so
it is not a candidate production-CI elapsed time. No projected packaging or
attestation time is represented as measured sharded-CI performance.

**Decision:** keep the production job serial. The data does not clear the already
adopted gate of at least 20% lower median end-to-end candidate CI time, and each
comparison consumes more aggregate Windows runner time with two shards. This
batch does not waive that requirement, add a partially verified matrix, or leave
an unmerged sharding implementation behind. The existing optional benchmark stays
available; the completed evaluation does not promise a production speedup.

## Reproducible evidence

The comparison artifacts below contain the machine-readable measured values;
each run also retains the three inventories and corresponding JUnit/measurement
artifacts. Artifact retention remains the existing seven days. Source and this
summary remain committed; expired artifacts are not represented as permanently
available downloads.

| Run | Comparison artifact | Verified archive digest |
| --- | --- | --- |
| `38867218437` | `12032395339` | `sha256:8775e92a0c0111d23c3bc19457e5f0097fd6650290fec613d92137b638a4fee9` |
| `38867217987` | `12031952211` | `sha256:d0aaa868dd8270737eaf1c7cafdb6e990988c36c68690ad8babcdc8a61d8d93b` |
| `38867218475` | `12031713695` | `sha256:6fe857fed1f7aef501081b3b892f7d30ce3355819f9e400b936e4dc33be92424` |
| `38867824735` | `12032038236` | `sha256:4b58162094c398302ee3e4fe98aa7f5b6dddfb5d31c4df8a0cbb7e1eb0ef329c` |
| `38867941690` | `12032108065` | `sha256:c6ca9f2f7334adf2ecda378f66d455db27ca9e097d32c441ee6ee29657e88192` |

The actual serial production workflow at the same implementation source passed
[run 38867143415](https://github.com/cepeter-job/spt-downloader/actions/runs/38867143415). The current-main integration
passed [PR run 38867512896](https://github.com/cepeter-job/spt-downloader/actions/runs/38867512896), including native/Tk/Edge,
worker preparation, source/frozen self-tests, strict dependency audit and exact
artifact readback. The latter's package artifact is
`12032341257`, archive digest
`sha256:035f8cdf2edc955a73f9669c4d4101944232a25d7134ef2b9d623d380928799f`. The five-file distribution remains
`SPTDownloader.exe`, `LICENSE.txt`, `README.txt`, `build-selftest.json` and
`SHA256SUMS.txt`. These are executable verification results, not a released or
Authenticode-signed product claim.

Independent automated source reviews covered fixture identity/lifetimes, the
incoming PPN refresh, unused-import cleanup, workflow mutation gaps and their
corrections. The final evidence review checks the raw measurements and limitations.
These reviews are not independent human tax-output acceptance.

The final evidence commit changes documentation only; its complete fresh-head
CI, exact merge SHA/tree and post-merge main verification are recorded in PR #28
rather than preclaimed here. No release or deployment is part of this completion.
