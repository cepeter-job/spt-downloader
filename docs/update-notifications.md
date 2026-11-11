# Public release notifications (Cloudflare Pages)

Status: **candidate in issue #237**. The production URL is intentionally unset.
No Cloudflare Pages project, actual release metadata, or in-app update service
is claimed live by this document. No executable auto-updater is introduced.

## Scope and trust

Notification metadata is public and contains **no** SharePoint/OneDrive URLs,
Microsoft credentials, NPWP, account data, build artifacts, or tax records.
The approved Windows SPT Downloader executable checks at most a small JSON file
over HTTPS; the private organizational SharePoint folder continues to own
release downloads under its existing access control. An end user does not need
to log in to GitHub/OneDrive to receive the public notification.

The read-only client is `spt_desktop/update_notice.py`. The exact final
`https://<owned-project>.pages.dev/latest.json` must be reviewed and placed
in its `MANIFEST_URL` constant **only after** deployment ownership and office
network access are proven. An unknown URL is not provided via environment,
user preferences, or data from the public manifest. This intentionally means
the current candidate does **not** contact a fabricated project endpoint.

The client:
- uses a descriptive `SPTDownloader-UpdateCheck/1.0` User-Agent;
- validates TLS through the OS/Python trust context; HTTPS-only, exact hostname
  and path, no redirects, no query or embedded credentials;
- reads at most 4096 bytes with a five-second network timeout, requires HTTP
  200 with JSON content type, rejects duplicate keys, unexpected keys, invalid
  fields and external links inside notes;
- checks the immutable `build-info.json` values for commit, run ID and
  attempt. An installed build without valid identity never makes a request;
- shows a newer release only when it has a **different commit** and a strictly
  later source-main Actions run ID than the installed build. This deliberately
  fails closed for development builds created after a published release;
- never performs any request on Tk's UI thread, and defers automatic
  notifications through active jobs, selection dialogs and open Settings;
- makes failure a silent no-op in automatic mode. Manual checking gives a
  generic message only. It neither logs URLs nor attempts a download.

This version relies on the HTTPS origin and tightly restricted informational
schema. It is **not** a signed-update protocol and may not be used to authorize
downloads or executable installation. If the release message is ever used for
authorization, require independently verified signatures and an audited
trust-anchor/provisioning process first.

## Manifest contract

Place `latest.json` in the root of an **owned** Cloudflare Pages project:

```json
{
  "schema": 1,
  "version": "2026.11.1",
  "published_at": "2026-11-11",
  "notes": "Perbaikan stabilitas",
  "commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "run_id": "420",
  "run_attempt": 1
}
```

These values are **synthetic examples**, not an existing public release.
Use the exact source-main commit/run/attempt from a verified, independently
reviewed release promotion and a maintainer-approved release number.
Publish **only after** the corresponding ZIP/EXE is approved and available
to authorized people. Do not publish PR builds, unverified artifacts, or
draft releases. A newer run ID is an announcement heuristic, not proof of
Git ancestry or a replacement for the existing provenance checks.

Cloudflare Pages Direct Upload can publish this single JSON file without
a GitHub integration. Cloudflare dashboard authentication and a valid project
are required; a 403 Cloudflare challenge to command-line HTTP requests does not
prove that a normal browser session is blocked. Check whether the real endpoint
returns application/json, HTTP 200 and valid TLS **from the Fortinet office PC**.
Sample Pages sites passing is insufficient.

## Acceptance, disabling and recovery

1. Create and verify the Pages project through an authorized administrator.
2. Review the manifest schema and exact source release identity.
3. Set the exact owned `MANIFEST_URL`; open an implementation PR; run exact-head
   portable and Windows GUI tests plus the signed/verified packaging gates.
4. Independently review; approve and merge only after all CI/review requirements.
5. Upload the approved informational manifest, then test the actual endpoint
   from the Fortinet-protected PC. Confirm one notice for an older executable,
   none for an equal or newer build, and no interruption during a live job.
6. Restore a previously reviewed manifest (or delete it to disable checks)
   if publication was incorrect. Missing/blocked endpoints fail closed, leaving
   Coretax and local export unaffected.

Do not infer organizational SharePoint access from the notification: users may
still need Microsoft 365 login and permissions to download release files.
