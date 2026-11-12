# Simple update notification (Cloudflare Worker)

SPT Downloader checks a public **Cloudflare Worker** at
`https://divine-hill-13fc.punzer4.workers.dev/`. It does **not** use GitHub,
OneDrive, or Microsoft authentication to check for an update.

The notification has exactly one message, **`update tersedia`**, and two buttons:

- **Update** opens the maintainer-approved, organization-shared **personal
  OneDrive** folder in the default browser. The application does not download
  or install files.
- **Close** dismisses the notification without opening the browser.

The folder is in an organizational Microsoft 365 tenant but has a `/personal/`
storage path; it is **not** a team-site document library. The owner has
explicitly confirmed that its existing sharing policy permits people in the
organization to access it, and requested this exact destination. The URL does
contain the account identifier and is visible in this public repository and
installed application, but provides **no credentials or permission by itself**.
Accessing the private files may still require Microsoft 365 sign-in and
organization membership. This accepted tradeoff avoids creating an unrelated
team site; the link is not guaranteed to survive an owner departure, an account
rename, a folder move, or a changed sharing policy. Any migration requires a
reviewed change to the single `UPDATE_FOLDER_URL` constant and a new verified
app build. The destination is never taken from the public Worker JSON.

## Manually publish metadata

This hostname uses **Cloudflare Workers (`workers.dev`)**, not Pages. The
application checks the **root path `/`**, not `/latest.json`. The current
root returned HTTP 200, `application/json` and an **empty body** during
initial endpoint validation; that is a connectivity result, not an update
manifest. Until you publish JSON, no automatic notification appears.

When a **main** release has passed all CI, independent review, manual
acceptance and verified artifact-promotion gates, copy its `build-info.json`
commit, run ID and run attempt. Publish this exact four-field JSON object
as the response body at the Worker root:

```json
{
  "schema": 1,
  "commit": "REPLACE_WITH_VERIFIED_LOWERCASE_40_CHARACTER_COMMIT_SHA",
  "run_id": "REPLACE_WITH_VERIFIED_NUMERIC_RUN_ID",
  "run_attempt": 1
}
```

Replace the placeholders with actual verified release coordinates. Keep
`run_id` as a quoted decimal string; `run_attempt` is an integer. Do not
publish a PR commit, a draft release or a speculative latest version. The
Worker must return **HTTP 200**, `Content-Type: application/json`, and this
valid JSON body over HTTPS with **no redirect**. For a manually edited
Cloudflare Worker, an example return expression is:

```javascript
export default {
  async fetch(request) {
    if (new URL(request.url).pathname !== "/") {
      return new Response("Not found", { status: 404 });
    }
    return new Response(JSON.stringify({
      schema: 1,
      commit: "REPLACE_WITH_VERIFIED_LOWERCASE_40_CHARACTER_COMMIT_SHA",
      run_id: "REPLACE_WITH_VERIFIED_NUMERIC_RUN_ID",
      run_attempt: 1
    }), {
      status: 200,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store"
      }
    });
  }
};
```

This is a complete example Worker module to paste into the manual deployment editor,
not a live verified release and not an instruction to run a new unreviewed
release. Do not put credentials, download links, tax records, or personal
information in the public response.

The client accepts only the exact configured HTTPS Worker root, no redirects,
and an HTTP 200 JSON response up to 4096 bytes with a five-second timeout.
It rejects unknown/duplicate keys and invalid values. It only notifies if the
published build has a different commit and a **later source-main Actions run
ID** than the locally verified installed build. This is a conservative
comparison, not a signed update proof or Git ancestry verification.

## Checks and behavior

The app schedules its first automatic check immediately after the window is
constructed, on the first Tk event-loop turn (no four-second startup delay),
and checks again daily while open. Network work runs off the Tk UI thread.
Manual check is available in Settings via
**Cek pembaruan**. It defers the popup while an SPT job or interaction is active.
If the Worker is empty, malformed, blocked, or offline, automatic checks do
nothing; they never block Coretax or local export. Only the release notice
has the two buttons.

Test the exact root from the intended organizational network after each
deployment, confirming HTTP 200, valid JSON and TLS. Initial connectivity
checks succeeded, but
that is not proof the final metadata has been published. Cloudflare Workers
deployments remain **manual**; this repository does not publish or update the
Worker. No executable installation, Microsoft Graph, or automatic OneDrive
access is performed.

A notice is **informational** and is not an executable authenticity signal.
The Worker response is not cryptographically signed. If installation or
artifact authorization is added in the future, independently verified
signatures and stronger release verification will be required.

## Rollback and publication risk

A manifest rolled back to a smaller `run_id` will not notify a newer installed
build. Conversely, a manually deployed manifest advertising a **newer but
unaccepted** run can trigger an informational notification even if that build
should not be distributed. **This is an accepted residual risk of an unsigned,
operator-published informational manifest**, not proof of release acceptance.
Only an approved main-branch artifact with completed CI, independent review,
verified provenance and available organizational downloads should be announced.
The operator is responsible for restoring the last accepted manifest or an
empty response immediately upon discovering an incorrect publication; clients
must fail silently on invalid/empty responses. No automatic installation or
file integrity decision is based on this metadata.
