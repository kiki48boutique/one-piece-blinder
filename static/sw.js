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
  const url = event.request.url;

  // 1. Ignorer les requêtes non-GET, l'API et les pages HTML dynamiques
  if (
    event.request.method !== 'GET' || 
    url.includes('/api/') || 
    url.includes('/cartes/') || 
    url.includes('/serie/') ||
    url.includes('/ami/')
  ) {
    return; // Le navigateur gère la requête en direct sur le serveur
  }

  // 2. Réseau en priorité avec fallback sécurisé sur le cache
  event.respondWith(
    fetch(event.request).catch(async () => {
      const cachedResponse = await caches.match(event.request);
      if (cachedResponse) {
        return cachedResponse;
      }
      // Si la ressource n'est ni sur le réseau ni en cache, renvoyer une vraie Response
      return new Response('Contenu non disponible hors-ligne', {
        status: 503,
        statusText: 'Service Unavailable',
        headers: new Headers({ 'Content-Type': 'text/plain; charset=utf-8' })
      });
    })
  );
});