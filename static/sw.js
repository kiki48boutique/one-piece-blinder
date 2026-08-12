const CACHE_NAME = 'op-binder-v1';

// Installation du Service Worker
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

// Gestion des requêtes
self.addEventListener('fetch', (event) => {
  // Ignorer les requêtes non-GET (ex: POST pour la connexion) et les appels d'API
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
    return; // Laisse le navigateur gérer la requête directement
  }

  // Utilisation du réseau en priorité avec fallback sur le cache pour le reste (GET)
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});