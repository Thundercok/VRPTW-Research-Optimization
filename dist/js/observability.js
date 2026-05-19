/**
 * Frontend observability bootstrap.
 *
 * Fetches /api/config and dynamically loads three optional providers, each
 * gated by env vars on the backend:
 *   - Sentry browser SDK   (SENTRY_FRONTEND_DSN)
 *   - Plausible Analytics  (PLAUSIBLE_DOMAIN)
 *   - PostHog              (POSTHOG_PUBLIC_KEY)
 *
 * Goals:
 *   - Zero-config when no keys are set: do nothing, never break the app.
 *   - Stays out of the critical render path (script is plain ES, no modules).
 *   - Exposes window.vrptwTrack(event, props) so app code can send events
 *     without caring which analytics tool is wired up.
 */
(function () {
  "use strict";

  var CONFIG_ENDPOINT = "/api/config";
  var DEFAULT_SENTRY_BUNDLE = "https://browser.sentry-cdn.com/8.34.0/bundle.tracing.min.js";

  function loadScript(src, onload, onerror, attrs) {
    var s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.defer = true;
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        s.setAttribute(key, attrs[key]);
      });
    }
    s.onload = function () {
      if (typeof onload === "function") onload();
    };
    s.onerror = function () {
      if (typeof onerror === "function") onerror();
    };
    document.head.appendChild(s);
  }

  function noop() {}

  function initSentry(cfg) {
    if (!cfg || !cfg.enabled || !cfg.dsn) return;
    if (window.Sentry && typeof window.Sentry.init === "function") {
      try {
        window.Sentry.init({
          dsn: cfg.dsn,
          environment: cfg.environment || "development",
          tracesSampleRate: cfg.tracesSampleRate || 0.0,
          release: (window.__VRPTW_VERSION__ || "dev"),
        });
        return;
      } catch (e) {
        // fall through to CDN load
      }
    }
    loadScript(
      DEFAULT_SENTRY_BUNDLE,
      function () {
        if (window.Sentry && typeof window.Sentry.init === "function") {
          try {
            window.Sentry.init({
              dsn: cfg.dsn,
              environment: cfg.environment || "development",
              tracesSampleRate: cfg.tracesSampleRate || 0.0,
            });
          } catch (e) {
            console.warn("Sentry init failed", e);
          }
        }
      },
      function () {
        console.warn("Could not load Sentry browser SDK");
      },
      { crossorigin: "anonymous" }
    );
  }

  function initPlausible(cfg) {
    if (!cfg || !cfg.enabled || !cfg.domain) return;
    var src = cfg.src || "https://plausible.io/js/script.js";
    loadScript(src, noop, function () {
      console.warn("Plausible script blocked or unreachable");
    }, { "data-domain": cfg.domain });
  }

  function initPostHog(cfg) {
    if (!cfg || !cfg.enabled || !cfg.apiKey) return;
    /* eslint-disable */
    !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures getActiveMatchingSurveys getSurveys".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
    /* eslint-enable */
    try {
      window.posthog.init(cfg.apiKey, {
        api_host: cfg.apiHost || "https://app.posthog.com",
        capture_pageview: true,
        autocapture: true,
        person_profiles: "identified_only",
      });
    } catch (e) {
      console.warn("PostHog init failed", e);
    }
  }

  /**
   * Lightweight tracker that fans out to whatever provider happens to be ready.
   * Callable from anywhere, e.g. window.vrptwTrack("run_model", {dataset:"demo"}).
   */
  function track(event, props) {
    try {
      if (window.plausible) window.plausible(event, { props: props || {} });
    } catch (e) {}
    try {
      if (window.posthog && window.posthog.capture) window.posthog.capture(event, props || {});
    } catch (e) {}
    try {
      if (window.Sentry && window.Sentry.addBreadcrumb) {
        window.Sentry.addBreadcrumb({ category: "event", message: event, data: props || {}, level: "info" });
      }
    } catch (e) {}
  }
  window.vrptwTrack = track;

  function bootstrap() {
    fetch(CONFIG_ENDPOINT, { credentials: "same-origin" })
      .then(function (resp) {
        if (!resp.ok) throw new Error("config " + resp.status);
        return resp.json();
      })
      .then(function (cfg) {
        if (!cfg) return;
        if (cfg.app && cfg.app.version) window.__VRPTW_VERSION__ = cfg.app.version;
        initSentry(cfg.sentry);
        initPlausible(cfg.plausible);
        initPostHog(cfg.posthog);
      })
      .catch(function (err) {
        console.debug("observability disabled:", err && err.message);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();
