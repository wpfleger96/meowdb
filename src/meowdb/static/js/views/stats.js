/* ============================================================
   views/stats.js — Stats dashboard Alpine component
   ============================================================ */

function statsView() {
  return {
    stats: null,
    isLoading: false,
    error: null,

    async init() {
      await this.load();
    },

    async load() {
      this.isLoading = true;
      this.error = null;
      try {
        this.stats = await getStats();
      } catch (err) {
        this.error = err.message || 'Failed to load stats';
        showToast(this.error, 'error');
      } finally {
        this.isLoading = false;
      }
    },

    async playLeaderboardMeow(meow) {
      if (!meow?.mp3_url) return;
      audioPlayer.stop();
      recordPlay(meow.id).catch(() => {});
      audioPlayer.onEnded = null;
      audioPlayer.onError = (err) => showToast('Playback error: ' + err.message, 'error');
      try {
        await audioPlayer.play(meow.mp3_url);
      } catch {}
    },

    /* ──────────────────────────────────────────────────────
       Formatting helpers
    ────────────────────────────────────────────────────── */

    formatDuration(ms) {
      if (!ms && ms !== 0) return '—';
      const totalSeconds = Math.round(ms / 1000);
      if (totalSeconds < 60) return `${totalSeconds}s`;
      const m = Math.floor(totalSeconds / 60);
      const s = totalSeconds % 60;
      if (m < 60) return s > 0 ? `${m}m ${s}s` : `${m}m`;
      const h = Math.floor(m / 60);
      const rm = m % 60;
      return rm > 0 ? `${h}h ${rm}m` : `${h}h`;
    },

    formatDate(iso) {
      if (!iso) return '—';
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    },

    formatId(id) {
      if (!id) return '';
      return id.slice(0, 8) + '…';
    },

    get totalDurationFormatted() {
      return this.formatDuration(this.stats?.total_duration_ms ?? null);
    },

    get avgDurationFormatted() {
      return this.formatDuration(this.stats?.avg_duration_ms ?? null);
    },

    get firstMeowDate() {
      if (!this.stats?.recent?.length) return '—';
      // Most-recent is first in the list; iterate to find oldest via created_at
      // The API returns last 10, so we rely on the backend for "first" date
      // If the backend exposes it directly, use it; otherwise fall back.
      return this.stats.first_meow_at
        ? this.formatDate(this.stats.first_meow_at)
        : '—';
    },
  };
}
