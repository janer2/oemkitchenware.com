# wa-clicks — contact-link click log

Records every click on a WhatsApp link on oemkitchenware.com so that an enquiry can be traced back
to the page it started on. One Worker, one D1 table, no cookies.

## What gets stored

| column | example | note |
|---|---|---|
| `sid` | `w7f3a` | random per browser tab, the same value is appended to the WhatsApp message |
| `path` | `/product/AA-43` | the page the button was on |
| `referrer` | `https://www.google.com/` | empty for direct visits |
| `ts` | `1763378000000` | click time, ms |
| `country`, `city` | `DE`, `Hamburg` | from Cloudflare's edge, no GeoIP lookup |
| `ua`, `width`, `lang` | | device roughness only |
| `ip_hash` | `9f2c…` | SHA-256 of IP + `IP_SALT`, truncated; the address is never stored |

Rows older than 90 days are removed by the nightly cron.

## Deploy (one time, ~5 minutes)

```bash
npm install -g wrangler          # if you do not have it
wrangler login                   # opens a browser once

cd worker
wrangler d1 create yongli_wa     # prints database_id
# paste that id into wrangler.toml

wrangler d1 execute yongli_wa --remote --file schema.sql
wrangler secret put STATS_TOKEN  # invent a long random string, keep it
wrangler secret put IP_SALT      # invent another one

wrangler deploy                  # prints https://yongli-wa.<subdomain>.workers.dev
```

Then set `ENDPOINT` in `assets/js/wa-track.js` to that URL plus `/wa` and redeploy the site.
Until that constant is filled in, the script does nothing at all - it is already included on every page.

## Reading it

```bash
# last 7 days, top pages and countries
curl "https://yongli-wa.<subdomain>.workers.dev/wa/stats?token=$STATS_TOKEN"

# what one enquiry did before writing: paste the [sid] from their message
curl "https://yongli-wa.<subdomain>.workers.dev/wa/sid/w7f3a?token=$STATS_TOKEN"
```

When a message arrives carrying `[w7f3a]`, the second call shows every page that visitor clicked from,
with timestamps and country. Keep the token out of the repo and out of screenshots.

## Notes

- If the Worker is unreachable the page still works: `sendBeacon` failures are ignored.
- The click log tells you that someone clicked; only the WhatsApp message tells you who. The `sid`
  in the prefilled text is what joins the two, and a buyer who deletes that line simply stays anonymous.
- Delete a row by `sid` if someone asks to be forgotten:
  `wrangler d1 execute yongli_wa --remote --command "DELETE FROM wa_clicks WHERE sid='w7f3a'"`
