/* =====================================================
   NEPTOON WEALTH · PWA SERVICE WORKER
   Network-first application architecture
===================================================== */

const CACHE_NAME = "neptoon-shell-v3";

const SHELL_URLS = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-maskable-512.png",
  "/icons/apple-touch-icon.png"
];


/* =====================================================
   INSTALL
===================================================== */

self.addEventListener("install", event => {

  event.waitUntil((async () => {

    const cache = await caches.open(CACHE_NAME);

    await Promise.allSettled(
      SHELL_URLS.map(url =>
        cache.add(
          new Request(url, {
            cache:"reload"
          })
        )
      )
    );

    await self.skipWaiting();

  })());

});


/* =====================================================
   ACTIVATE
===================================================== */

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


/* =====================================================
   NETWORK FIRST
===================================================== */

async function networkFirst(request, fallback = null){

  const cache = await caches.open(CACHE_NAME);

  try {

    const response = await fetch(request, {
      cache:"no-store"
    });

    if(response.ok){

      await cache.put(
        request,
        response.clone()
      );

    }

    return response;

  } catch(error){

    const cached = await cache.match(request);

    if(cached) return cached;

    if(fallback){

      const fallbackResponse =
        await cache.match(fallback);

      if(fallbackResponse) return fallbackResponse;

    }

    throw error;

  }

}


/* =====================================================
   CACHE FIRST
===================================================== */

async function cacheFirst(request){

  const cache = await caches.open(CACHE_NAME);

  const cached = await cache.match(request);

  if(cached) return cached;

  const response = await fetch(request);

  if(response.ok){

    await cache.put(
      request,
      response.clone()
    );

  }

  return response;

}


/* =====================================================
   FETCH
===================================================== */

self.addEventListener("fetch", event => {

  const request = event.request;

  if(request.method !== "GET") return;

  const url = new URL(request.url);

  if(url.origin !== self.location.origin) return;


  /* =====================================
     FINANCIAL DATA · NETWORK ONLY
  ===================================== */

  if(
    url.pathname.endsWith(".json") ||
    url.pathname.startsWith("/api/")
  ){

    event.respondWith(
      fetch(request, {
        cache:"no-store"
      })
    );

    return;

  }


  /* =====================================
     HTML · NETWORK FIRST
  ===================================== */

  if(request.mode === "navigate"){

    event.respondWith(
      networkFirst(request, "/index.html")
    );

    return;

  }


  /* =====================================
     APPLICATION CODE · NETWORK FIRST
  ===================================== */

  if(
    request.destination === "script" ||
    request.destination === "style" ||
    url.pathname.endsWith(".js") ||
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".webmanifest")
  ){

    event.respondWith(
      networkFirst(request)
    );

    return;

  }


  /* =====================================
     STATIC RESOURCES · CACHE FIRST
  ===================================== */

  if(
    request.destination === "image" ||
    request.destination === "font"
  ){

    event.respondWith(
      cacheFirst(request)
    );

    return;

  }

});
