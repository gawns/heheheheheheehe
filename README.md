# Ine Mebel Jepara

Website katalog mebel (Flask + MySQL/Laragon) dengan panel admin.

## Menjalankan

```bash
python db-init.py     # sekali saja: buat database + 12 produk awal
python app.py         # http://127.0.0.1:5000/
```

## Halaman

| Halaman | URL | Keterangan |
|---|---|---|
| Beranda | `/index.html` | Hero, kategori, produk pilihan |
| Katalog | `/katalog.html` | Filter, sortir, load more, wishlist |
| Detail produk | `/detail.html?sku=IMJ-0001` | **Path berbasis SKU** (fallback `?id=1` masih didukung). Halaman berupa **template** — diisi JS setelah data produk siap. |
| 404 | `/404.html` | Halaman tidak ditemukan (link rusak / SKU tidak ada) |
| Panel admin - Produk | `/admin.html` | CRUD produk |
| Panel admin - Statistik | `/admin-stats.html` | **Halaman terpisah**: kunjungan, terpopuler, tren favorit |
| Panel admin - Ulasan | `/admin-ulasan.html` | **Tambah/hapus ulasan** produk |

Panel admin memakai login (tabel `admin_users`). Default: `admin` / `2026`
(ubah lewat `db.set_admin_password(...)`).

## API

| Method | Endpoint | Keterangan |
|---|---|---|
| GET | `/api/products` | Daftar produk aktif |
| GET | `/api/products?sku=IMJ-0001` | Satu produk via **SKU** (dipakai detail.html) |
| GET | `/api/products?id=1` | Satu produk via ID |
| GET | `/api/products?include_all=1` | Semua produk (admin) |
| POST/PUT/DELETE | `/api/products` | CRUD produk. **SKU terkunci** - PUT selalu memakai SKU lama |
| GET | `/api/reviews?sku=IMJ-0001` | Ulasan satu produk + rata-rata rating (publik) |
| GET | `/api/reviews/all` | Semua ulasan (admin) |
| POST | `/api/reviews` | Tambah ulasan (admin) |
| DELETE | `/api/reviews?id=1` | Hapus ulasan (admin) |
| GET | `/api/admin/stats?days=7` | Statistik analitik (admin) |
| POST | `/api/login` | Login admin, mengembalikan token |

## Catatan penting

- **SKU terkunci**: field SKU di form admin `readonly`, dan server menimpa SKU
  dengan nilai lama saat PUT. Ini menjaga URL `detail.html?sku=...` tetap stabil.
- **Foto produk**: semua memakai gambar milik sendiri di folder `img/` (tidak ada
  lagi tautan Unsplash). Jalankan `python fix-images.py` untuk merapikan data lama.
- **Halaman detail (template)**: `detail.html` hanya berisi kerangka (skeleton) +
  status "Memuat produk...". Galeri & thumbnail **di-generate dari data produk**
  oleh `script.js` (`renderDetailGallery`), jadi tidak ada daftar gambar yang
  di-hardcode. Halaman ini tidak menampilkan rating dan tidak ada swatch varian
  warna (daftar varian cukup lewat baris spesifikasi "Pilihan Warna").
- **CTA penutup** (`index.html`): section `cta-section` kini full-bleed satu layar
  (foto latar penuh + overlay gelap, teks & tombol terpusat).
- **404**: kalau SKU/ID tidak ditemukan, `script.js` mengalihkan ke `/404.html`.
  URL yang benar-benar tidak ada juga dilayani `404.html` (via `app.errorhandler(404)`);
  khusus path `/api/*` tetap mengembalikan JSON.
- **Wishlist**: tersimpan per-device di `localStorage`. Menghapus item dari panel
  wishlist navbar otomatis mengembalikan ikon hati di katalog/detail ke bentuk awal.
- **Ulasan**: tabel `reviews` dibuat otomatis (lihat `db.ensure_reviews_table()`).

## Alamat showroom

RT.27/RW.06, Bawu III, Bawu, Kec. Batealit, Kabupaten Jepara, Jawa Tengah 59461
