# Panduan Lengkap Deploy — Ine Mebel Jepara (Railway)

Dokumen ini merangkum **semua** yang perlu Anda ketahui: URL, login, di mana
password MySQL berada, penyebab error login, dan langkah perbaikannya.
Simpan file ini. Jangan pernah commit password asli ke Git.

---

## 1. Alamat situs (Production)

| Halaman | URL |
| --- | --- |
| Beranda | https://heheheheheheehe-production.up.railway.app/ |
| Katalog | https://heheheheheheehe-production.up.railway.app/katalog.html |
| Detail produk | https://heheheheheheehe-production.up.railway.app/detail.html?sku=IMJ-0001 |
| Panel admin (login) | https://heheheheheheehe-production.up.railway.app/admin.html |
| Statistik | https://heheheheheheehe-production.up.railway.app/admin-stats.html |
| Ulasan | https://heheheheheheehe-production.up.railway.app/admin-ulasan.html |
| Health check | https://heheheheheheehe-production.up.railway.app/api/health |

Nama service di dashboard Railway: **heheheheheheehe**
(project: bebas, service: `heheheheheheehe`, plus service MySQL terpisah).

---

## 2. Password & rahasia: ADA DI MANA

### 2a. Password admin panel (untuk login di admin.html)

- **Bukan** di file. Tersimpan sebagai **hash PBKDF2** di tabel `admin_users`
  kolom `password_hash` (lihat `db.py:687-710`).
- Nilai yang berlaku saat ini kemungkinan besar masih password **lama**,
  karena penyemaian otomatis hanya jalan sekali saat tabel masih kosong.
- Password yang Anda inginkan: lihat env `DEFAULT_ADMIN_PASS` di
  **Railway → service aplikasi → Variables**.
- Untuk melihat password di database: tidak bisa (hash satu arah).
  Harus di-**ganti**, bukan dibaca.

### 2b. Password MySQL Railway

Jangan diketik manual. Railway mengisinya otomatis sebagai env di service
**MySQL** (bukan di service aplikasi):

| Env (service MySQL) | Isi |
| --- | --- |
| `MYSQLHOST` | host database |
| `MYSQLPORT` | port, biasanya 3306 |
| `MYSQLUSER` | user, biasanya `root` |
| `MYSQLPASSWORD` | **password MySQL** — ada di sini |
| `MYSQLDATABASE` | nama database, biasanya `railway` |
| `MYSQL_URL` / `DATABASE_URL` | versi URL lengkap |

Cara melihatnya: **Railway → klik service MySQL → tab Variables**
(atau **Settings → Variables**). Di service **aplikasi**, nilainya biasanya
muncul lewat **reference variable** yang mengarah ke service MySQL.

`config.py:43-52` membaca env ini dengan urutan prioritas:
`MYSQLHOST`/`MYSQLPORT`/`MYSQLUSER`/`MYSQLPASSWORD`/`MYSQLDATABASE`
→ lalu `DATABASE_URL`/`MYSQL_URL` → terakhir default Laragon (`127.0.0.1`).

### 2c. Rahasia lain (semua di Railway → service aplikasi → Variables)

| Env | Fungsi | Cara membuat |
| --- | --- | --- |
| `AUTH_SECRET` | tanda tangan token admin | `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `AUTH_ENABLED` | `1` = admin wajib login | sudah diisi `1` |
| `APP_DEBUG` | harus `0` di produksi | sudah diisi `0` |
| `DEFAULT_ADMIN_USER` | username admin | `admin` |
| `DEFAULT_ADMIN_PASS` | password admin (dipakai saat seed) | password kuat pilihan Anda |
| `TOKEN_TTL` | masa berlaku token (detik) | `28800` = 8 jam |
| `UPLOAD_DIR` | folder simpan foto | `img` |
| `UPLOAD_URL` | prefix URL foto | `img` |
| `MAX_UPLOAD_MB` | batas ukuran upload | `5` |

---

## 3. Soal error: "Username atau password salah"

### Penyebab pasti

`db.py:703-708` menyemai admin **hanya bila tabel `admin_users` kosong**:

```python
cur.execute(f"SELECT COUNT(*) AS n FROM {ADMIN_TABLE}")
if int((cur.fetchone() or {}).get("n") or 0) == 0:
    cur.execute(..., (DEFAULT_ADMIN_USER, _hash_password(DEFAULT_ADMIN_PASS)))
```

Deploy pertama mengisi tabel dengan password yang berlaku **saat itu**.
Setelah Anda ganti `DEFAULT_ADMIN_PASS`, baris tidak ikut berubah karena
tabel sudah tidak kosong. Jadi password baru tidak pernah masuk database.

### Kenapa perlu diedit lewat skrip, bukan dashboard

Hash tidak bisa dibaca/ditulis manual dari dashboard Railway. Harus lewat
fungsi `db.set_admin_password()` (`db.py:734-745`) yang melakukan `UPDATE`.

### Cara perbaikan yang BENAR (jalankan di dalam Railway)

**Penting:** host `mysql.railway.internal` **hanya bisa diakses dari dalam
jaringan Railway**. Menjalankannya dari komputer Anda akan selalu gagal
dengan:

```
socket.gaierror: [Errno 11001] getaddrinfo failed
Target: mysql.railway.internal:3306
```

Itu bukan salah perintah, itu memang batasan jaringan privat.

#### Langkah resmi (lewat Railway Console)

1. Buka https://railway.app → proyek Anda.
2. Klik **service aplikasi** (`heheheheheheehe`).
3. Buka tab **Console** (ikon terminal `>_`).
4. Cek dulu database mana yang tersambung:

```bash
python -c "import config; print(config.DB_HOST, config.DB_PORT, config.DB_NAME)"
```

5. Setelah cocok (harus `mysql.railway.internal 3306 ...`), ganti password:

```bash
python -c "import db; db.set_admin_password('admin', 'MebelJepara#2026!xY7'); print('OK')"
```

6. Kalau muncul `OK`, login di `/admin.html` dengan:
   **user:** `admin` — **pass:** `MebelJepara#2026!xY7`

#### Alternatif bila Console tidak tersedia

Buka **Public Networking** pada service MySQL (Railway → service MySQL →
Settings → Networking → Public Networking), lalu jalankan dari komputer
dengan env diisi manual:

```powershell
$env:MYSQLHOST="<host-publik>"
$env:MYSQLPORT="<port-publik>"
$env:MYSQLUSER="root"
$env:MYSQLPASSWORD="<password dari Variables>"
$env:MYSQLDATABASE="railway"
python -c "import db; db.set_admin_password('admin', 'MebelJepara#2026!xY7'); print('OK')"
```

Setelah selesai, sebaiknya Public Networking dimatikan lagi.

---

## 4. Perintah yang sering dipakai

| Tujuan | Perintah | Dijalankan di |
| --- | --- | --- |
| Cek DB lokal | `python check.db.py` | terminal PC |
| Isi DB lokal | `python db-init.py` | terminal PC |
| Perbaiki path gambar | `python fix-images.py` | terminal PC |
| Jalankan lokal | `python app.py` | terminal PC |
| Ganti password admin (Railway) | `python -c "import db; db.set_admin_password(...)"` | **Railway Console** |
| Ambil env Railway ke lokal | `railway run python ...` | terminal PC (tetap gagal untuk DB internal) |

Catatan: `railway run` berguna untuk env yang bisa diakses publik, tapi
**tidak bisa** menembus `mysql.railway.internal`.

---

## 5. Masalah yang MASIH harus diperbaiki

### 5a. Foto upload hilang setiap redeploy (WAJIB)

`app.py:31` menyimpan ke `img/` di filesystem container yang **sementara**.
Setiap redeploy/restart, semua foto yang diunggah **hilang**.

**Perbaikan:** pasang Railway **Volume**:

1. Railway → service aplikasi → **Volumes** → **New Volume**.
2. Mount path: `/app/img` (sesuaikan dengan path container Anda —
   cek log deploy untuk memastikan, biasanya `/app`).
3. Redeploy.

Kalau setelah mount gambar justru tidak muncul, berarti mount path salah;
cocokkan dengan `gunicorn app:app` yang dijalankan dari root repo.

### 5b. Error tertelan tanpa log (disarankan)

- `db.py:709` — `except Exception: pass` pada penyemaian admin.
- `db.py:727` — `except Exception: return False` pada cek login.

Akibatnya kegagalan koneksi/query terlihat sama seperti "password salah".
Disarankan menambahkan `print()` pada kedua blok agar penyebab asli terlihat
di log Railway.

---

## 6. Konfigurasi deploy saat ini

**railway.json**

```json
{
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60",
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 60,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

- `requirements.txt`: Flask>=3.0, PyMySQL>=1.1, gunicorn>=21.2
- `runtime.txt`: python-3.12
- Port: dari env `PORT` (Railway mengisinya otomatis)
- Health check: `/api/health` → `status: ok` bila DB & config sehat.

Arti status health:

| Field | Arti |
| --- | --- |
| `database: error` | koneksi MySQL gagal → cek `error` di respons |
| `config: incomplete` | ada env keamanan belum diisi → lihat `config_problems` |
| `status: degraded` | salah satu di atas bermasalah (HTTP tetap 200 bila DB jalan) |

---

## 7. Catatan keamanan

- Jangan commit file `.env` (sudah masuk `.gitignore`). Belum ada `.env`
  di repo ini — bagus.
- `AUTH_SECRET` default `ubah-secret-ini-di-hosting` akan membuat admin
  panel **diblokir** di produksi (lihat `app.py:221`). Pastikan sudah diganti.
- Setelah semuanya berjalan, pertimbangkan mengganti password admin dari
  nilai yang beredar di chat ini.

