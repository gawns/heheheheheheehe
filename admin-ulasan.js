/**
 * Ine Mebel Jepara - Halaman Ulasan Admin (admin-ulasan.html)
 * Tambah & hapus ulasan via /api/reviews
 */

'use strict';

let productCache = [];
let reviewCache = [];
let pendingDeleteId = null;

const reviewForm      = document.getElementById('review-form');
const reviewProduct   = document.getElementById('review-product');
const reviewRating    = document.getElementById('review-rating');
const reviewName      = document.getElementById('review-name');
const reviewComment   = document.getElementById('review-comment');
const reviewFormErr   = document.getElementById('review-form-error');
const reviewTableWrap = document.getElementById('review-table-wrap');
const reviewSearch    = document.getElementById('review-search');
const deleteReviewDlg = document.getElementById('delete-review-dialog');

function starsText(rating) {
  const n = Math.max(0, Math.min(5, Math.round(Number(rating) || 0)));
  return '★★★★★'.slice(0, n) + '☆☆☆☆☆'.slice(0, 5 - n);
}

function formatDate(value) {
  if (!value) return '-';
  const d = new Date(String(value).replace(' ', 'T'));
  if (isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' });
}

async function loadProducts() {
  const { data } = await apiFetch('products?include_all=1');
  productCache = (data && data.success) ? data.products : [];
  if (reviewProduct) {
    reviewProduct.innerHTML = '<option value="">- Pilih produk -</option>' +
      productCache.map(p => `<option value="${escapeAttr(p.sku)}">${escapeHTML(p.name)} (${escapeHTML(p.sku)})</option>`).join('');
  }
}

async function loadReviews() {
  const { ok, data } = await apiFetch('reviews/all');
  if (!ok || !data.success) {
    reviewCache = [];
  } else {
    reviewCache = Array.isArray(data.reviews) ? data.reviews : [];
  }
  renderReviews();
}

function renderReviews() {
  if (!reviewTableWrap) return;
  const term = (reviewSearch ? reviewSearch.value : '').trim().toLowerCase();
  let rows = reviewCache;
  if (term) {
    rows = rows.filter(r =>
      (r.name || '').toLowerCase().includes(term) ||
      (r.sku || '').toLowerCase().includes(term) ||
      (r.comment || '').toLowerCase().includes(term)
    );
  }

  if (!rows.length) {
    reviewTableWrap.innerHTML = `<div class="admin-empty"><p>${reviewCache.length ? 'Tidak ada ulasan yang cocok dengan pencarian.' : 'Belum ada ulasan. Tambahkan ulasan di formulir atas.'}</p></div>`;
    return;
  }

  const productName = (sku) => {
    const p = productCache.find(x => x.sku === sku);
    return p ? p.name : sku;
  };

  reviewTableWrap.innerHTML = `
    <div class="admin-table-wrap">
      <table class="admin-table">
        <thead>
          <tr>
            <th>Produk</th><th>Pengulas</th><th>Rating</th><th>Ulasan</th><th>Tanggal</th><th>Aksi</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map(r => `
            <tr>
              <td>
                <span class="admin-table__sku">${escapeHTML(r.sku || '-')}</span>
                <span class="admin-table__name-sm">${escapeHTML(productName(r.sku))}</span>
              </td>
              <td>${escapeHTML(r.name)}</td>
              <td><span class="admin-review-stars" title="${r.rating}/5">${starsText(r.rating)}</span></td>
              <td class="admin-review-comment">${escapeHTML(r.comment)}</td>
              <td>${escapeHTML(formatDate(r.createdAt))}</td>
              <td>
                <button type="button" class="admin-btn admin-btn--danger admin-btn-delete-review" data-id="${r.id}" data-name="${escapeAttr(r.name)}">Hapus</button>
              </td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;

  reviewTableWrap.querySelectorAll('.admin-btn-delete-review').forEach(btn => {
    btn.addEventListener('click', () => openDeleteDialog(Number(btn.dataset.id), btn.dataset.name));
  });
}

function openDeleteDialog(id, name) {
  pendingDeleteId = id;
  const body = document.getElementById('delete-review-body');
  if (body) body.textContent = `Ulasan dari "${name}" akan dihapus permanen.`;
  if (deleteReviewDlg && typeof deleteReviewDlg.showModal === 'function') deleteReviewDlg.showModal();
}

function closeDeleteDialog() {
  pendingDeleteId = null;
  if (deleteReviewDlg && deleteReviewDlg.open) deleteReviewDlg.close();
}

async function doDelete(id) {
  const { ok, data } = await apiFetch(`reviews?id=${encodeURIComponent(id)}`, { method: 'DELETE' });
  if (ok && data.success) {
    showToast(data.message || 'Ulasan dihapus.');
    await loadReviews();
  } else {
    showToast(data.message || 'Gagal menghapus ulasan.', 'error');
  }
}

if (reviewForm) {
  reviewForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (reviewFormErr) reviewFormErr.hidden = true;

    const payload = {
      sku: reviewProduct ? reviewProduct.value : '',
      name: reviewName ? reviewName.value.trim() : '',
      rating: reviewRating ? Number(reviewRating.value) : 5,
      comment: reviewComment ? reviewComment.value.trim() : '',
    };

    if (!payload.sku || !payload.name || !payload.comment) {
      if (reviewFormErr) { reviewFormErr.textContent = 'Produk, nama pengulas, dan isi ulasan wajib diisi.'; reviewFormErr.hidden = false; }
      return;
    }

    const saveBtn = document.getElementById('btn-save-review');
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Menyimpan...'; }

    const { ok, data } = await apiFetch('reviews', { method: 'POST', body: JSON.stringify(payload) });

    if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'Simpan Ulasan'; }

    if (ok && data.success) {
      showToast(data.message || 'Ulasan ditambahkan.');
      reviewForm.reset();
      if (reviewRating) reviewRating.value = '5';
      await loadReviews();
    } else if (reviewFormErr) {
      reviewFormErr.textContent = data.message || 'Gagal menyimpan ulasan.';
      reviewFormErr.hidden = false;
    }
  });
}

if (reviewSearch) {
  let t;
  reviewSearch.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(renderReviews, 220);
  });
}

document.getElementById('btn-refresh-reviews')?.addEventListener('click', async () => {
  await loadProducts();
  await loadReviews();
  showToast('Data ulasan dimuat ulang.');
});

deleteReviewDlg?.querySelector('[data-dialog-confirm]')?.addEventListener('click', async () => {
  const id = pendingDeleteId;
  closeDeleteDialog();
  if (id) await doDelete(id);
});
deleteReviewDlg?.querySelector('[data-dialog-cancel]')?.addEventListener('click', closeDeleteDialog);
deleteReviewDlg?.addEventListener('cancel', () => { pendingDeleteId = null; });

requireAdminThen(async () => {
  await loadProducts();
  await loadReviews();
});
