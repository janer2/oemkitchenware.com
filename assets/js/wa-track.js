/**
 * Contact-link click log.
 *
 * Every wa.me link on the site already carries "(via oemkitchenware.com/<path>)"
 * in its prefilled text. This adds one more thing: a short session id that is
 * sent to the Worker on click AND appended to the message. When the buyer
 * actually writes, the id in their message resolves to the exact click history
 * behind it - without a cookie and without knowing who they are beforehand.
 *
 * Deploy order: set ENDPOINT below to the deployed Worker URL + /wa, then ship.
 * While ENDPOINT is empty this file does nothing.
 */
(function () {
  var ENDPOINT = ""; // e.g. "https://yongli-wa.yourname.workers.dev/wa"
  if (!ENDPOINT) return;

  var KEY = "wa_sid";

  function sid() {
    var v;
    try { v = sessionStorage.getItem(KEY); } catch (e) { v = null; }
    if (!v) {
      v = Math.random().toString(36).slice(2, 7);
      try { sessionStorage.setItem(KEY, v); } catch (e) {}
    }
    return v;
  }

  function beacon(payload) {
    var body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
      navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "text/plain;charset=UTF-8" }));
      return;
    }
    try {
      fetch(ENDPOINT, { method: "POST", body: body, keepalive: true, mode: "cors" });
    } catch (e) {}
  }

  document.addEventListener(
    "click",
    function (ev) {
      var a = ev.target && ev.target.closest ? ev.target.closest('a[href*="wa.me/"]') : null;
      if (!a) return;

      var id = sid();

      // 1) stamp the message the buyer is about to send, while we still can
      try {
        var u = new URL(a.href);
        var text = u.searchParams.get("text") || "";
        if (text.indexOf("[" + id + "]") === -1) {
          u.searchParams.set("text", text + " [" + id + "]");
          a.href = u.toString();
        }
      } catch (e) {}

      // 2) record the click; a failure here must never block the navigation
      beacon({
        sid: id,
        path: location.pathname,
        ref: document.referrer || "",
        ts: Date.now(),
        w: window.innerWidth,
        lang: navigator.language
      });
    },
    true
  );
})();
