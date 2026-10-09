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
Daily buckets contain path, language, device category, country, referrer hostname and count.
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
6. Install `deploy/ewm-search-console.conf` as
   `/etc/systemd/system/ewm.service.d/search-console.conf` (root-owned, mode 0644)
   and run `systemctl daemon-reload`. The explicit supplementary `ewm` group is
   needed because the service's primary group is `www-data`; the nginx user must
   not be granted access to credentials. Set these entries in the private
   `/etc/ewm.env`, then restart `ewm.service`:

   SEARCH_CONSOLE_PROPERTY=sc-domain:elliottwavemonitor.com
   SEARCH_CONSOLE_CREDENTIALS=/etc/ewm-secrets/search-console-service-account.json

7. Open Statistics. The status should become Connected. No data may be available
   initially; verify permissions and property identity if attention is required.

Reports use the Google read-only webmasters scope, never expose credentials to
the browser, and cache results for 30 minutes (failures for five minutes).
The Google reporting window uses Pacific dates and ends three days ago, requesting
finalized Web Search data. Queries, landing pages and countries each have independent
10-row Previous/Next pagination, preserving the selected period and other tables.
The API startRow offset and one lookahead row determine whether Next is available;
no total is invented. Property totals are requested separately from paginated
rows because Google omits some anonymized/low-volume data.
The local traffic report uses the configured website timezone.

Credential rotation: install the new private file securely, restart the service,
verify Connected, then revoke the old Google key. Revoking property access stops
new reports; cached reports can remain up to 30 minutes. To disconnect immediately,
clear SEARCH_CONSOLE_CREDENTIALS and restart the application.

Reference: https://developers.google.com/webmaster-tools/v1/searchanalytics/query

## Country statistics for all website traffic

This is separate from Google countries and measures page views by approximate
country across all traffic sources, not unique people. Previously collected
views remain Unknown; IP addresses were not stored and cannot be backfilled.
Country lookup is local, with no visitor IP sent to third parties or persisted
in statistics. VPNs, proxies, missing records and location database errors can
produce inaccurate/Unknown countries. Existing bot and privacy exclusions apply.

The provider is DB-IP Country Lite, licensed CC BY 4.0. Keep the linked DB-IP
attribution in the dashboard. The dataset is not committed or publicly served.
Set TRAFFIC_COUNTRY_DATABASE=/var/lib/ewm/geoip/country.mmdb in /etc/ewm.env,
then run `python manage.py update_country_database` with the production environment
loaded and permission to write that directory. Restart the service after initial
configuration. The command downloads the current monthly file over HTTPS,
validates it and atomically replaces the old file; failed updates preserve it.
Refresh monthly with that command. The dashboard warns after 62 days of age.

Keep TRUST_PROXY_CLIENT_IP=True only behind the installed nginx proxy, which
overwrites X-Real-IP with the validated connection address. The configured
Cloudflare real-IP list handles proxied traffic; untrusted visitor country and
forwarded headers are never accepted as location evidence.
