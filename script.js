/**
 * Ine Mebel Jepara - Main Script
 * Data: MySQL-backed product store (API Flask)
 * Handles: Intro, Navbar, Mobile menu, Product rendering,
 *          Catalog filters/sort/load-more, Detail page,
 *          Floating WhatsApp FAB, Wishlist
 */

'use strict';

/* ===============================================================
   API - SUMBER DATA (MySQL via Flask)
   =============================================================== */
const API_BASE = 'api';
const PRODUCT_CATEGORIES = ['kursi', 'meja', 'sofa', 'lemari', 'aksesoris', 'lainnya'];

let _productCache   = [];
let _productsLoaded = false;

async function loadProducts(force = false) {
  if (_productsLoaded && !force) return _productCache;

  try {
    const res  = await fetch(`${API_BASE}/products`, { headers: { Accept: 'application/json' } });
    const data = await res.json();
    if (!data.success) throw new Error(data.message || 'Gagal memuat produk');
    _productCache   = Array.isArray(data.products) ? data.products : [];
    _productsLoaded = true;
  } catch (err) {
    console.error('Gagal memuat produk dari server:', err);
    _productCache   = [];
    _productsLoaded = false;
  }
  return _productCache;
}

function getProducts() {
  return Array.isArray(_productCache) ? _productCache : [];
}

function getCategoryCounts(products = getProducts()) {
  return PRODUCT_CATEGORIES.reduce((counts, category) => {
    counts[category] = products.filter(p => p.category === category).length;
    return counts;
  }, { semua: products.length });
}

function syncProductCounts() {
  const counts = getCategoryCounts();
  document.querySelectorAll('.cat-card__count').forEach((el) => {
    const category = el.closest('.cat-card')?.querySelector('.cat-card__link')?.getAttribute('aria-label') || '';
    const found = [...PRODUCT_CATEGORIES].find((value) => category.toLowerCase().includes(value));
    el.textContent = String(found ? counts[found] : counts.semua);
  });
  document.querySelectorAll('.filter-count').forEach((el) => {
    const filter = el.closest('.sidebar-filter-btn')?.dataset.filter;
    if (!filter) return;
    el.textContent = String(filter === 'semua' ? counts.semua : (counts[filter] ?? 0));
  });
}

/* ===============================================================
   HELPERS
   =============================================================== */
function formatRupiah(num) {
  return 'Rp\u00A0' + Number(num).toLocaleString('id-ID');
}

function escapeHTML(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeAttr(str) {
  return String(str || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function detailUrl(product) {
  if (product && product.sku) return `detail.html?sku=${encodeURIComponent(product.sku)}`;
  return `detail.html?id=${product ? product.id : ''}`;
}

function createProductCard(product) {
  const card = document.createElement('article');
  card.className = 'product-card';
  card.dataset.category = product.category;
  card.dataset.status = product.status || 'aktif';
  card.dataset.productId = String(product.id);

  const catLabel = product.category.charAt(0).toUpperCase() + product.category.slice(1);
  const discount = product.discountPrice && product.discountPrice < product.price;
  const displayPrice = discount ? product.discountPrice : product.price;
  const stock = product.stock ?? 0;
  const href = detailUrl(product);

  let badges = '';
  if (product.status === 'draft')    badges += `<span class="product-badge product-badge--draft">Draft</span>`;
  if (product.status === 'nonaktif') badges += `<span class="product-badge product-badge--nonaktif">Nonaktif</span>`;
  if (discount)                      badges += `<span class="product-badge product-badge--discount">-${Math.round((1 - product.discountPrice / product.price) * 100)}%</span>`;
  if (stock === 0)                   badges += `<span class="product-badge product-badge--out">Habis</span>`;

  card.innerHTML = `
    <a href="${href}" class="product-card__img-wrap" tabindex="-1" aria-hidden="true">
      ${badges ? `<div class="product-card__badges">${badges}</div>` : ''}
      <img src="${escapeAttr(product.img)}" alt="${escapeAttr(product.imgAlt || product.name)}"
        width="600" height="450" loading="lazy" />
    </a>
    <div class="product-card__body">
      <p class="product-card__cat">${escapeHTML(catLabel)}${product.sku ? ` - ${escapeHTML(product.sku)}` : ''}</p>
      <h3 class="product-card__name">
        <a href="${href}">${escapeHTML(product.name)}</a>
      </h3>
      <p class="product-card__desc">${escapeHTML(product.desc)}</p>
      <div class="product-card__footer">
        <div>
          <span class="product-card__price">${formatRupiah(displayPrice)}</span>
          ${discount ? `<span class="product-card__price-original">${formatRupiah(product.price)}</span>` : ''}
        </div>
        <button class="wishlist-icon-btn" aria-label="Tambah ${escapeAttr(product.name)} ke wishlist" aria-pressed="false">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
        </button>
      </div>
      ${stock > 0 && stock < 10 ? `<p class="product-card__stock product-card__stock--low">Stok tersisa: ${stock}</p>` : ''}
    </div>
  `;

  const wishlistBtn = card.querySelector('.wishlist-icon-btn');
  syncWishlistBtnState(wishlistBtn, product.id);
  wishlistBtn.addEventListener('click', () => {
    toggleWishlist(product.id);
    syncWishlistBtnState(wishlistBtn, product.id);
  });

  return card;
}

/* ===============================================================
   PELACAKAN STATISTIK (kunjungan, lihat produk, favorit)
   =============================================================== */
const VISITOR_KEY = 'imj_visitor_id_v1';

function getVisitorId() {
  try {
    let id = localStorage.getItem(VISITOR_KEY);
    if (!id) {
      id = 'v-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
      localStorage.setItem(VISITOR_KEY, id);
    }
    return id;
  } catch { return 'anon'; }
}

// Kirim statistik dengan cara "fire and forget" (tidak mengganggu UX).
function sendTrack(path, payload) {
  try {
    fetch(`${API_BASE}/${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {});
  } catch { /* abaikan */ }
}

function trackPageView(page) {
  sendTrack('track/view', { visitorId: getVisitorId(), page: page || 'site' });
}

function trackProductView(productId) {
  if (!productId) return;
  sendTrack('track/product', { productId: Number(productId) });
}

function trackFavorite(productId, action) {
  if (!productId) return;
  sendTrack('track/favorite', { productId: Number(productId), action: action || 'add' });
}

/* ===============================================================
   WISHLIST - per device (localStorage)
   =============================================================== */
const WISHLIST_KEY = 'jn_wishlist_v1';

function getWishlist() {
  try {
    const raw = localStorage.getItem(WISHLIST_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch { return []; }
}

function saveWishlist(ids) {
  try { localStorage.setItem(WISHLIST_KEY, JSON.stringify(ids)); } catch {}
}

function isWishlisted(id) { return getWishlist().includes(Number(id)); }

function toggleWishlist(id) {
  const idNum = Number(id);
  let list = getWishlist();
  const removing = list.includes(idNum);
  if (removing) list = list.filter(x => x !== idNum);
  else list.push(idNum);
  saveWishlist(list);
  trackFavorite(idNum, removing ? 'remove' : 'add');
  refreshWishlistUI();
}

function removeFromWishlist(id) {
  saveWishlist(getWishlist().filter(x => x !== Number(id)));
  trackFavorite(Number(id), 'remove');
  refreshWishlistUI();
}

function clearWishlist() {
  saveWishlist([]);
  refreshWishlistUI();
}

function syncWishlistBtnState(btn, productId) {
  if (!btn) return;
  const added = isWishlisted(productId);
  btn.setAttribute('aria-pressed', String(added));
  const svg = btn.querySelector('svg');
  if (svg) {
    svg.setAttribute('fill', added ? 'var(--clr-neon-purple)' : 'none');
    svg.setAttribute('stroke', added ? 'var(--clr-neon-purple)' : 'currentColor');
  }
}

function syncAllWishlistButtons() {
  // Sinkronkan semua tombol hati (kartu katalog) dengan isi wishlist.
  const list = getWishlist();
  document.querySelectorAll('.product-card').forEach((card) => {
    const btn = card.querySelector('.wishlist-icon-btn');
    if (!btn) return;
    const id = Number(card.dataset.productId);
    syncWishlistBtnState(btn, id);
  });
  // Tombol hati di halaman detail.
  const detailBtn = document.querySelector('.wishlist-btn');
  if (detailBtn && detailBtn.dataset.productId) {
    syncWishlistBtnState(detailBtn, Number(detailBtn.dataset.productId));
  }
}

function refreshWishlistUI() {
  const list = getWishlist();
  const products = getProducts();
  const badge = document.getElementById('wishlist-badge');
  const itemsWrap = document.getElementById('wishlist-items');
  const clearBtn = document.getElementById('wishlist-clear');
  const toggleBtn = document.getElementById('wishlist-toggle');

  if (badge) { badge.textContent = String(list.length); badge.hidden = list.length === 0; }
  if (toggleBtn) toggleBtn.setAttribute('aria-label', `Wishlist (${list.length} item)`);
  if (clearBtn) clearBtn.hidden = list.length === 0;

  // Kartu di katalog harus kembali ke bentuk awal saat item dihapus.
  syncAllWishlistButtons();

  if (!itemsWrap) return;

  if (list.length === 0) {
    itemsWrap.innerHTML = `
      <div class="wishlist-empty">
        <span class="wishlist-empty__icon" aria-hidden="true">☆</span>
        <p>Wishlist kamu masih kosong.</p>
        <p class="wishlist-empty__hint">Tekan ikon ♥ pada produk untuk menyimpannya di device ini.</p>
      </div>`;
    return;
  }

  itemsWrap.innerHTML = list.map((id) => {
    const p = products.find(x => x.id === id);
    if (!p) return '';
    return `
      <a href="${detailUrl(p)}" class="wishlist-item">
        <img src="${escapeAttr(p.img)}" alt="" width="56" height="56" loading="lazy" />
        <span class="wishlist-item__info">
          <strong>${escapeHTML(p.name)}</strong>
          <span class="wishlist-item__price">${formatRupiah(p.price)}</span>
        </span>
        <button class="wishlist-item__remove" data-id="${p.id}" aria-label="Hapus ${escapeAttr(p.name)} dari wishlist" type="button">✕</button>
      </a>`;
  }).join('');

  itemsWrap.querySelectorAll('.wishlist-item__remove').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      removeFromWishlist(Number(btn.dataset.id));
    });
  });
}

function initWishlistPanel() {
  const toggleBtn = document.getElementById('wishlist-toggle');
  const panel = document.getElementById('wishlist-panel');
  const clearBtn = document.getElementById('wishlist-clear');
  if (!toggleBtn || !panel) return;

  toggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = toggleBtn.getAttribute('aria-expanded') === 'true';
    toggleBtn.setAttribute('aria-expanded', String(!isOpen));
    panel.hidden = isOpen;
    if (!isOpen) refreshWishlistUI();
  });

  document.addEventListener('click', (e) => {
    if (panel.hidden) return;
    if (!panel.contains(e.target) && e.target !== toggleBtn && !toggleBtn.contains(e.target)) {
      panel.hidden = true;
      toggleBtn.setAttribute('aria-expanded', 'false');
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !panel.hidden) {
      panel.hidden = true;
      toggleBtn.setAttribute('aria-expanded', 'false');
      toggleBtn.focus();
    }
  });

  if (clearBtn) clearBtn.addEventListener('click', clearWishlist);
  refreshWishlistUI();
}

/* ===============================================================
   INTRO / SPLASH SCREEN
   ---------------------------------------------------------------
   Markup intro ada langsung di index.html (elemen #intro).
   Halaman lain (katalog/detail/admin) tidak punya #intro dan/atau
   memakai <body class="no-intro">, sehingga fungsi ini langsung
   keluar tanpa error.
   =============================================================== */
const INTRO_SESSION_KEY = 'jn_intro_seen';
let introTimers = [];
let introStopDust = null;
let introWatchdog = null;

function introClearTimers() {
  introTimers.forEach(clearTimeout);
  introTimers = [];
  if (introWatchdog) { clearTimeout(introWatchdog); introWatchdog = null; }
}

/* Partikel debu cahaya (canvas ringan). Mengembalikan fungsi stop(). */
function initIntroDust(canvas) {
  const noop = () => {};
  if (!canvas || !canvas.getContext) return noop;
  const ctx = canvas.getContext('2d');
  if (!ctx) return noop;

  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  let w = 0, h = 0, particles = [], rafId = null, running = true;

  const spawn = (randomY) => ({
    x: Math.random() * w,
    y: randomY ? Math.random() * h : h + 10,
    r: 0.6 + Math.random() * 2.2,
    baseAlpha: 0.18 + Math.random() * 0.55,
    vy: -(0.06 + Math.random() * 0.22),
    vx: (Math.random() - 0.5) * 0.16,
    drift: Math.random() * Math.PI * 2,
    driftSpeed: 0.004 + Math.random() * 0.01,
    twinkle: Math.random() * Math.PI * 2,
    twinkleSpeed: 0.008 + Math.random() * 0.02,
  });

  function resize() {
    w = canvas.clientWidth || window.innerWidth;
    h = canvas.clientHeight || window.innerHeight;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.round(Math.min(90, Math.max(26, (w * h) / 22000)));
    particles = [];
    for (let i = 0; i < count; i++) particles.push(spawn(true));
  }

  function draw() {
    if (!running) return;
    ctx.clearRect(0, 0, w, h);
    ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      p.drift += p.driftSpeed;
      p.twinkle += p.twinkleSpeed;
      p.x += p.vx + Math.sin(p.drift) * 0.22;
      p.y += p.vy;
      if (p.y < -12 || p.x < -20 || p.x > w + 20) { particles[i] = spawn(false); continue; }
      const alpha = p.baseAlpha * (0.6 + 0.4 * Math.sin(p.twinkle));
      const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 4);
      grad.addColorStop(0, 'rgba(255, 226, 170, ' + alpha + ')');
      grad.addColorStop(0.45, 'rgba(242, 174, 99, ' + (alpha * 0.45) + ')');
      grad.addColorStop(1, 'rgba(242, 174, 99, 0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 4, 0, Math.PI * 2);
      ctx.fill();
    }
    rafId = requestAnimationFrame(draw);
  }

  resize();
  window.addEventListener('resize', resize, { passive: true });
  if (reduce) {
    draw();
    running = false;
  } else {
    rafId = requestAnimationFrame(draw);
  }

  return function stop() {
    running = false;
    window.removeEventListener('resize', resize);
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
  };
}

function finishIntro(intro) {
  introClearTimers();
  if (introStopDust) { introStopDust(); introStopDust = null; }
  try { sessionStorage.setItem(INTRO_SESSION_KEY, '1'); } catch (e) { /* private mode */ }
  intro.classList.add('intro--done');
  document.body.classList.add('intro-complete');
  document.body.classList.remove('intro-active');
  document.body.style.overflow = '';
}

function dismissIntroInstant(intro) {
  introClearTimers();
  if (introStopDust) { introStopDust(); introStopDust = null; }
  intro.style.display = 'none';
  document.body.classList.add('intro-complete');
  document.body.classList.remove('intro-active');
  document.body.style.overflow = '';
}

function initIntro() {
  const body = document.body;
  if (!body) return false;

  // Halaman non-intro (katalog/detail/admin) -> dilewati.
  if (body.classList.contains('no-intro')) {
    body.classList.add('intro-complete');
    return false;
  }

  const intro = document.getElementById('intro');
  if (!intro) {
    // Tidak ada markup intro -> pastikan halaman tetap tampil & bisa di-scroll.
    body.classList.add('intro-complete');
    body.classList.remove('intro-active');
    body.style.overflow = '';
    return false;
  }

  // Sudah pernah dilihat di sesi ini -> langsung sembunyikan.
  let seen = false;
  try { seen = sessionStorage.getItem(INTRO_SESSION_KEY) === '1'; } catch (e) { seen = false; }
  if (seen) { dismissIntroInstant(intro); return false; }

  // Kunci scroll HANYA selama intro berjalan.
  body.classList.add('intro-active');

  // Jaring pengaman: apa pun yang terjadi, intro HARUS hilang setelah 6 detik.
  introWatchdog = setTimeout(() => {
    if (!intro.classList.contains('intro--done')) finishIntro(intro);
  }, 6000);

  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  introStopDust = initIntroDust(document.getElementById('intro-dust'));

  if (reduce) {
    intro.style.transition = 'opacity 400ms ease';
    introTimers.push(setTimeout(() => {
      intro.style.opacity = '0';
      finishIntro(intro);
    }, 400));
    return true;
  }

  // 2.2s: tahan sejenak setelah animasi masuk, lalu mulai transisi keluar.
  introTimers.push(setTimeout(() => intro.classList.add('intro--animating'), 2200));
  // Panel menutup ~1.25s (delay 0.55s + durasi 0.7s) -> sembunyikan setelah 3.55s.
  introTimers.push(setTimeout(() => finishIntro(intro), 3550));

  const skipBtn = document.getElementById('intro-skip');
  if (skipBtn) {
    skipBtn.addEventListener('click', () => {
      introClearTimers();
      if (introStopDust) { introStopDust(); introStopDust = null; }
      intro.classList.add('intro--skipping');
      // Tetap pasang jaring pengaman untuk jalur skip.
      introWatchdog = setTimeout(() => {
        if (!intro.classList.contains('intro--done')) finishIntro(intro);
      }, 1500);
      introTimers.push(setTimeout(() => finishIntro(intro), 500));
    });
  }

  return true;
}

/* ===============================================================
   NAVBAR
   =============================================================== */
function initNavbar() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;
  const isHeroPage = !document.body.classList.contains('no-intro');
  function updateNavbar() {
    if (isHeroPage) navbar.classList.toggle('scrolled', window.scrollY > 60);
  }
  window.addEventListener('scroll', updateNavbar, { passive: true });
  updateNavbar();
}

/* ===============================================================
   MOBILE MENU
   =============================================================== */
function initMobileMenu() {
  const toggle = document.getElementById('menu-toggle');
  const menu   = document.getElementById('mobile-menu');
  if (!toggle || !menu) return;

  toggle.addEventListener('click', () => {
    const isOpen = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!isOpen));
    menu.hidden = isOpen;
    if (!isOpen) {
      const firstLink = menu.querySelector('a');
      if (firstLink) firstLink.focus();
    }
  });

  document.addEventListener('click', (e) => {
    if (!toggle.contains(e.target) && !menu.contains(e.target)) {
      menu.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      menu.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
      toggle.focus();
    }
  });
}

/* ===============================================================
   FLOATING WHATSAPP BUTTON
   =============================================================== */
function initFAB() {
  const fab = document.getElementById('fab-whatsapp');
  if (!fab) return;
  const isHeroPage = !document.body.classList.contains('no-intro');
  function updateFAB() {
    const threshold = isHeroPage ? window.innerHeight * 0.8 : 100;
    fab.classList.toggle('fab--visible', window.scrollY > threshold);
  }
  window.addEventListener('scroll', updateFAB, { passive: true });
  if (!isHeroPage) setTimeout(() => fab.classList.add('fab--visible'), 300);
}

/* ===============================================================
   PARALLAX EFFECTS
   =============================================================== */
function initParallaxEffects() {
  const items = document.querySelectorAll('[data-parallax]');
  if (!items.length) return;

  items.forEach((item) => {
    const depth = Number(item.dataset.depth || 12);
    const media = item.querySelector('img');

    const reset = () => {
      item.style.transform = 'perspective(1200px) rotateX(0deg) rotateY(0deg) translateY(0px)';
      if (media) media.style.transform = 'scale(1.02) translate3d(0, 0, 0)';
    };

    item.addEventListener('pointermove', (event) => {
      const rect = item.getBoundingClientRect();
      const px = (event.clientX - rect.left) / rect.width - 0.5;
      const py = (event.clientY - rect.top) / rect.height - 0.5;
      const rotateY = px * depth * 1.8;
      const rotateX = -py * depth * 1.8;
      const moveX = px * depth * 2;
      const moveY = py * depth * 2;
      item.style.transform = `perspective(1200px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
      if (media) media.style.transform = `scale(1.08) translate3d(${moveX}px, ${moveY}px, 0)`;
    });

    item.addEventListener('pointerleave', reset);
    item.addEventListener('pointercancel', reset);
    reset();
  });
}

function initFeaturedGrid() {
  syncProductCounts();
  const grid = document.getElementById('featured-grid');
  if (!grid) return;

  // ✅ WAJIB: kosongkan dulu (hapus "Memuat produk...")
  grid.innerHTML = '';

  const products = getProducts();
  const featured = products.slice(0, 6);

  if (featured.length === 0) {
    grid.innerHTML = '<p class="empty-state">Belum ada produk. <a href="admin.html">Tambah via panel admin.</a></p>';
    return;
  }

  const fragment = document.createDocumentFragment();
  featured.forEach(p => fragment.appendChild(createProductCard(p)));
  grid.appendChild(fragment);
}
/* ===============================================================
   CATALOG PAGE (katalog.html)
   =============================================================== */
let currentFilter      = 'semua';
let currentPriceFilter = 'all';
let currentSort        = 'newest';
let currentStatus      = 'aktif';
let visibleCount       = 12;
let PAGE_SIZE          = 12;

function filteredAndSorted() {
  let list = getProducts();

  if (currentStatus !== 'semua') {
    list = list.filter(p => (p.status || 'aktif') === currentStatus);
  }

  if (currentFilter !== 'semua') {
    list = list.filter(p => p.category === currentFilter);
  }

  if (currentPriceFilter !== 'all') {
    if (currentPriceFilter === '0-2000000') list = list.filter(p => p.price < 2000000);
    else if (currentPriceFilter === '2000000-5000000') list = list.filter(p => p.price >= 2000000 && p.price <= 5000000);
    else if (currentPriceFilter === '5000000-10000000') list = list.filter(p => p.price > 5000000 && p.price <= 10000000);
    else if (currentPriceFilter === '10000000+') list = list.filter(p => p.price > 10000000);
  }

  switch (currentSort) {
    case 'price-asc':  list.sort((a, b) => a.price - b.price); break;
    case 'price-desc': list.sort((a, b) => b.price - a.price); break;
    case 'name':       list.sort((a, b) => a.name.localeCompare(b.name, 'id')); break;
    case 'stock':      list.sort((a, b) => (b.stock || 0) - (a.stock || 0)); break;
  }
  return list;
}

function renderCatalogGrid() {
  const grid = document.getElementById('catalog-grid');
  if (!grid) return;

  const list    = filteredAndSorted();
  const visible = list.slice(0, visibleCount);

  grid.style.opacity = '0';
  grid.style.transition = 'opacity 180ms ease';

  setTimeout(() => {
    grid.innerHTML = '';
    if (visible.length === 0) {
      grid.innerHTML = '<p class="empty-state">Tidak ada produk di kategori ini.</p>';
    } else {
      const fragment = document.createDocumentFragment();
      visible.forEach(p => fragment.appendChild(createProductCard(p)));
      grid.appendChild(fragment);
    }
    grid.style.opacity = '1';
  }, 160);

  const countEl = document.getElementById('catalog-count');
  if (countEl) {
    countEl.innerHTML = `Menampilkan <strong>${Math.min(visibleCount, list.length)}</strong> dari <strong>${list.length}</strong> produk`;
  }

  const loadMoreBtn = document.getElementById('load-more-btn');
  if (loadMoreBtn) {
    loadMoreBtn.style.display = visibleCount < list.length ? '' : 'none';
  }
}

function setFilter(value) {
  currentFilter = value;
  visibleCount  = PAGE_SIZE;
  document.querySelectorAll('.pill[data-filter]').forEach(p => p.classList.toggle('active', p.dataset.filter === value));
  document.querySelectorAll('.sidebar-filter-btn[data-filter]').forEach(b => b.classList.toggle('active', b.dataset.filter === value));
  renderCatalogGrid();
}

function initCatalogPage() {
  const grid = document.getElementById('catalog-grid');
  if (!grid) return;

  const params   = new URLSearchParams(window.location.search);
  const katParam = params.get('kategori');
  if (katParam) currentFilter = katParam;

  const perPageSel = document.getElementById('per-page-select');
  if (perPageSel) {
    PAGE_SIZE = parseInt(perPageSel.value, 10) || 12;
    visibleCount = PAGE_SIZE;
    perPageSel.addEventListener('change', () => {
      PAGE_SIZE = parseInt(perPageSel.value, 10) || 12;
      visibleCount = PAGE_SIZE;
      renderCatalogGrid();
    });
  }

  function updateSidebarCounts() {
    const products = getProducts().filter(p => (p.status || 'aktif') === 'aktif');
    const countSemua = document.querySelector('.sidebar-filter-btn[data-filter="semua"] .filter-count');
    if (countSemua) countSemua.textContent = products.length;
    ['kursi', 'meja', 'sofa', 'lemari'].forEach(cat => {
      const el = document.querySelector(`.sidebar-filter-btn[data-filter="${cat}"] .filter-count`);
      if (el) el.textContent = products.filter(p => p.category === cat).length;
    });
  }

  updateSidebarCounts();
  syncProductCounts();
  renderCatalogGrid();

  document.querySelectorAll('.status-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.status-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentStatus = pill.dataset.status;
      visibleCount = PAGE_SIZE;
      renderCatalogGrid();
    });
  });

  document.querySelectorAll('.pill[data-filter]').forEach(pill => {
    pill.addEventListener('click', () => setFilter(pill.dataset.filter));
  });
  document.querySelectorAll('.sidebar-filter-btn[data-filter]').forEach(btn => {
    btn.addEventListener('click', () => setFilter(btn.dataset.filter));
  });
  document.querySelectorAll('.sidebar-filter-btn[data-price]').forEach(btn => {
    btn.addEventListener('click', () => {
      const priceVal = btn.dataset.price;
      if (currentPriceFilter === priceVal) {
        currentPriceFilter = 'all';
        btn.classList.remove('active');
      } else {
        document.querySelectorAll('.sidebar-filter-btn[data-price]').forEach(b => b.classList.remove('active'));
        currentPriceFilter = priceVal;
        btn.classList.add('active');
      }
      visibleCount = PAGE_SIZE;
      renderCatalogGrid();
    });
  });

  const sortSelect = document.getElementById('sort-select');
  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      currentSort  = sortSelect.value;
      visibleCount = PAGE_SIZE;
      renderCatalogGrid();
    });
  }

  const loadMoreBtn = document.getElementById('load-more-btn');
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener('click', () => {
      visibleCount += PAGE_SIZE;
      renderCatalogGrid();
    });
  }
}

/* ===============================================================
   PRODUCT DETAIL PAGE (detail.html)
   =============================================================== */
function initDetailPage() {
  const galleryMain = document.getElementById('gallery-main-img');
  if (!galleryMain) return;

  const params   = new URLSearchParams(window.location.search);
  const skuParam = (params.get('sku') || '').trim().toUpperCase();
  const id       = parseInt(params.get('id'), 10);
  const products = getProducts();
  const product  =
    (skuParam ? products.find(p => (p.sku || '').toUpperCase() === skuParam) : null) ||
    (id ? products.find(p => p.id === id) : null) ||
    products[0];

  if (!product) {
    const main = document.querySelector('.product-detail');
    if (main) main.innerHTML = '<div class="container"><p class="empty-state">Produk tidak ditemukan. <a href="katalog.html">Kembali ke katalog</a></p></div>';
    return;
  }

  if (product) {
    document.title = `${product.name} - Ine Mebel Jepara`;

    // Statistik: catat produk yang dilihat + halaman detail ini.
    trackProductView(product.id);
    trackPageView('detail');

    const crumb = document.getElementById('breadcrumb-product');
    if (crumb) crumb.textContent = product.name;

    galleryMain.src = product.img;
    galleryMain.alt = product.imgAlt || product.name;

    const catEl = document.querySelector('.product-info__category');
    if (catEl) catEl.textContent = product.category.charAt(0).toUpperCase() + product.category.slice(1);

    const nameEl = document.getElementById('product-name');
    if (nameEl) nameEl.textContent = product.name;

    const priceEl = document.querySelector('.price-main');
    if (priceEl) {
      if (product.discountPrice && product.discountPrice < product.price) {
        priceEl.innerHTML = `${formatRupiah(product.discountPrice)} <span style="text-decoration:line-through;color:var(--text-muted);font-size:0.7em;margin-left:0.5rem;">${formatRupiah(product.price)}</span>`;
      } else {
        priceEl.textContent = formatRupiah(product.price);
      }
    }

    const codeEl = document.getElementById('product-code');
    if (codeEl && product.sku) codeEl.textContent = `#${product.sku}`;

    const descEl = document.querySelector('.product-info__desc');
    if (descEl) descEl.textContent = product.desc;

    const materialEl = document.getElementById('spec-material');
    if (materialEl) materialEl.textContent = product.material || '-';

    const dimensiEl = document.getElementById('spec-dimensi');
    if (dimensiEl) {
      const p = product.dimensiPanjang || 0;
      const l = product.dimensiLebar || 0;
      const t = product.dimensiTinggi || 0;
      dimensiEl.textContent = (p || l || t) ? `P ${p} x L ${l} x T ${t} cm` : '-';
    }

    const beratEl = document.getElementById('spec-berat');
    if (beratEl) beratEl.textContent = product.berat ? `${product.berat} kg` : '-';

    const finishingEl = document.getElementById('spec-finishing');
    if (finishingEl) finishingEl.textContent = product.finishing || '-';

    const garansiEl = document.getElementById('spec-garansi');
    if (garansiEl) garansiEl.textContent = product.garansi || '-';

    const variantsContainer = document.getElementById('product-variants-container');
    const thumbsContainer = document.getElementById('product-thumbs-container');
    if (product.warna) {
      if (variantsContainer) variantsContainer.style.display = '';
    } else {
      if (variantsContainer) variantsContainer.style.display = 'none';
    }

    const consultLink = document.querySelector('.consult-cta a');
    if (consultLink) {
      const msg = encodeURIComponent(`Halo, saya tertarik dengan ${product.name}. Bisa minta info lebih lanjut?`);
      consultLink.href = `https://wa.me/6283114241995?text=${msg}`;
    }

    const relatedGrid = document.getElementById('related-grid');
    if (relatedGrid) {
      const related = products.filter(p => p.category === product.category && p.id !== product.id).slice(0, 3);
      if (related.length) {
        relatedGrid.innerHTML = '';
        const fragment = document.createDocumentFragment();
        related.forEach(p => fragment.appendChild(createProductCard(p)));
        relatedGrid.appendChild(fragment);
      } else {
        relatedGrid.innerHTML = '<p class="empty-state">Tidak ada produk terkait lainnya.</p>';
      }
    }

    // Muat ulasan produk ini dari API.
    loadProductReviews(product);
  }

  const thumbBtns = document.querySelectorAll('.thumb-btn');
  thumbBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const src = btn.querySelector('img')?.src;
      if (!src) return;
      thumbBtns.forEach(b => { b.classList.remove('active'); b.setAttribute('aria-pressed', 'false'); });
      btn.classList.add('active');
      btn.setAttribute('aria-pressed', 'true');
      galleryMain.style.opacity = '0';
      galleryMain.style.transition = 'opacity 180ms ease';
      setTimeout(() => { galleryMain.src = src; galleryMain.style.opacity = '1'; }, 160);
    });
  });

  const swatches = document.querySelectorAll('.color-swatch');
  function selectColor(colorName) {
    swatches.forEach(s => {
      const active = s.dataset.color === colorName;
      s.classList.toggle('active', active);
      s.setAttribute('aria-pressed', String(active));
    });
    const selectedText = document.getElementById('variants-selected-text');
    if (selectedText) selectedText.innerHTML = `Warna terpilih: <strong>${escapeHTML(colorName)}</strong>`;
  }
  swatches.forEach(s => s.addEventListener('click', () => selectColor(s.dataset.color)));

  const wishlistBtn = document.querySelector('.wishlist-btn');
  if (wishlistBtn && product) {
    wishlistBtn.dataset.productId = String(product.id);
    syncWishlistBtnState(wishlistBtn, product.id);
    wishlistBtn.addEventListener('click', () => {
      toggleWishlist(product.id);
      syncWishlistBtnState(wishlistBtn, product.id);
    });
  }
}

/* ===============================================================
   ULASAN PRODUK (detail.html) - diambil dari API /api/reviews
   =============================================================== */
function renderStars(rating) {
  const full = Math.round(Number(rating) || 0);
  return '★★★★★'.slice(0, full) + '☆☆☆☆☆'.slice(0, 5 - full);
}

function formatReviewDate(value) {
  if (!value) return '';
  const d = new Date(String(value).replace(' ', 'T'));
  if (isNaN(d.getTime())) return '';
  try {
    return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' });
  } catch { return ''; }
}

async function loadProductReviews(product) {
  const listWrap = document.getElementById('reviews-list');
  const scoreEl  = document.querySelector('.rating-score');
  const countEl  = document.querySelector('.rating-count');
  const starsEl  = document.querySelector('.product-info__rating .stars');

  if (!listWrap && !scoreEl) return;

  let data = null;
  try {
    const res = await fetch(`${API_BASE}/reviews?product_id=${encodeURIComponent(product.id)}`, {
      headers: { Accept: 'application/json' },
    });
    data = await res.json();
  } catch (err) {
    console.error('Gagal memuat ulasan:', err);
  }

  const reviews = (data && data.success && Array.isArray(data.reviews)) ? data.reviews : [];
  const count   = data && data.success ? Number(data.count || 0) : 0;
  const average = data && data.success ? Number(data.average || 0) : 0;

  if (scoreEl) scoreEl.textContent = average ? average.toFixed(1) : '—';
  if (countEl) countEl.textContent = `(${count} ulasan)`;
  if (starsEl) starsEl.textContent = renderStars(average);

  if (!listWrap) return;

  if (!reviews.length) {
    listWrap.innerHTML = '<p class="empty-state">Belum ada ulasan untuk produk ini.</p>';
    return;
  }

  listWrap.innerHTML = reviews.map((r) => `
    <article class="review-item">
      <header class="review-item__head">
        <span class="review-item__avatar" aria-hidden="true">${escapeHTML((r.name || '?').charAt(0).toUpperCase())}</span>
        <div>
          <strong class="review-item__name">${escapeHTML(r.name)}</strong>
          <span class="review-item__stars" aria-label="Rating ${r.rating} dari 5">${renderStars(r.rating)}</span>
        </div>
        <time class="review-item__date">${escapeHTML(formatReviewDate(r.createdAt))}</time>
      </header>
      <p class="review-item__text">${escapeHTML(r.comment)}</p>
    </article>
  `).join('');
}

/* ===============================================================
   INIT
   =============================================================== */
document.addEventListener('DOMContentLoaded', async () => {
  // 1. Init UI non-data dulu (navbar, menu, dll) — tanpa intro
  initNavbar();
  initMobileMenu();
  initWishlistPanel();
  initFAB();
  initParallaxEffects();

  // 2. Tampilkan loading state pada grid yang ada
  const featuredGrid = document.getElementById('featured-grid');
  const catalogGrid  = document.getElementById('catalog-grid');
  if (featuredGrid) featuredGrid.innerHTML = '<p class="empty-state">Memuat produk...</p>';
  if (catalogGrid)  catalogGrid.innerHTML  = '<p class="empty-state">Memuat produk...</p>';

  // 3. Muat data produk DULU (await), baru render
  trackPageView(document.body.dataset.page || 'site');
  try {
    await loadProducts(true);
  } catch (err) {
    console.error('Gagal memuat produk:', err);
  }

  // 4. Baru render grid setelah data siap
  initFeaturedGrid();
  initCatalogPage();
  initDetailPage();
});