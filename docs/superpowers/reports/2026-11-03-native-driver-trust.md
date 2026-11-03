# Native Windows driver trust verification

The latest live main97f job reached the correct MPN unfiltered original list
but refused catalog acquisition on a Playwright transport failure. Its log
does not expose the original error. Generic handshake-only diagnostics on the
operator machine found Windows TLS success, Node default failure with
UNABLE_TO_VERIFY_LEAF_SIGNATURE, and Node system-CA success. These probes used
no HTTP, credentials or certificate installation, and kept verification enabled.

The installed pinned driver reports Node24.22.1 via executable version metadata.
The supported NODE_USE_SYSTEM_CA option reads the existing system trust store:
https://nodejs.org/api/cli.html#node_use_system_ca1

The new stdlib-only coretax_transport manager temporarily defaults that option
only during new Windows driver entry, preserves explicit pre-existing values
and different-value updates, and delegates exit unchanged. Same-value writes
during entry cannot be distinguished from the owned temporary default. CLI
and desktop retain local factories; CLI cleanup remains registered before entry.
The explicit managed/frozen worker resource list includes the new module.

There are no changes to TLS verification, proxy settings, trusted certificates
on the operator machine, the approved one-GET allowance, endpoints/locales,
source pins, Document/scope, deadlines, size, redirects/retries, original-byte
custody, PARTIAL or publication gates. A driver startup option is not new
authorization for any remote request.

## Runner regression evidence

The first RED run41554919414 reproduced the missing manager/resource behavior.
The real TLS fixture then needed isolated runner setup corrections: native PS
module lookup, a noninteractive trust store, and guaranteed ownership cleanup.
It now uses .NET ephemeral RSA, writes its public CER before trust insertion,
and adds only that public certificate to the disposable hosted runner's root
store. It creates no persistent My/private key entry. Cleanup surrounds setup,
timeouts, output parsing and server teardown; it matches the exact synthetic
subject nonce/thumbprint/bytes, verifies removal and removes generated files.

GREEN run41557885238 at6fddac7db5fb78a3fe4cec03a427204865431dea passed51
cases without failure/error/skip. Artifact13194399544 was hash/ZIP/JUnit checked;
SHA-25643eb6a82fc4dc905dd1b8161d39083b53cbbe7b917664ecb21f708005e603219.
This includes real APIRequestContext HTTPS: bundled-default trust rejects the
synthetic root, the owned native-trust driver accepts it, and hostname mismatch
still fails. Unit cases cover explicit overrides, non-Windows behavior, nested
and concurrent starts, startup exceptions/Stop, exit semantics, CLI partial
acquisition cleanup, desktop authentication refusal, and unrelated network env.

Independent source review resolved one material fixture-cleanup issue and
found no remaining Critical/Important issues at6fddac7. Its minor same-value
environment limitation is documented. The temporary probe is removed from the
final candidate. Full exact-head CI, preceding-merge review and exact-main
artifact verification remain separate merge/release gates.

This repairs a demonstrated trust-path obstacle; it does not certify a full
build-matched live MPN capture. L3-B performance is a separate investigation:
its page-wide overlay coupling and unmeasured wall gaps still need live owner
and readiness evidence. No L3 deadline, page cap, readiness or data rule changes
are included in this trust repair.
