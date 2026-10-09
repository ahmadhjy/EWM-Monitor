# Integrated statistics

Open `/admin/content/trafficdaily/` or **Site management → Statistics**.
The admin stays English/LTR. Superusers can view it; other staff require the
`content.view_trafficdaily` permission (Statistics: Can view Statistics).
There are no add/edit/delete controls for analytics rows.

## Built-in page views

Production defaults to enabled when DEBUG is false. Both
`TRAFFIC_STATS_ENABLED=True` and `SITE_INDEXING_ENABLED=True` must be enabled.
Set TRAFFIC_STATS_ENABLED=False and restart the application to stop collection.

This is intentionally basic aggregate reporting, not unique visitors, sessions,
engagement time, conversions, or an anti-fraud system. Counts start at activation.
Only successful public HTML GET documents count. Staff, recognizable bots,
background fetches, DNT and Global Privacy Control requests are excluded.
Browser caches/CDN full-page caches that bypass Django cannot be counted; do not
configure a Cloudflare Cache Everything rule for dynamic HTML if these origin
page-view counts are relied on. Standard static-asset caching is fine.

No frontend analytics script, analytics cookie, IP address, user identifier,
full user-agent, query string, or full referrer URL is stored by this feature.
Daily buckets contain path, language, device category, referrer hostname and count.
Counter increments are atomic. Old aggregates are pruned after 180 days on the
next counted request. Existing server access logs have separate retention rules.
Do not mistake basic bot filtering for a guarantee that every count is human.

## One-time Google Search Console setup

1. Verify the Domain property `elliottwavemonitor.com` in Search Console. Add the
   exact DNS TXT verification record Google supplies to Cloudflare. Keep it in DNS.
2. Submit `https://elliottwavemonitor.com/sitemap.xml` in Search Console.
3. In an owner-controlled Google Cloud project, enable **Google Search Console API**
   and create a dedicated service account. It does not need project-wide IAM roles.
4. Add that service-account email as a **Restricted user** in the Search Console
   property's Settings → Users and permissions. This integration only reads data.
5. Generate its JSON key and transfer it privately to the server administrator.
   Never commit it, attach it to chat, or upload it to the public media library.
   Install it outside `/var/www/ewm`, for example at
   `/etc/ewm-secrets/search-console-service-account.json`, owned by `root:ewm`,
   mode 0640, in a root-owned directory with mode 0750 and group `ewm`.
6. Set these entries in the private `/etc/ewm.env`, then restart `ewm.service`:

   SEARCH_CONSOLE_PROPERTY=sc-domain:elliottwavemonitor.com
   SEARCH_CONSOLE_CREDENTIALS=/etc/ewm-secrets/search-console-service-account.json

7. Open Statistics. The status should become Connected. No data may be available
   initially; verify permissions and property identity if attention is required.

Reports use the Google read-only webmasters scope, never expose credentials to
the browser, and cache results for 30 minutes (failures for five minutes).
The Google reporting window uses Pacific dates and ends three days ago, requesting
finalized Web Search data. Property totals are requested separately from top-ten
query/page rows because Google omits some anonymized/low-volume data.
The local traffic report uses the configured website timezone.

Credential rotation: install the new private file securely, restart the service,
verify Connected, then revoke the old Google key. Revoking property access stops
new reports; cached reports can remain up to 30 minutes. To disconnect immediately,
clear SEARCH_CONSOLE_CREDENTIALS and restart the application.

Reference: https://developers.google.com/webmaster-tools/v1/searchanalytics/query
