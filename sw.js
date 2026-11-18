
/* =====================================================
   NEPTOON WEALTH · PWA SERVICE WORKER
   Network-first application shell
===================================================== */

const CACHE_NAME = "neptoon-shell-v2";

const SHELL_URLS = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-maskable-512.png",
  "/icons/apple-touch-icon.png"
];

/* INSTALL */

self.addEventListener("install", event => {

  self.skipWaiting();

  event.waitUntil((async () => {

    const cache = await caches.open(CACHE_NAME);

    await Promise.allSettled(
      SHELL_URLS.map(url => cache.add(url))
    );

  })());

});

/* ACTIVATE */

self.addEventListener("activate", event => {

  event.waitUntil((async () => {

    const names = await caches.keys();

    await Promise.all(
      names
        .filter(name =>
          name.startsWith("neptoon-shell-") &&
          name !== CACHE_NAME
        )
        .map(name => caches.delete(name))
    );

    await self.clients.claim();

  })());

});

/* FETCH */

self.addEventListener("fetch", event => {

  const request = event.request;

  if(request.method !== "GET") return;

  const url = new URL(request.url);

  if(url.origin !== self.location.origin) return;

  // Live data must never be served from shell cache.
  if(
    url.pathname.endsWith(".json") ||
    url.pathname.endsWith(".webmanifest") ||
    url.pathname.startsWith("/api/")
  ){
    return;
  }

  // Network-first for page navigation.
  if(request.mode !== "navigate") return;

  event.respondWith((async () => {

    try {

      const response = await fetch(request, {
        cache:"no-store"
      });

      if(response.ok){

        const cache = await caches.open(CACHE_NAME);

        await cache.put(
          "/index.html",
          response.clone()
        );

      }

      return response;

    } catch(error){

      const cache = await caches.open(CACHE_NAME);

      const cached = await cache.match("/index.html");

      if(cached) return cached;

      throw error;

    }

  })());

});
