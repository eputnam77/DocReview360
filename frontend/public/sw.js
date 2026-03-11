/**
 * DocReview360 Service Worker — offline caching stub.
 *
 * STUB STATUS: This service worker is functional but intentionally minimal.
 * Full offline support requires registration in _app.tsx (see comment at EOF).
 *
 * Strategies:
 *   Static assets  — Cache-First  (served instantly; stale-while-revalidate in bg)
 *   API calls      — Network-First with offline fallback
 *   Navigation     — Network-First; falls back to cached shell if offline
 */

const CACHE_VERSION = "v1";
const STATIC_CACHE = `docreview360-static-${CACHE_VERSION}`;
const API_CACHE = `docreview360-api-${CACHE_VERSION}`;

// Static assets to pre-cache on install.
const PRECACHE_URLS = [
  "/",
  // Additional shell assets (icons, fonts) can be added here.
];

// API path prefixes that should use Network-First with offline fallback.
const API_PREFIXES = ["/api/", "/documents/", "/projects/"];

// ---------------------------------------------------------------------------
// Install: pre-cache the app shell
// ---------------------------------------------------------------------------
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting()),
  );
});

// ---------------------------------------------------------------------------
// Activate: prune caches from previous versions
// ---------------------------------------------------------------------------
self.addEventListener("activate", (event) => {
  const currentCaches = [STATIC_CACHE, API_CACHE];
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => !currentCaches.includes(key))
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

// ---------------------------------------------------------------------------
// Fetch: route requests to the appropriate strategy
// ---------------------------------------------------------------------------
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin requests.
  if (url.origin !== self.location.origin) return;

  const isApiRequest = API_PREFIXES.some((prefix) => url.pathname.startsWith(prefix));

  if (isApiRequest) {
    // Network-First: try the network; fall back to cache if offline.
    event.respondWith(networkFirstWithFallback(request));
  } else if (request.destination === "document") {
    // Navigation: Network-First so the user always gets the freshest HTML.
    event.respondWith(networkFirstWithFallback(request));
  } else {
    // Static assets: Cache-First for speed.
    event.respondWith(cacheFirstWithRevalidate(request));
  }
});

// ---------------------------------------------------------------------------
// Strategy helpers
// ---------------------------------------------------------------------------

/**
 * Cache-First: serve from cache immediately; fetch from network in the
 * background to keep the cache fresh (stale-while-revalidate).
 */
async function cacheFirstWithRevalidate(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);

  const networkFetch = fetch(request)
    .then((response) => {
      if (response && response.status === 200) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => null);

  return cached ?? (await networkFetch) ?? new Response("Offline", { status: 503 });
}

/**
 * Network-First: try the network; on failure serve the cached copy.
 * Caches successful API responses for offline fallback.
 */
async function networkFirstWithFallback(request) {
  const cache = await caches.open(API_CACHE);
  try {
    const response = await fetch(request);
    // Cache GET responses only.
    if (request.method === "GET" && response.status === 200) {
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    // Return a JSON offline indicator for API requests.
    const url = new URL(request.url);
    const isApi = API_PREFIXES.some((p) => url.pathname.startsWith(p));
    if (isApi) {
      return new Response(
        JSON.stringify({ offline: true, message: "You are offline. Data may be stale." }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      );
    }
    return new Response("You are offline.", { status: 503 });
  }
}

/**
 * TODO (registration): Add the following to frontend/pages/_app.tsx to enable
 * this service worker:
 *
 *   useEffect(() => {
 *     if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
 *       navigator.serviceWorker
 *         .register("/sw.js")
 *         .catch((err) => console.error("SW registration failed:", err));
 *     }
 *   }, []);
 */
