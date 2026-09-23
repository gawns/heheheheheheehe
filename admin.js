/**
 * Ine Mebel Jepara - Admin Panel Script
 * Product CRUD lengkap 28 field + login admin (token dari /api/login)
 */

'use strict';

const API_BASE = 'api';
const TOKEN_KEY = 'imj_admin_token';
let productCache = [];
const DEFAULT_IMG = 'img/produk-sofa-klasik-marun.jpeg';

function getToken() { return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY) || ''; }
function setToken(t) { sessionStorage.setItem(TOKEN_KEY, t); }
function clearToken() { sessionStorage.removeItem(TOKEN_KEY); localStorage.removeItem(TOKEN_KEY); }

/* ===============================================================
   API HELPER
   =============================================================== */
async function apiFetch(path, options = {}) {
  const headers = Object.assign({ 'Accept': 'application/json' }, options.headers || {});
  // Biarkan browser menetapkan Content-Type (beserta boundary) untuk FormData.
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  if (options.body && !isFormData) headers['Content-Type'] = 'application/json';
  const token = getToken();
  if (token) headers['X-Admin-Token'] = token;

  if (location.protocol === 'file:') {
    return { ok: false, status: 0, data: {
      success: false,
      message: 'Halaman dibuka lewat file:// - server Flask tidak berjalan. Jalankan "python app.py" lalu buka http://127.0.0.1:5000/admin.html',
    }};
  }

  let res;
  try {
    res = await fetch(`${API_BASE}/${path}`, Object.assign({}, options, { headers }));
  } catch (netErr) {
    return { ok: false, status: 0, data: {
      success: false,
      message: `Tidak dapat menghubungi server (${path}). Pastikan MySQL (Laragon) berjalan dan "python app.py" sudah dijalankan.`,
    }};
  }

  let data;
  const raw = await res.text();
  try { data = JSON.parse(raw); }
  catch {
    const snippet = raw.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 160);
    data = { success: false, message: `Respons server tidak valid (HTTP ${res.status}).` + (snippet ? ` Isi: ${snippet}` : '') };
  }

  // Sesi kedaluwarsa / token tidak valid -> bersihkan token supaya gate muncul lagi.
  if (res.status === 401 && !/login/i.test(path)) {
    clearToken();
  }

  return { ok: res.ok, status: res.status, data };
}

async function refreshProducts() {
  const { data } = await apiFetch('products?include_all=1');
  productCache = (data && data.success) ? data.products : [];
  return productCache;
}

function getProducts() { return productCache; }

/* ===============================================================
   ELEMENTS
   =============================================================== */
const dashboard      = document.getElementById('admin-dashboard');
const toast          = document.getElementById('toast');
const deleteDialog   = document.getElementById('delete-dialog');
const gate           = document.getElementById('admin-gate');

const formSection    = document.getElementById('admin-form-section');
const formTitle      = document.getElementById('form-section-title');
const productForm    = document.getElementById('product-form');
const editIdInput    = document.getElementById('edit-product-id');
const imgPreviewWrap = document.getElementById('img-preview-wrap');
const imgPreview     = document.getElementById('img-preview');
const formError      = document.getElementById('form-error');

const addBtn         = document.getElementById('btn-add-product');
const addBtnSidebar  = document.getElementById('btn-add-sidebar');
const refreshBtn     = document.getElementById('btn-refresh');
const cancelBtn      = document.getElementById('btn-cancel-form');
const cancelBtn2     = document.getElementById('btn-cancel-form-2');
const statsRow       = document.getElementById('admin-stats');
const tableWrap      = document.getElementById('admin-product-table-wrap');
const searchInput    = document.getElementById('admin-search');
const filterCat      = document.getElementById('admin-filter-cat');

/* ===============================================================
   FIELD REFS (28 field)
   =============================================================== */
const F = {
  name:        document.getElementById('field-name'),
  sku:         document.getElementById('field-sku'),
  category:    document.getElementById('field-category'),
  subcategory: document.getElementById('field-subcategory'),
  brand:       document.getElementById('field-brand'),
  price:       document.getElementById('field-price'),
  discount:    document.getElementById('field-discount-price'),
  stock:       document.getElementById('field-stock'),
  status:      document.getElementById('field-status'),
  condition:   document.getElementById('field-condition'),
  desc:        document.getElementById('field-desc'),
  material:    document.getElementById('field-material'),
  woodType:    document.getElementById('field-wood-type'),
  warna:       document.getElementById('field-warna'),
  finishing:   document.getElementById('field-finishing'),
  berat:       document.getElementById('field-berat'),
  dimP:        document.getElementById('field-dimensi-panjang'),
  dimL:        document.getElementById('field-dimensi-lebar'),
  dimT:        document.getElementById('field-dimensi-tinggi'),
  kapasitas:   document.getElementById('field-kapasitas-beban'),
  perakitan:   document.getElementById('field-perakitan'),
  img:         document.getElementById('field-img'),
  imgFile:     document.getElementById('field-img-file'),
  imagesFile:  document.getElementById('field-images-file'),
  images:      document.getElementById('field-images'),
  video:       document.getElementById('field-video'),
  pelengkap:   document.getElementById('field-pelengkap'),
  relasiTipe:  document.getElementById('field-relasi-tipe'),
  tags:        document.getElementById('field-tags'),
  garansi:     document.getElementById('field-garansi'),
};

/* ===============================================================
   INIT
   =============================================================== */
async function enterAdmin() {
  if (gate) gate.hidden = true;
  await refreshProducts();
  if (dashboard) dashboard.hidden = false;
  renderDashboard();
  if (addBtn) addBtn.focus();
}

/* ===============================================================
   LOGIN
   =============================================================== */
function renderLoginGate() {
  if (!gate) return;
  gate.innerHTML = `
    <div class="admin-gate__card">
      <h1 class="admin-gate__title">Panel Admin</h1>
      <p class="admin-gate__sub">Masuk untuk mengelola produk Ine Mebel Jepara.</p>
      <form id="login-form" class="admin-gate__form" autocomplete="off">
        <label class="form-label" for="login-user">Username</label>
        <input class="form-input" id="login-user" name="username" type="text" required autocomplete="username" />
        <label class="form-label" for="login-pass">Password</label>
        <input class="form-input" id="login-pass" name="password" type="password" required autocomplete="current-password" />
        <p class="form-error" id="login-error" role="alert" hidden></p>
        <button class="btn btn--primary admin-gate__btn" type="submit" id="login-submit">Masuk</button>
      </form>
    </div>`;
  gate.hidden = false;
  if (dashboard) dashboard.hidden = true;

  const form = document.getElementById('login-form');
  const errEl = document.getElementById('login-error');
  const submitBtn = document.getElementById('login-submit');
  document.getElementById('login-user')?.focus();

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (errEl) errEl.hidden = true;
    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Memproses...'; }

    const { ok, data } = await apiFetch('login', {
      method: 'POST',
      body: JSON.stringify({
        username: document.getElementById('login-user').value.trim(),
        password: document.getElementById('login-pass').value,
      }),
    });

    if (ok && data.success) {
      if (data.token) setToken(data.token);
      if (dashboard) dashboard.hidden = false;
      gate.hidden = true;
      showToast(data.message || 'Login berhasil.');
      await refreshProducts();
      renderDashboard();
      return;
    }

    if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Masuk'; }
    if (errEl) { errEl.textContent = data.message || 'Login gagal.'; errEl.hidden = false; }
  });
}

async function initAdmin() {
  try {
    const res = await apiFetch('session');
    const data = res.data || {};
    // Server mati / tidak terjangkau - tetap tampilkan dashboard agar pesan error terlihat.
    if (res.status === 0) {
      if (dashboard) dashboard.hidden = false;
      if (gate) gate.hidden = true;
      await enterAdmin();
      return;
    }
    if (data.auth && !data.authenticated) {
      renderLoginGate();
      return;
    }
    await enterAdmin();
  } catch (err) {
    console.error('initAdmin gagal:', err);
    if (dashboard) dashboard.hidden = false;
    if (gate) gate.hidden = true;
    showToast('Gagal memuat data. Periksa koneksi server/MySQL.', 'error');
  }
}

/* ===============================================================
   TOAST
   =============================================================== */
let toastTimer;
function showToast(msg, type = 'success') {
  if (!toast) return;
  toast.textContent = msg;
  toast.className = `toast toast--${type}`;
  toast.hidden = false;
  void toast.offsetWidth;
  toast.classList.add('toast--visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.remove('toast--visible');
    toast.addEventListener('transitionend', () => { toast.hidden = true; }, { once: true });
  }, 3000);
}

/* ===============================================================
   HELPERS
   =============================================================== */
function formatRupiah(num) {
  return 'Rp\u00A0' + Number(num || 0).toLocaleString('id-ID');
}

function formatPriceDisplay(num) {
  return Number(num || 0).toLocaleString('id-ID');
}

function parsePrice(str) {
  const num = parseInt(String(str).replace(/\D/g, ''), 10);
  return isNaN(num) || num <= 0 ? null : num;
}

function escapeHTML(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeAttr(str) {
  return String(str || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function titleCase(str) {
  return str.replace(/\b\w/g, c => c.toUpperCase());
}

function sentenceCase(str) {
  return str.replace(/(^\s*\w|[.!?]\s+\w)/g, c => c.toUpperCase());
}

/* ===============================================================
   DASHBOARD RENDER
   =============================================================== */
function renderDashboard() {
  renderStats();
  renderProductTable();
}

function renderStats() {
  if (!statsRow) return;
  const products = getProducts();
  const cats = ['kursi', 'meja', 'sofa', 'lemari', 'aksesoris', 'lainnya'];
  const counts = {};
  cats.forEach(c => { counts[c] = products.filter(p => p.category === c).length; });

  statsRow.innerHTML = `
    <div class="stat-card">
      <span class="stat-card__num">${products.length}</span>
      <span class="stat-card__label">Total produk</span>
    </div>
    ${cats.map(c => `
      <div class="stat-card">
        <span class="stat-card__num">${counts[c]}</span>
        <span class="stat-card__label">${c.charAt(0).toUpperCase() + c.slice(1)}</span>
      </div>
    `).join('')}
  `;
}

function renderProductTable() {
  if (!tableWrap) return;

  const searchQ = (searchInput?.value || '').toLowerCase().trim();
  const filterVal = filterCat?.value || '';
  let products = getProducts();

  if (filterVal) products = products.filter(p => p.category === filterVal);
  if (searchQ) products = products.filter(p =>
    p.name.toLowerCase().includes(searchQ) ||
    p.desc.toLowerCase().includes(searchQ) ||
    (p.sku || '').toLowerCase().includes(searchQ)
  );

  if (products.length === 0) {
    tableWrap.innerHTML = `<div class="admin-empty"><p>Tidak ada produk ditemukan.</p></div>`;
    return;
  }

  tableWrap.innerHTML = `
    <table class="admin-table" aria-label="Daftar produk">
      <thead>
        <tr>
          <th scope="col" style="width:60px">Foto</th>
          <th scope="col">Produk</th>
          <th scope="col" style="width:110px">Kategori</th>
          <th scope="col" style="width:90px">Stok</th>
          <th scope="col" style="width:100px">Status</th>
          <th scope="col" style="width:150px">Harga</th>
          <th scope="col" style="width:140px">Aksi</th>
        </tr>
      </thead>
      <tbody>
        ${products.map(p => {
          const harga = p.discountPrice && p.discountPrice < p.price ? p.discountPrice : p.price;
          const diskon = p.discountPrice && p.discountPrice < p.price;
          const stok = p.stock ?? 0;
          const stokKelas = stok === 0 ? 'admin-table__stock--out' : (stok <= 5 ? 'admin-table__stock--low' : '');
          return `
          <tr data-product-id="${p.id}">
            <td>
              <img src="${escapeAttr(p.img || DEFAULT_IMG)}" alt="" class="admin-table__thumb"
                width="52" height="52" loading="lazy"
                data-fallback="${escapeAttr(DEFAULT_IMG)}" />
            </td>
            <td>
              <strong class="admin-table__name">${escapeHTML(p.name)}</strong>
              <span class="admin-table__desc">${escapeHTML(p.sku || '-')} - ${escapeHTML(p.desc)}</span>
            </td>
            <td><span class="cat-badge cat-badge--${escapeAttr(p.category)}">${escapeHTML(p.category)}</span></td>
            <td><span class="admin-table__stock ${stokKelas}">${stok}</span></td>
            <td><span class="status-badge status-badge--${escapeAttr(p.status || 'aktif')}">${escapeHTML(p.status || 'aktif')}</span></td>
            <td class="admin-table__price">
              ${formatRupiah(harga)}
              ${diskon ? `<span class="admin-table__price-old">${formatRupiah(p.price)}</span>` : ''}
            </td>
            <td class="admin-table__actions">
              <div>
                <button type="button" class="admin-btn-edit" data-id="${p.id}" aria-label="Edit ${escapeAttr(p.name)}">Edit</button>
                <button type="button" class="admin-btn-delete" data-id="${p.id}" aria-label="Hapus ${escapeAttr(p.name)}">Hapus</button>
              </div>
            </td>
          </tr>
        `;}).join('')}
      </tbody>
    </table>
  `;

  tableWrap.querySelectorAll('.admin-btn-edit').forEach(btn => {
    btn.addEventListener('click', () => openEditForm(Number(btn.dataset.id)));
  });
  tableWrap.querySelectorAll('.admin-btn-delete').forEach(btn => {
    btn.addEventListener('click', () => confirmDelete(Number(btn.dataset.id)));
  });
  tableWrap.querySelectorAll('.admin-table__thumb[data-fallback]').forEach(img => {
    img.addEventListener('error', function onErr() {
      img.removeEventListener('error', onErr);
      const fb = img.dataset.fallback;
      if (fb && img.src !== fb) img.src = fb;
    });
  });
}

/* ===============================================================
   FORM - ADD / EDIT
   =============================================================== */
function nextSku() {
  // Cari nomor terbesar dari SKU berformat IMJ-#### lalu tambah 1.
  let max = 0;
  getProducts().forEach(p => {
    const m = String(p.sku || '').match(/(\d+)\s*$/);
    if (m) max = Math.max(max, parseInt(m[1], 10));
  });
  return `IMJ-${String(max + 1).padStart(4, '0')}`;
}

function lockSkuField() {
  // SKU terkunci: read-only + tidak ikut ter-submit sebagai perubahan.
  if (!F.sku) return;
  F.sku.readOnly = true;
  F.sku.setAttribute('aria-readonly', 'true');
  F.sku.classList.add('form-input--locked');
}

function openAddForm() {
  resetForm();
  if (formTitle) formTitle.textContent = 'Tambah Produk Baru';
  const saveBtn = document.getElementById('btn-save-product');
  if (saveBtn) saveBtn.textContent = 'Simpan Produk';

  // Auto-generate SKU (terkunci)
  if (F.sku) F.sku.value = nextSku();
  lockSkuField();

  showFormSection();
}

function openEditForm(id) {
  const product = getProducts().find(p => p.id === id);
  if (!product) return;

  resetForm();
  if (formTitle) formTitle.textContent = 'Edit Produk';
  const saveBtn = document.getElementById('btn-save-product');
  if (saveBtn) saveBtn.textContent = 'Perbarui Produk';

  editIdInput.value = id;
  F.name.value        = product.name || '';
  F.sku.value         = product.sku || '';
  F.category.value    = product.category || '';
  F.subcategory.value = product.subcategory || '';
  F.brand.value       = product.brand || '';
  F.price.value       = formatPriceDisplay(product.price);
  F.discount.value    = product.discountPrice ? formatPriceDisplay(product.discountPrice) : '';
  F.stock.value       = product.stock || 0;
  F.status.value      = product.status || 'aktif';
  F.condition.value   = product.kondisi || 'baru';
  F.desc.value        = product.desc || '';
  F.material.value    = product.material || '';
  F.woodType.value    = product.woodType || '';
  F.warna.value       = product.warna || '';
  F.finishing.value   = product.finishing || '';
  F.berat.value       = product.berat || '';
  F.dimP.value        = product.dimensiPanjang || '';
  F.dimL.value        = product.dimensiLebar || '';
  F.dimT.value        = product.dimensiTinggi || '';
  F.kapasitas.value   = product.kapasitasBeban || '';
  F.perakitan.value   = product.perakitan || 'sudah';
  F.img.value         = product.img || '';
  F.images.value      = (product.images || []).join(', ');
  F.video.value       = product.videoUrl || '';
  F.pelengkap.value   = product.pelengkap || '';
  F.relasiTipe.value  = product.relasiTipe || '';
  F.tags.value        = (product.tags || []).join(', ');
  F.garansi.value     = product.garansi || '';

  if (product.img) showImgPreview(product.img);
  lockSkuField();
  showFormSection();
}

function resetForm() {
  if (!productForm) return;
  productForm.reset();
  if (editIdInput) editIdInput.value = '';
  if (F.imgFile) F.imgFile.value = '';
  if (F.imagesFile) F.imagesFile.value = '';
  if (formError) { formError.hidden = true; formError.textContent = ''; }
  if (imgPreviewWrap) imgPreviewWrap.hidden = true;
  if (imgPreview) imgPreview.src = '';
  productForm.querySelectorAll('.form-input').forEach(el => el.classList.remove('input--error'));
  if (F.status) F.status.value = 'aktif';
  if (F.condition) F.condition.value = 'baru';
  if (F.perakitan) F.perakitan.value = 'sudah';
  if (F.stock) F.stock.value = '0';
}

function showFormSection() {
  if (!formSection) return;
  formSection.hidden = false;
  formSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  setTimeout(() => F.name && F.name.focus(), 300);
}

function hideFormSection() {
  if (!formSection) return;
  formSection.hidden = true;
  resetForm();
  if (addBtn) addBtn.focus();
}

if (addBtn)        addBtn.addEventListener('click', openAddForm);
if (addBtnSidebar) addBtnSidebar.addEventListener('click', openAddForm);
if (cancelBtn)     cancelBtn.addEventListener('click', hideFormSection);
if (cancelBtn2)    cancelBtn2.addEventListener('click', hideFormSection);

if (refreshBtn) {
  refreshBtn.addEventListener('click', async () => {
    refreshBtn.disabled = true;
    await refreshProducts();
    renderDashboard();
    refreshBtn.disabled = false;
    showToast('Data produk dimuat ulang.');
  });
}

/* Tutup form saat tombol Escape ditekan */
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && formSection && !formSection.hidden) hideFormSection();
});

/* -- Form Submit -- */
if (productForm) {
  productForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (formError) formError.hidden = true;

    const payload = {
      name:           F.name.value.trim(),
      sku:            F.sku.value.trim(),
      category:       F.category.value,
      subcategory:    F.subcategory.value.trim(),
      brand:          F.brand.value.trim(),
      price:          parsePrice(F.price.value),
      discountPrice:  parsePrice(F.discount.value) || null,
      stock:          parseInt(F.stock.value, 10) || 0,
      status:         F.status.value,
      kondisi:        F.condition.value,
      desc:           F.desc.value.trim(),
      material:       F.material.value.trim(),
      woodType:       F.woodType.value,
      warna:          F.warna.value.trim(),
      finishing:      F.finishing.value,
      berat:          F.berat.value.trim(),
      dimensiPanjang: parseFloat(F.dimP.value) || 0,
      dimensiLebar:   parseFloat(F.dimL.value) || 0,
      dimensiTinggi:  parseFloat(F.dimT.value) || 0,
      kapasitasBeban: parseFloat(F.kapasitas.value) || null,
      perakitan:      F.perakitan.value,
      img:            F.img.value.trim(),
      images:         F.images.value.split(',').map(s => s.trim()).filter(Boolean),
      videoUrl:       F.video.value.trim(),
      pelengkap:      F.pelengkap.value.trim(),
      relasiTipe:     F.relasiTipe.value,
      tags:           F.tags.value.split(',').map(s => s.trim()).filter(Boolean),
      garansi:        F.garansi.value.trim(),
    };

    // Foto utama wajib: dari URL/path ATAU file yang diunggah.
    const mainFile = F.imgFile && F.imgFile.files[0] ? F.imgFile.files[0] : null;
    if (!payload.img && !mainFile) payload.img = DEFAULT_IMG;

    if (!payload.name || !payload.sku || !payload.category || !payload.desc || !payload.price) {
      if (formError) {
        formError.textContent = 'Mohon isi semua field wajib (*).';
        formError.hidden = false;
      }
      return;
    }

    const extraFiles = F.imagesFile ? Array.from(F.imagesFile.files) : [];

    // PENTING: editId harus dibaca SEBELUM dipakai (hindari Temporal Dead Zone).
    const editId = editIdInput && editIdInput.value ? Number(editIdInput.value) : null;

    // Bila ada file yang dipilih -> kirim multipart/form-data (server menyimpan ke img/).
    let requestInit;
    if (mainFile || extraFiles.length) {
      const fd = new FormData();
      Object.entries(payload).forEach(([key, val]) => {
        if (Array.isArray(val)) {
          val.forEach(v => fd.append(`${key}[]`, v));
        } else if (val !== null && val !== undefined) {
          fd.append(key, val);
        }
      });
      if (mainFile) fd.append('img', mainFile);
      extraFiles.forEach(f => fd.append('images[]', f));
      requestInit = { method: editId ? 'PUT' : 'POST', body: fd };
    } else {
      requestInit = { method: editId ? 'PUT' : 'POST', body: JSON.stringify(payload) };
    }

    const saveBtn = document.getElementById('btn-save-product');
    const oldLabel = saveBtn ? saveBtn.textContent : '';
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Menyimpan...'; }

    try {
      const { ok, data } = editId
        ? await apiFetch(`products?id=${editId}`, requestInit)
        : await apiFetch('products', requestInit);

      if (!ok || !data.success) {
        if (formError) {
          formError.textContent = data.message || 'Gagal menyimpan produk.';
          formError.hidden = false;
        }
        return;
      }

      showToast(data.message || (editId ? `"${payload.name}" diperbarui.` : `"${payload.name}" ditambahkan.`));
      hideFormSection();
      await refreshProducts();
      renderDashboard();
    } catch (err) {
      if (formError) {
        formError.textContent = 'Tidak dapat menghubungi server.';
        formError.hidden = false;
      }
    } finally {
      if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = oldLabel; }
    }
  });
}

/* ===============================================================
   DELETE
   =============================================================== */
let pendingDeleteId = null;

function confirmDelete(id) {
  const product = getProducts().find(p => p.id === id);
  if (!product) return;

  const body = document.getElementById('delete-dialog-body');
  if (body) body.textContent = `"${product.name}" akan dihapus permanen dan tidak bisa dikembalikan.`;

  const canModal = deleteDialog && typeof deleteDialog.showModal === 'function';
  if (!canModal) {
    if (window.confirm(`Hapus "${product.name}" secara permanen?`)) doDelete(id, product.name);
    return;
  }

  pendingDeleteId = id;
  deleteDialog.showModal();
}

function closeDeleteDialog() {
  if (deleteDialog && deleteDialog.open) deleteDialog.close();
}

if (deleteDialog) {
  const confirmBtn  = deleteDialog.querySelector('[data-dialog-confirm]');
  const cancelBtnEl = deleteDialog.querySelector('[data-dialog-cancel]');

  confirmBtn?.addEventListener('click', () => {
    const id = pendingDeleteId;
    const name = getProducts().find(p => p.id === id)?.name || '';
    pendingDeleteId = null;
    closeDeleteDialog();
    if (id != null) doDelete(id, name);
  });
  cancelBtnEl?.addEventListener('click', () => {
    pendingDeleteId = null;
    closeDeleteDialog();
  });
  deleteDialog.addEventListener('click', (e) => {
    if (e.target === deleteDialog) { pendingDeleteId = null; closeDeleteDialog(); }
  });
  deleteDialog.addEventListener('cancel', () => { pendingDeleteId = null; });
}

async function doDelete(id, name) {
  try {
    const { ok, data } = await apiFetch(`products?id=${id}`, { method: 'DELETE' });
    if (!ok || !data.success) {
      showToast(data.message || 'Gagal menghapus produk.', 'error');
      return;
    }
    showToast(data.message || `"${name}" berhasil dihapus.`, 'success');
    if (editIdInput.value === String(id)) hideFormSection();
    await refreshProducts();
    renderDashboard();
  } catch {
    showToast('Tidak dapat menghubungi server.', 'error');
  }
}

/* ===============================================================
   AUTO-CAPITALIZE
   =============================================================== */
if (F.name) {
  F.name.addEventListener('input', () => {
    const pos = F.name.selectionStart;
    const fixed = titleCase(F.name.value);
    if (fixed !== F.name.value) {
      F.name.value = fixed;
      F.name.setSelectionRange(pos, pos);
    }
  });
}

if (F.desc) {
  F.desc.addEventListener('input', () => {
    const pos = F.desc.selectionStart;
    const fixed = sentenceCase(F.desc.value);
    if (fixed !== F.desc.value) {
      F.desc.value = fixed;
      F.desc.setSelectionRange(pos, pos);
    }
  });
}

/* ===============================================================
   PRICE FORMATTING
   =============================================================== */
if (F.price) {
  F.price.addEventListener('input', () => {
    const raw = F.price.value.replace(/\D/g, '');
    const num = parseInt(raw, 10);
    const pos = F.price.selectionStart;
    const oldLen = F.price.value.length;
    F.price.value = isNaN(num) ? '' : formatPriceDisplay(num);
    const newLen = F.price.value.length;
    const newPos = Math.max(0, pos + (newLen - oldLen));
    F.price.setSelectionRange(newPos, newPos);
  });
  F.price.addEventListener('blur', () => {
    const num = parsePrice(F.price.value);
    F.price.value = num ? formatPriceDisplay(num) : '';
  });
}

if (F.discount) {
  F.discount.addEventListener('input', () => {
    const raw = F.discount.value.replace(/\D/g, '');
    const num = parseInt(raw, 10);
    F.discount.value = isNaN(num) ? '' : formatPriceDisplay(num);
  });
}

/* ===============================================================
   IMAGE PREVIEW
   =============================================================== */
function showImgPreview(url) {
  if (!imgPreviewWrap || !imgPreview) return;
  if (!url) { imgPreviewWrap.hidden = true; return; }
  imgPreview.src = url;
  imgPreviewWrap.hidden = false;
  imgPreview.onerror = () => { imgPreviewWrap.hidden = true; };
}

if (F.img) {
  let imgDebounce;
  F.img.addEventListener('input', () => {
    clearTimeout(imgDebounce);
    imgDebounce = setTimeout(() => showImgPreview(F.img.value.trim()), 600);
  });
}

/* -- Unggah foto dari perangkat lokal: langsung upload ke img/ -- */

// Inti proses unggah (dipakai oleh <input type=file> DAN drag & drop).
async function uploadImageFiles(input, files, { multiple = false, targetInput, preview = false, dropzone = null } = {}) {
  files = Array.from(files || []).filter(Boolean);
  if (!files.length) return;

  if (dropzone) dropzone.classList.add('dropzone--busy');

  const fd = new FormData();
  files.forEach(f => fd.append(multiple ? 'images[]' : 'img', f));

  const { ok, data } = await apiFetch('upload', { method: 'POST', body: fd });

  if (dropzone) dropzone.classList.remove('dropzone--busy');

  if (!ok || !data.success || !data.files || !data.files.length) {
    showToast((data && data.message) || 'Gagal mengunggah foto.', 'error');
    return;
  }

  const paths = data.files;
  if (targetInput) {
    if (multiple) {
      const existing = targetInput.value.split(',').map(s => s.trim()).filter(Boolean);
      targetInput.value = existing.concat(paths).join(', ');
    } else {
      targetInput.value = paths[0];
    }
  }
  if (preview && paths[0]) showImgPreview(paths[0]);
  showToast(`Foto diunggah: ${paths.join(', ')}`, 'success');
}

// Pasang handler klik-pilih + drag & drop pada <input type=file> dan dropzone-nya.
async function handleFileUpload(input, { multiple = false, targetInput, preview = false } = {}) {
  if (!input) return;

  input.addEventListener('change', async () => {
    await uploadImageFiles(input, input.files, { multiple, targetInput, preview });
    input.value = ''; // biar file yang sama bisa dipilih ulang
  });

  // Cari elemen dropzone terdekat (bisa induk langsung atau via data-dropzone).
  const dropzone = input.closest('.dropzone') ||
    document.querySelector(`.dropzone[data-dropzone="${input.id === 'field-images-file' ? 'extra' : 'main'}"]`);
  if (!dropzone) return;

  const setActive = (on) => dropzone.classList.toggle('dropzone--active', on);

  dropzone.addEventListener('click', (e) => {
    // Klik pada input sudah otomatis membuka dialog; hindari dobel.
    if (e.target !== input) input.click();
  });
  dropzone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); }
  });

  ['dragenter', 'dragover'].forEach(evt =>
    dropzone.addEventListener(evt, (e) => { e.preventDefault(); e.stopPropagation(); setActive(true); })
  );
  ['dragleave', 'dragend'].forEach(evt =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault(); e.stopPropagation();
      // Hanya matikan bila kursor benar-benar keluar area dropzone.
      if (!dropzone.contains(e.relatedTarget)) setActive(false);
    })
  );
  dropzone.addEventListener('drop', async (e) => {
    e.preventDefault(); e.stopPropagation();
    setActive(false);

    const dt = e.dataTransfer;
    const dropped = dt && dt.files ? Array.from(dt.files) : [];
    if (!dropped.length) return;

    const onlyImages = dropped.filter(f => f.type.startsWith('image/'));
    if (onlyImages.length !== dropped.length) {
      showToast('Hanya file gambar (JPG, PNG, WEBP, GIF) yang diizinkan.', 'error');
      return;
    }
    if (!multiple && onlyImages.length > 1) {
      showToast('Hanya satu foto utama yang boleh diunggah. Menggunakan foto pertama.', 'info');
    }
    await uploadImageFiles(input, multiple ? onlyImages : onlyImages.slice(0, 1),
      { multiple, targetInput, preview });
  });
}

handleFileUpload(F.imgFile, { targetInput: F.img, preview: true });
handleFileUpload(F.imagesFile, { multiple: true, targetInput: F.images });


/* ===============================================================
   SEARCH & FILTER
   =============================================================== */
if (searchInput) {
  let searchDebounce;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(renderProductTable, 250);
  });
}

if (filterCat) {
  filterCat.addEventListener('change', renderProductTable);
}

/* ===============================================================
   INIT
   =============================================================== */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAdmin);
} else {
  initAdmin();
}
