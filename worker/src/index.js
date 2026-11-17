/**
 * Contact-link click log for oemkitchenware.com
 *
 *   POST /wa          one row per click on a wa.me link (called with sendBeacon)
 *   GET  /wa/stats    aggregate counts, protected by a token
 *   GET  /wa/sid/:id  the click history behind one enquiry message
 *
 * Privacy choices that are deliberate, not accidental:
 *   - no cookies and no persistent id: `sid` is generated per browser tab by the
 *     page script and thrown away when the tab closes;
 *   - the IP never leaves this Worker in readable form, only a salted SHA-256;
 *   - country/city come from Cloudflare's `request.cf`, so no GeoIP database and
 *     no third party is involved;
 *   - rows older than 90 days are deleted nightly by the scheduled handler.
 */

const ALLOWED = new Set([
  "https://oemkitchenware.com",
  "https://www.oemkitchenware.com",
]);

const RETENTION_DAYS = 90;

function cors(origin) {
  const ok = ALLOWED.has(origin) ? origin : "https://oemkitchenware.com";
  return {
    "Access-Control-Allow-Origin": ok,
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

const clean = (v, max) => (typeof v === "string" ? v.slice(0, max) : null);
const sidOk = (v) => typeof v === "string" && /^[a-z0-9]{4,16}$/i.test(v);

async function sha256hex(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].slice(0, 16).map((b) => b.toString(16).padStart(2, "0")).join("");
}

function json(data, origin, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...cors(origin) },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "";

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors(origin) });
    }

    if (request.method === "POST" && url.pathname === "/wa") {
      // a beacon body is small; anything larger is not ours
      const raw = await request.text();
      if (raw.length > 1024) return new Response(null, { status: 413, headers: cors(origin) });

      let body;
      try { body = JSON.parse(raw); } catch { return new Response(null, { status: 400, headers: cors(origin) }); }
      if (!sidOk(body.sid) || !body.path) return new Response(null, { status: 400, headers: cors(origin) });

      const ip = request.headers.get("CF-Connecting-IP") || "";
      const ipHash = ip ? await sha256hex(ip + (env.IP_SALT || "")) : null;
      const cf = request.cf || {};

      await env.DB.prepare(
        `INSERT INTO wa_clicks (sid, path, referrer, ts, width, lang, country, city, ua, ip_hash)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      ).bind(
        body.sid,
        clean(body.path, 200),
        clean(body.ref, 300),
        Number.isFinite(body.ts) ? body.ts : Date.now(),
        Number.isFinite(body.w) ? body.w : null,
        clean(body.lang, 12),
        cf.country || null,
        cf.city || null,
        clean(request.headers.get("User-Agent"), 200),
        ipHash
      ).run();

      return new Response(null, { status: 204, headers: cors(origin) });
    }

    if (request.method === "GET" && url.pathname === "/wa/stats") {
      if (url.searchParams.get("token") !== env.STATS_TOKEN) {
        return json({ error: "forbidden" }, origin, 403);
      }
      const now = Date.now();
      const day = now - 86400000;
      const week = now - 7 * 86400000;

      const totals = await env.DB.prepare(
        `SELECT
           SUM(CASE WHEN ts >= ? THEN 1 ELSE 0 END) AS last24h,
           SUM(CASE WHEN ts >= ? THEN 1 ELSE 0 END) AS last7d,
           COUNT(*) AS all_time,
           COUNT(DISTINCT sid) AS sessions
         FROM wa_clicks`
      ).bind(day, week).first();

      const pages = await env.DB.prepare(
        `SELECT path, COUNT(*) AS clicks, COUNT(DISTINCT sid) AS sessions
         FROM wa_clicks WHERE ts >= ? GROUP BY path ORDER BY clicks DESC LIMIT 25`
      ).bind(week).all();

      const countries = await env.DB.prepare(
        `SELECT country, COUNT(*) AS clicks FROM wa_clicks WHERE ts >= ?
         GROUP BY country ORDER BY clicks DESC LIMIT 15`
      ).bind(week).all();

      return json({ totals, pages: pages.results, countries: countries.results }, origin);
    }

    const m = url.pathname.match(/^\/wa\/sid\/([a-z0-9]{4,16})$/i);
    if (request.method === "GET" && m) {
      if (url.searchParams.get("token") !== env.STATS_TOKEN) {
        return json({ error: "forbidden" }, origin, 403);
      }
      const rows = await env.DB.prepare(
        `SELECT path, referrer, ts, country, city, ua FROM wa_clicks
         WHERE sid = ? ORDER BY ts ASC LIMIT 200`
      ).bind(m[1].toLowerCase()).all();
      return json({ sid: m[1], clicks: rows.results }, origin);
    }

    if (url.pathname === "/wa/health") return json({ ok: true }, origin);

    return new Response("Not found", { status: 404 });
  },

  // Cloudflare Cron: drop anything past the retention window.
  async scheduled(_event, env) {
    const cutoff = Date.now() - RETENTION_DAYS * 86400000;
    await env.DB.prepare("DELETE FROM wa_clicks WHERE ts < ?").bind(cutoff).run();
  },
};
