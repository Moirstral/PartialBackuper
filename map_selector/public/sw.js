const CACHE = "mc-map-offline-v1";
const SHELL = [
  "/offline.html", "/style.css",
  "/manifest.webmanifest", "/icon.svg", "/icon-192.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;

  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .catch(() => caches.match("/offline.html"))
    );
    return;
  }

  // 其他静态资源：网络优先，失败回缓存
  event.respondWith(fetch(req).catch(() => caches.match(req)));
});