const CACHE_NAME = 'smartbus-cache-v1';
const urlsToCache = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/js/details.js',
    '/static/js/dashboard.js',
    '/static/js/results.js',
    '/static/js/rewards.js',
    '/static/js/chatbot.js'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                return cache.addAll(urlsToCache);
            })
    );
});

self.addEventListener('fetch', event => {
    // Network first, fallback to cache for HTML. Cache first for static assets.
    if (event.request.method !== 'GET') return;
    
    event.respondWith(
        fetch(event.request).then(response => {
            const resClone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, resClone));
            return response;
        }).catch(() => caches.match(event.request))
    );
});
