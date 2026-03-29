/**
 * Service Worker  —  AI Task Tracker v3
 * Handles incoming push notifications.
 * Must be served from root: /sw.js
 */

self.addEventListener('install',  () => self.skipWaiting());
self.addEventListener('activate', e  => e.waitUntil(clients.claim()));

// ── Receive push ──────────────────────────────────────────
self.addEventListener('push', event => {
  let data = { title: 'AI Task Tracker', body: 'You have a reminder', url: '/' };

  if (event.data) {
    try   { data = JSON.parse(event.data.text()); }
    catch { data.body = event.data.text(); }
  }

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body:    data.body,
      icon:    '/img/icon-192.png',
      badge:   '/img/icon-192.png',
      vibrate: [200, 100, 200],
      data:    { url: data.url },
      actions: [
        { action: 'open',    title: 'Open App' },
        { action: 'dismiss', title: 'Dismiss'  },
      ],
    })
  );
});

// ── Notification click ────────────────────────────────────
self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'dismiss') return;

  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const client of list) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});
