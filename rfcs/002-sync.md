# RFC: Sync Command

**Status:** Draft  
**Author:** Brian Brennan  
**Created:** 2025-01-30

---

## Summary

Implement `alm sync` to pull defects from ALM's REST API and store them locally per RFC 001.

## Problem

ALM data exists only in ALM's garbage web UI. We need to pull it out so we can actually search and link to defects.

## Proposed Solution

### Authentication

Manual cookie refresh. User logs into ALM in browser, copies cookies, saves to config file.

```
~/.config/alm-scraper/config.json
```

```json
{
  "base_url": "https://alm.deloitte.com/qcbin",
  "domain": "CONVERGINT",
  "project": "Convergint_Transformation",
  "cookies": {
    "JSESSIONID": "...",
    "access_token": "...",
    "QCSession-...": "...",
    "ALM_USER": "...",
    "XSRF-TOKEN": "..."
  }
}
```

**Convenience import:** Since copying individual cookies is tedious, provide a way to import from a curl command:

```bash
$ alm config import-curl
Paste curl command (then press Enter twice):
curl 'https://alm.deloitte.com/qcbin/...' -H '...' -b '...'

Imported config:
  base_url: https://alm.deloitte.com/qcbin
  domain: CONVERGINT
  project: Convergint_Transformation
  cookies: 5 cookies extracted

Saved to ~/.config/alm-scraper/config.json
```

This parses the curl command, extracts the URL components and `-b` cookie header, and writes the config file.

### API Details

**Endpoint:**

```
GET /qcbin/rest/domains/{domain}/projects/{project}/defects
```

**Query params:**

- `page-size=1000` - max results per page
- `start-index=1` - pagination (1-indexed)
- `order-by={id[asc];}` - consistent ordering for pagination

**Required headers:**

- `Accept: application/json`
- `alm-client-type: ALM Web Client UI`

**Pagination:** Response includes `TotalResults` field, so we know upfront how many pages to fetch:

```json
{
  "entities": [...],
  "TotalResults": 1263
}
```

### User Experience

```bash
$ alm sync
Fetching defects from ALM...
  Page 1/2: 1000 defects
  Page 2/2: 263 defects
Synced 1263 defects in 8.2s
```

On auth failure (need to determine what error ALM actually returns - might not be 401):

```bash
$ alm sync
Error: ALM authentication failed

Your session has expired. To refresh:
1. Log into ALM in your browser
2. Open DevTools > Network
3. Find a request to /qcbin/rest/... and "Copy as cURL"
4. Run: alm config import-curl
```

### Rate limiting

Be polite: wait 1-2 seconds between page requests. We're only fetching 2-3 pages anyway, so this adds ~5 seconds to sync time. Not worth risking getting blocked.

## Open Questions

1. **What error does ALM return on expired session?** - Might be 401, might be something else. Need to test.
2. **Which cookies are actually required?** - The curl has a bunch, but some might be optional (OptanonConsent is cookie consent banner garbage, AWSALB is load balancer stickiness)

## Notes

- Observed curl command in `tmp/curl.sh`
- page-size=1000 seems to work
- start-index is 1-indexed (start-index=1001 fetches page 2)
- Response includes `TotalResults` for pagination

### Cookie details

The `QCSession-*` cookie name has a base64-encoded suffix:

- Cookie name: `QCSession-YWxtIHdlYiBjbGllbnQgdWkX`
- Suffix decodes to: `alm web client ui`

The cookie value is also base64, semicolon-delimited:

```
8504763;SEUPYZkWWGvQk6cEHkv5mg**;ALM Web Client UI;60;dashboard,management,REQUIREMENTS,TESTLAB,DEFECTS;
```

- User/session ID
- Token/hash
- Client type
- Timeout (minutes?)
- Module permissions

When parsing cookies from curl, match `QCSession-*` as a prefix.

### Session keep-alive

ALM's web client pings `GET /qcbin/rest/site-session` every 3 minutes to keep the session alive. Returns 200 OK with empty body, but the response **does** include `Set-Cookie` headers that rotate the `access_token`.

Observed behavior:

- Request sends current `access_token`
- Response has `Content-Length: 0` (no body)
- Response includes `Set-Cookie: access_token=<new_token>; Path=/; Secure; HttpOnly`
- Browser automatically updates the cookie

The `QCSession-*`, `JSESSIONID`, `ALM_USER`, and `XSRF-TOKEN` cookies stay constant across heartbeats. Only `access_token` and `AWSALB*` rotate.

**For our sync:** We ignore this. Our sync takes ~10 seconds, not long enough for token rotation to matter. If we ever hit issues with token expiry mid-sync, we could capture `Set-Cookie` headers and update cookies between requests.

### Web client bootup sequence

For reference, here's what the ALM web client does on load (from HAR capture):

1. `GET /qcbin/rest/serversettings` - server config
2. `GET /qcbin/rest/is-authenticated` - auth check
3. `GET /qcbin/rest/site-session` - keep-alive ping
4. `GET /qcbin/v2/sa/api/permissions` - user permissions
5. `GET /qcbin/rest/domains/{domain}/projects/{project}/customization/modules` - available modules
6. `GET /qcbin/rest/domains/{domain}/projects/{project}/webrunner/profile` - user profile
7. `DELETE /qcbin/rest/site-session` - logs out old session (requires `x-xsrf-token` header)
8. `POST /qcbin/rest/site-session` - creates new session with XML body:
   ```xml
   <session-parameters>
     <client-type>ALM Web Client UI</client-type>
     <licenses><license>dashboard</license><license>DEFECTS</license>...</licenses>
     <time-out>60</time-out>
   </session-parameters>
   ```
9. `GET /qcbin/rest/domains/{domain}/projects?is-template-project=y` - list projects
10. `GET /qcbin/rest/domains/{domain}/projects/{project}/metadata` - project metadata

We don't need any of this - we piggyback on an existing browser session. But it's useful context if we ever need to understand session lifecycle or debug auth issues.
