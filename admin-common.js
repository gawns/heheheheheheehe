/**
 * Ine Mebel Jepara - Admin: utilitas bersama
 * Dipakai oleh admin.html, admin-stats.html, admin-ulasan.html
 * Berisi: token admin, apiFetch, login gate, toast, & helper format.
 */

'use strict';

const ADMIN_API_BASE = 'api';
const ADMIN_TOKEN_KEY = 'imj_admin_token';

function getToken() { return sessionStorage.getItem(ADMIN_TOKEN_KEY) || localStorage.getItem(ADMIN_TOKEN_KEY) || ''; }
function setToken(t) { sessionStorage.setItem(ADMIN_TOKEN_KEY, t); }
function clearToken() {
  sessionStorage.removeItem(ADMIN_TOKEN_KEY);
  localStorage.removeItem(ADMIN_TOKEN_KEY);
}

async function apiFetch(path, options = {}) {
  const headers = Object.assign({ 'Accept': 'application/json' }, options.headers || {});
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
    res = await fetch(`${ADMIN_API_BASE}/${path}`, Object.assign({}, options, { headers }));
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

/* ---------------------------- TOAST ---------------------------- */
let adminToastTimer;
function showToast(msg, type = 'success') {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.className = `toast toast--${type}`;
  toast.hidden = false;
  void toast.offsetWidth;
  toast.classList.add('toast--visible');
  clearTimeout(adminToastTimer);
  adminToastTimer = setTimeout(() => {
    toast.classList.remove('toast--visible');
    toast.addEventListener('transitionend', () => { toast.hidden = true; }, { once: true });
  }, 3200);
}

/* ---------------------------- FORMAT ---------------------------- */
function formatRupiah(num) {
  return 'Rp\u00A0' + Number(num || 0).toLocaleString('id-ID');
}

function escapeHTML(str) {
  return String(str == null ? '' : str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeAttr(str) {
  return String(str == null ? '' : str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function formatNumber(n) {
  return Number(n || 0).toLocaleString('id-ID');
}

/* ---------------------------- LOGIN GATE ---------------------------- */
/**
 * Cek sesi lalu jalankan onReady() bila admin sudah login.
 * Bila belum, tampilkan form login di elemen #admin-gate.
 */
async function requireAdminThen(onReady) {
  const gate = document.getElementById('admin-gate');
  const dashboard = document.getElementById('admin-dashboard');

  const run = async () => {
    if (gate) gate.hidden = true;
    if (dashboard) dashboard.hidden = false;
    try { await onReady(); }
    catch (err) { console.error(err); showToast('Gagal memuat data.', 'error'); }
  };

  const renderLoginGate = () => {
    if (!gate) return;
    gate.innerHTML = `
      <div class="admin-gate__card">
        <h1 class="admin-gate__title">Panel Admin</h1>
        <p class="admin-gate__sub">Masuk untuk mengelola Ine Mebel Jepara.</p>
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
    document.getElementById('login-user')?.focus();

    document.getElementById('login-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const errEl = document.getElementById('login-error');
      const submitBtn = document.getElementById('login-submit');
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
        showToast(data.message || 'Login berhasil.');
        await run();
        return;
      }
      if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Masuk'; }
      if (errEl) { errEl.textContent = data.message || 'Login gagal.'; errEl.hidden = false; }
    });
  };

  try {
    const res = await apiFetch('session');
    const data = res.data || {};

    // Server tidak terjangkau (status 0) -> tampilkan dashboard agar pesan error terlihat.
    if (res.status === 0) { await run(); return; }

    // Auth aktif & belum login -> tampilkan form login.
    if (data.auth === true && data.authenticated !== true) {
      renderLoginGate();
      return;
    }

    await run();
  } catch (err) {
    console.error('requireAdminThen gagal:', err);
    if (gate) renderLoginGate();
    showToast('Gagal memuat data. Periksa koneksi server/MySQL.', 'error');
  }
}
