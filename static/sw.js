const CACHE_NAME = 'op-binder-v1';

// Installation du Service Worker
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

// Gestion des requêtes (passe toujours par le réseau pour garder vos prix/decks à jour)
self.addEventListener('fetch', (event) => {
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});