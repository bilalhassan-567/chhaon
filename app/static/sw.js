// Chhaon's Web Push service worker. Deliberately minimal — its only job is to turn
// an incoming push event into a visible notification. Registered at root scope
// (served from /sw.js, not /static/sw.js) so it can control the whole origin.

self.addEventListener("push", (event) => {
  let payload = { title: "Chhaon heat alert", body: "A zone you're watching may be at risk." };
  if (event.data) {
    try {
      payload = event.data.json();
    } catch (e) {
      payload.body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: "/static/og-image.png",
      badge: "/static/og-image.png",
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow("/"));
});
