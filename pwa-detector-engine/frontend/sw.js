const CACHE_PREFIX = "pwa-radar-shell-";
const CACHE_NAME = CACHE_PREFIX + "v1";
const SHELL_PATHS = [
    "./",
    "./index.html",
    "./manifest.webmanifest",
    "./icons/icon-192.png",
    "./icons/icon-512.png",
    "./icons/icon-maskable-512.png"
];
const shellURLs = new Set(SHELL_PATHS.map((path) => new URL(path, self.registration.scope).href));

self.addEventListener("install", (event) => {
    event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_PATHS)));
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((names) => Promise.all(
            names.filter((name) => name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME)
                .map((name) => caches.delete(name))
        )).then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", (event) => {
    // Le API e tutte le risorse estranee alla shell restano esclusivamente in rete.
    if (event.request.method !== "GET" || !shellURLs.has(event.request.url)) return;
    event.respondWith((async () => {
        const cache = await caches.open(CACHE_NAME);
        let response;
        try {
            response = await fetch(event.request);
        } catch (error) {
            const cached = await cache.match(event.request);
            if (cached) return cached;
            throw error;
        }
        if (response.ok && response.type === "basic") {
            event.waitUntil(cache.put(event.request, response.clone()));
        }
        return response;
    })());
});
