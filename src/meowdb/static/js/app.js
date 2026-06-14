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

    init() {
      // Handle browser back/forward
      window.addEventListener('popstate', () => {
        this.currentView = pathToView(location.pathname);
      });

      // Handle programmatic navigation
      window.addEventListener('route-change', (e) => {
        this.currentView = pathToView(e.detail.path);
      });
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
