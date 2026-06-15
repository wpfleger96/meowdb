/* ============================================================
   app.js — client-side router, Alpine registrations, global state
   ============================================================ */

/* ──────────────────────────────────────────────────────────
   Route table
────────────────────────────────────────────────────────── */

const ROUTES = {
  '/':        'play',
  '/library': 'library',
  '/upload':  'ingest',
  '/stats':   'stats',
};

function pathToView(path) {
  return ROUTES[path] || ROUTES['/'];
}

/* ──────────────────────────────────────────────────────────
   Global navigation helper (called by view components)
────────────────────────────────────────────────────────── */

function navigateTo(path) {
  history.pushState({}, '', path);
  dispatchRouteChange(path);
}

function dispatchRouteChange(path) {
  window.dispatchEvent(new CustomEvent('route-change', { detail: { path } }));
}

/* ──────────────────────────────────────────────────────────
   Toast system
────────────────────────────────────────────────────────── */

/**
 * Show a transient toast notification.
 * @param {string} message
 * @param {'info'|'success'|'error'} [type='info']
 * @param {number} [duration=3000]
 */
function showToast(message, type = 'info', duration = 3000) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);

  setTimeout(() => {
    el.classList.add('removing');
    el.addEventListener('animationend', () => el.remove(), { once: true });
  }, duration);
}

/* ──────────────────────────────────────────────────────────
   Root Alpine component
────────────────────────────────────────────────────────── */

function app() {
  return {
    currentView: pathToView(location.pathname),
    authenticated: false,
    showLoginModal: false,
    loginPassword: '',
    loginError: '',
    loginLoading: false,

    async init() {
      // Handle browser back/forward
      window.addEventListener('popstate', () => {
        this.currentView = pathToView(location.pathname);
      });

      // Handle programmatic navigation
      window.addEventListener('route-change', (e) => {
        this.currentView = pathToView(e.detail.path);
      });

      try {
        const s = await getAuthStatus();
        this.authenticated = s.authenticated;
      } catch (_) {
        // auth status check is best-effort; if it fails, assume unauthenticated
      }
    },

    isView(name) {
      return this.currentView === name;
    },

    goTo(path) {
      navigateTo(path);
    },

    navClass(view) {
      return this.currentView === view ? 'nav-tab active' : 'nav-tab';
    },

    async doLogin() {
      this.loginLoading = true;
      this.loginError = '';
      try {
        await login(this.loginPassword);
        this.authenticated = true;
        this.showLoginModal = false;
        this.loginPassword = '';
      } catch (e) {
        this.loginError = e.message || 'Login failed';
      } finally {
        this.loginLoading = false;
      }
    },

    async doLogout() {
      try {
        await logout();
      } catch (_) {}
      this.authenticated = false;
    },

    requireAuth() {
      if (!this.authenticated) {
        this.showLoginModal = true;
        return false;
      }
      return true;
    },
  };
}

/* ──────────────────────────────────────────────────────────
   Alpine registrations — called after Alpine is ready
────────────────────────────────────────────────────────── */

document.addEventListener('alpine:init', () => {
  Alpine.data('app', app);
  Alpine.data('playView', playView);
  Alpine.data('libraryView', libraryView);
  Alpine.data('ingestView', ingestView);
  Alpine.data('statsView', statsView);
});
