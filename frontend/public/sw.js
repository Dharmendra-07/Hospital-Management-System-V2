/**
 * HMS V2 — Service Worker
 * Strategy:
 *   - App shell (HTML, CSS, JS, fonts): Cache First
 *   - API calls (/api/*): Network First with fallback
 *   - Images: Cache First with 30-day expiry
 */

const CACHE_NAME    = 'hms-v2-cache-v1'
const API_CACHE     = 'hms-v2-api-cache-v1'

// App shell assets to pre-cache
const PRECACHE_URLS = [
  '/',
  '/index.html',
]

// ── Install ─────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
  )
  self.skipWaiting()
})

// ── Activate ────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_NAME && k !== API_CACHE)
          .map(k => caches.delete(k))
      )
    )
  )
  self.clients.claim()
})

// ── Fetch ────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Skip non-GET and browser extension requests
  if (request.method !== 'GET') return
  if (!url.protocol.startsWith('http')) return

  // API calls — Network First, fall back to cached response
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstAPI(request))
    return
  }

  // App shell — Cache First, fall back to network
  event.respondWith(cacheFirstShell(request))
})

async function networkFirstAPI(request) {
  const cache = await caches.open(API_CACHE)
  try {
    const response = await fetch(request)
    // Only cache successful GET responses for safe endpoints
    if (response.ok) {
      const safeEndpoints = ['/api/patient/departments', '/api/patient/doctors']
      const isSafe = safeEndpoints.some(ep => request.url.includes(ep))
      if (isSafe) cache.put(request, response.clone())
    }
    return response
  } catch (_) {
    const cached = await cache.match(request)
    if (cached) return cached
    return new Response(
      JSON.stringify({ error: 'You appear to be offline. Please check your connection.' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    )
  }
}

async function cacheFirstShell(request) {
  const cached = await caches.match(request)
  if (cached) return cached
  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME)
      cache.put(request, response.clone())
    }
    return response
  } catch (_) {
    // Return cached index.html for SPA navigation
    const fallback = await caches.match('/index.html')
    return fallback || new Response('Offline', { status: 503 })
  }
}

// ── Push notifications (future) ─────────────────────────────
self.addEventListener('push', (event) => {
  if (!event.data) return
  const data = event.data.json()
  event.waitUntil(
    self.registration.showNotification(data.title || 'HMS Reminder', {
      body:    data.body    || '',
      icon:    data.icon    || '/icons/icon-192.png',
      badge:   data.badge   || '/icons/icon-96.png',
      tag:     data.tag     || 'hms-notification',
      vibrate: [200, 100, 200],
    })
  )
})
