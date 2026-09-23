/**
 * Ine Mebel Jepara - Halaman Statistik Admin (admin-stats.html)
 * Memuat analitik dari /api/admin/stats
 */

'use strict';

const DEFAULT_IMG = 'img/produk-sofa-klasik-marun.jpeg';

function shortDateLabel(iso) {
  const d = new Date(iso + 'T00:00:00');
  if (isNaN(d)) return iso;
  return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
}

function renderStatCards(stats) {
  const el = document.getElementById('stats-cards');
  if (!el) return;
  const vis = stats.visitors || {};
  const fav = stats.favoriteTrend || [];
  const favTotal = fav.reduce((sum, d) => sum + (d.added || 0), 0);
  const favRemoved = fav.reduce((sum, d) => sum + (d.removed || 0), 0);
  const viewsTotal = (stats.popular || []).reduce((sum, p) => sum + (p.views || 0), 0);
  const avg = stats.days > 0 ? Math.round((vis.total || 0) / stats.days) : 0;

  el.innerHTML = `
    <div class="stat-card">
      <span class="stat-card__label">Pengunjung Hari Ini</span>
      <span class="stat-card__value">${formatNumber(vis.today)}</span>
      <span class="stat-card__hint">Rata-rata ${formatNumber(avg)}/hari</span>
    </div>
    <div class="stat-card">
      <span class="stat-card__label">Pengunjung ${formatNumber(stats.days)} Hari</span>
      <span class="stat-card__value">${formatNumber(vis.total)}</span>
      <span class="stat-card__hint">Total kunjungan unik</span>
    </div>
    <div class="stat-card">
      <span class="stat-card__label">Lihat Produk</span>
      <span class="stat-card__value">${formatNumber(viewsTotal)}</span>
      <span class="stat-card__hint">Total dari produk terpopuler</span>
    </div>
    <div class="stat-card">
      <span class="stat-card__label">Favorit Ditambahkan</span>
      <span class="stat-card__value">${formatNumber(favTotal)}</span>
      <span class="stat-card__hint">${formatNumber(favRemoved)} dihapus</span>
    </div>
  `;
}

function renderChart(containerId, series) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!series.length) {
    el.innerHTML = '<p class="chart-empty">Belum ada data pada periode ini.</p>';
    return;
  }
  const max = Math.max(1, ...series.map(d => d.value));
  el.innerHTML = series.map(d => {
    const pct = Math.round((d.value / max) * 100);
    const cls = d.mod ? ` chart-col__bar--${d.mod}` : '';
    return `
      <div class="chart-col" title="${escapeAttr(d.label)}: ${d.value}">
        <span class="chart-col__value">${d.value > 0 ? d.value : ''}</span>
        <div class="chart-col__bar-wrap">
          <div class="chart-col__bar${cls}" style="height:${Math.max(3, pct)}%;"></div>
        </div>
        <span class="chart-col__label">${escapeHTML(d.short)}</span>
      </div>`;
  }).join('');
}

function renderVisitsChart(visitors) {
  const perDay = (visitors && visitors.perDay) || [];
  renderChart('stats-visits-chart', perDay.map(d => ({
    label: shortDateLabel(d.date),
    short: shortDateLabel(d.date),
    value: d.visitors ?? d.count ?? 0,
  })));
}

function renderFavoriteChart(trend) {
  renderChart('stats-fav-chart', (trend || []).map(d => ({
    label: `${shortDateLabel(d.date)} (+${d.added || 0}/-${d.removed || 0})`,
    short: shortDateLabel(d.date),
    value: (d.added || 0) + (d.removed || 0),
    mod: (d.added || 0) >= (d.removed || 0) ? 'fav' : 'rmv',
  })));
}

function renderPopular(products) {
  const el = document.getElementById('stats-popular');
  if (!el) return;
  if (!products || !products.length) {
    el.innerHTML = '<p class="chart-empty">Belum ada produk yang dilihat.</p>';
    return;
  }
  const max = Math.max(1, ...products.map(p => p.views || 0));
  el.innerHTML = products.map((p, i) => `
    <div class="stats-row">
      <span class="stats-row__rank">#${i + 1}</span>
      <img class="stats-row__img" src="${escapeAttr(p.img || DEFAULT_IMG)}" alt=""
        width="40" height="40" loading="lazy" data-fallback="${escapeAttr(DEFAULT_IMG)}" />
      <div class="stats-row__body">
        <p class="stats-row__name">${escapeHTML(p.name || ('Produk #' + p.id))}</p>
        <p class="stats-row__meta">${escapeHTML(p.category || '-')} &middot; ${formatNumber(p.views)} kali dilihat</p>
        <div class="stats-bar" style="width:${Math.round(((p.views || 0) / max) * 100)}%;"></div>
      </div>
      <span class="stats-row__val">${formatNumber(p.favorites)} &#9825;</span>
    </div>`).join('');

  el.querySelectorAll('.stats-row__img[data-fallback]').forEach(img => {
    img.addEventListener('error', function onErr() {
      img.removeEventListener('error', onErr);
      const fb = img.dataset.fallback;
      if (fb && !img.src.endsWith(fb)) img.src = fb;
    });
  });
}

function renderCategories(categories) {
  const el = document.getElementById('stats-categories');
  if (!el) return;
  if (!categories || !categories.length) {
    el.innerHTML = '<p class="chart-empty">Belum ada data kategori.</p>';
    return;
  }
  const max = Math.max(1, ...categories.map(c => c.count || 0));
  el.innerHTML = categories.map(c => `
    <div class="stats-row">
      <div class="stats-row__body">
        <p class="stats-row__name">${escapeHTML(c.category || '-')}</p>
        <div class="stats-bar" style="width:${Math.round(((c.count || 0) / max) * 100)}%;"></div>
      </div>
      <span class="stats-row__val">${formatNumber(c.count)}</span>
    </div>`).join('');
}

async function loadStatistics() {
  const rangeEl = document.getElementById('stats-range');
  const days = rangeEl ? rangeEl.value : '7';
  const wrap = document.getElementById('stats-panel');
  if (wrap) wrap.classList.add('is-loading');

  try {
    const { ok, data } = await apiFetch(`admin/stats?days=${encodeURIComponent(days)}`);
    if (!ok || !data.success) {
      showToast(data.message || 'Gagal memuat statistik.', 'error');
      return;
    }
    const stats = data.stats || {};
    renderStatCards(stats);
    renderVisitsChart(stats.visitors);
    renderFavoriteChart(stats.favoriteTrend);
    renderPopular(stats.popular);
    renderCategories(stats.categories);
  } catch {
    showToast('Tidak dapat menghubungi server.', 'error');
  } finally {
    if (wrap) wrap.classList.remove('is-loading');
  }
}

document.getElementById('stats-range')?.addEventListener('change', loadStatistics);
document.getElementById('btn-refresh-stats')?.addEventListener('click', loadStatistics);

requireAdminThen(loadStatistics);
