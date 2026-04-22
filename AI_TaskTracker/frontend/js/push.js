/**
 * Push Notification Manager  —  AI Task Tracker v3
 * Handles browser permission, VAPID subscription, test sends.
 * Works: Chrome, Edge, Firefox desktop + Android Chrome.
 * Does NOT work: iOS Safari (Apple restriction as of 2025).
 */
const PushManager = {
  _sw:  null,  // ServiceWorkerRegistration
  _sub: null,  // PushSubscription

  async init() {
    if (!this.isSupported()) return;
    try {
      this._sw  = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
      this._sub = await this._sw.pushManager.getSubscription();
      this._updateUI();
    } catch (e) {
      console.warn('Push init failed:', e);
    }
  },

  isSupported() {
    return 'serviceWorker' in navigator && 'PushManager' in window;
  },

  isSubscribed() {
    return !!this._sub;
  },

  _updateUI() {
    const subBtn   = document.getElementById('push-subscribe-btn');
    const unsubBtn = document.getElementById('push-unsubscribe-btn');
    const testBtn  = document.getElementById('push-test-btn');
    const banner   = document.getElementById('push-banner');
    const unsupMsg = document.getElementById('push-unsupported');

    if (!this.isSupported()) {
      banner?.classList.add('hidden');
      unsupMsg?.classList.remove('hidden');
      return;
    }

    banner?.classList.remove('hidden');
    unsupMsg?.classList.add('hidden');

    if (this.isSubscribed()) {
      subBtn?.classList.add('hidden');
      unsubBtn?.classList.remove('hidden');
    } else {
      subBtn?.classList.remove('hidden');
      unsubBtn?.classList.add('hidden');
    }
  },

  async subscribe() {
    if (!this.isSupported()) {
      Toast.error('Push notifications are not supported in this browser');
      return;
    }

    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      Toast.warning('Notification permission denied. Check browser settings.');
      return;
    }

    try {
      const { public_key } = await API.push.vapidKey();
      const appServerKey   = this._urlBase64ToUint8Array(public_key);

      this._sub = await this._sw.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: appServerKey,
      });

      const rawKey  = this._sub.getKey('p256dh');
      const rawAuth = this._sub.getKey('auth');

      await API.push.subscribe({
        endpoint: this._sub.endpoint,
        p256dh:   btoa(String.fromCharCode(...new Uint8Array(rawKey))),
        auth:     btoa(String.fromCharCode(...new Uint8Array(rawAuth))),
      });

      Toast.success('🔔 Push notifications enabled!');
      this._updateUI();
    } catch (e) {
      if (e.message?.includes('not configured')) {
        Toast.error('VAPID keys not set up. Run: python scripts/generate_vapid.py');
      } else {
        Toast.error('Failed to enable notifications: ' + e.message);
      }
    }
  },

  async unsubscribe() {
    if (!this._sub) return;
    try {
      const rawKey  = this._sub.getKey('p256dh');
      const rawAuth = this._sub.getKey('auth');

      await API.push.unsubscribe({
        endpoint: this._sub.endpoint,
        p256dh:   btoa(String.fromCharCode(...new Uint8Array(rawKey))),
        auth:     btoa(String.fromCharCode(...new Uint8Array(rawAuth))),
      });

      await this._sub.unsubscribe();
      this._sub = null;
      Toast.info('Push notifications disabled');
      this._updateUI();
    } catch (e) {
      Toast.error('Failed to disable: ' + e.message);
    }
  },

  _urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64  = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw     = window.atob(base64);
    return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
  },
};
