"""
Ine Mebel Jepara - Aplikasi Flask + Laragon
============================================
Menyajikan halaman statis (HTML/CSS/JS) sekaligus REST API produk.

Cara menjalankan:
    python app.py
lalu buka  http://127.0.0.1:5000/

Endpoint API (JSON):
    GET    /api/products           -> daftar produk (default: hanya status='aktif')
    GET    /api/products?id=3      -> satu produk
    GET    /api/products?include_all=1  -> semua produk (untuk admin)
    POST   /api/products           -> tambah produk
    PUT    /api/products?id=3      -> ubah produk
    DELETE /api/products?id=3      -> hapus produk
"""

import os
import re
import sys
import time

from flask import Flask, jsonify, request, send_from_directory, abort
from werkzeug.utils import secure_filename

import config
import db
from db import DbError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, getattr(config, "UPLOAD_DIR", "img"))
UPLOAD_URL_PREFIX = getattr(config, "UPLOAD_URL", "img").strip("/")
MAX_UPLOAD_BYTES = int(getattr(config, "MAX_UPLOAD_MB", 5)) * 1024 * 1024
ALLOWED_IMAGE_EXTS = tuple(getattr(config, "ALLOWED_IMAGE_EXTS", (".jpg", ".jpeg", ".png", ".webp", ".gif")))

# Versi commit yang sedang berjalan - dipakai /api/health & /api/live agar
# verifikasi "deploy sudah ter-update?" cukup dari browser, tanpa baca dashboard.
# Railway mengisi RAILWAY_GIT_COMMIT_SHA saat deploy dari GitHub.
COMMIT_SHA = (
    os.getenv("RAILWAY_GIT_COMMIT_SHA")
    or os.getenv("GIT_COMMIT")
    or os.getenv("SOURCE_VERSION")
    or "unknown"
)[:12]

app = Flask(__name__, static_folder=None)
app.config["JSON_SORT_KEYS"] = False
# Tidak memasang MAX_CONTENT_LENGTH: validasi ukuran dilakukan di
# save_uploaded_image() supaya pesan error selalu berupa JSON (bukan halaman HTML 413).


# ---------------------------------------------------------------------
#  UTIL
# ---------------------------------------------------------------------
def json_error(message, status, **extra):
    payload = {"success": False, "message": message}
    payload.update(extra)
    return jsonify(payload), status


def _log_exc(prefix, exc):
    """Cetak pesan error + traceback penuh ke stderr.

    Dipakai agar penyebab crash/gagal koneksi DB terlihat di log deploy,
    bukan tertelan diam-diam (mis. di blok `except Exception: pass`).
    """
    import traceback

    print(f"{prefix}: {exc}", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()


def _file_ext(filename):
    return os.path.splitext(filename or "")[1].lower()


def save_uploaded_image(file_storage):
    """Simpan file gambar yang diunggah ke folder img/ (lokal).

    Mengembalikan (relative_path, error_message).
    - Validasi ekstensi & ukuran
    - Sanitasi nama file + suffix unik agar tidak bentrok
    - Path yang dikembalikan: "img/<nama-file>.<ext>" (siap dipakai <img src>)
    """
    if file_storage is None or not getattr(file_storage, "filename", ""):
        return None, "Tidak ada file yang diunggah."

    original = file_storage.filename
    ext = _file_ext(original)
    if ext not in ALLOWED_IMAGE_EXTS:
        allowed = ", ".join(ALLOWED_IMAGE_EXTS)
        return None, f"Format file tidak didukung (boleh: {allowed})."

    # Nama dasar yang aman: tanpa ekstensi, tanpa karakter aneh.
    base = os.path.splitext(secure_filename(original))[0]
    base = re.sub(r"[^A-Za-z0-9_-]+", "-", base).strip("-_").lower()
    if not base:
        base = "produk"

    # Cek ukuran (bila diketahui) sebelum menulis ke disk.
    stream = file_storage.stream
    try:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(0)
    except Exception:
        size = None
    if size is not None and size > MAX_UPLOAD_BYTES:
        return None, f"Ukuran file melebihi batas {getattr(config, 'MAX_UPLOAD_MB', 5)} MB."

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    filename = f"{base}{ext}"
    target = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(target):
        filename = f"{base}-{int(time.time())}{ext}"
        target = os.path.join(UPLOAD_DIR, filename)

    file_storage.save(target)

    # Verifikasi akhir ukuran setelah tersimpan.
    if os.path.getsize(target) > MAX_UPLOAD_BYTES:
        try:
            os.remove(target)
        except OSError:
            pass
        return None, f"Ukuran file melebihi batas {getattr(config, 'MAX_UPLOAD_MB', 5)} MB."

    rel = f"{UPLOAD_URL_PREFIX}/{filename}" if UPLOAD_URL_PREFIX else filename
    return rel.replace(os.sep, "/"), None


def make_request_payload():
    """Ambil payload produk dari JSON ATAU multipart/form-data.

    Saat multipart, file bernama `img`/`image`/`foto` -> foto utama, dan
    file berulang `images[]` -> galeri. Semua disimpan ke img/ lalu
    path-nya disisipkan ke payload.
    """
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        body = {k: v for k, v in request.form.items()}
        errors = []

        # Array sederhana dari form (mis. tags yang dikirim berulang).
        multi_tags = request.form.getlist("tags[]")
        if multi_tags:
            body["tags"] = multi_tags

        # Foto utama: field file bernama "img" (atau "image"/"foto").
        main_file = (
            request.files.get("img")
            or request.files.get("image")
            or request.files.get("foto")
        )
        if main_file and main_file.filename:
            rel, err = save_uploaded_image(main_file)
            if err:
                errors.append(err)
            else:
                body["img"] = rel

        # Foto tambahan: field file "images[]" (bisa banyak).
        extra_imgs = []
        for key in ("images[]", "images", "gallery"):
            for f in request.files.getlist(key):
                if f and f.filename:
                    rel, err = save_uploaded_image(f)
                    if err:
                        errors.append(err)
                    else:
                        extra_imgs.append(rel)
        if extra_imgs:
            body["images"] = extra_imgs
        elif isinstance(body.get("images"), str) and body["images"].strip():
            body["images"] = [s.strip() for s in body["images"].split(",") if s.strip()]

        return body, errors

    return request.get_json(silent=True) or {}, []


def request_token():
    token = request.headers.get("X-Admin-Token")
    if token:
        return token.strip()
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


# Daftar masalah konfigurasi keamanan yang terdeteksi saat startup.
# Bila tidak kosong, aplikasi tetap hidup (agar mudah di-debug & healthcheck
# jalan) TAPI seluruh akses tulis/admin diblokir sampai env diperbaiki.
_CONFIG_PROBLEMS = []


def require_admin():
    if _CONFIG_PROBLEMS:
        return json_error(
            "Panel admin dinonaktifkan: konfigurasi keamanan belum lengkap. "
            "Periksa log deploy & set env (AUTH_SECRET, DEFAULT_ADMIN_PASS, dll).",
            503,
            auth=False,
            config_error=True,
        )
    if not db.verify_admin_token(request_token()):
        return json_error(
            "Akses ditolak. Silakan login ulang sebagai admin.", 401, auth=False
        )
    return None


# ---------------------------------------------------------------------
#  PENJAGA KEAMANAN SAAT DEPLOY
# ---------------------------------------------------------------------
_INSECURE_SECRETS = {"", "ubah-secret-ini-di-hosting"}


def _is_production():
    """Deteksi lingkungan produksi (Railway/Render/Heroku dsb.)."""
    return bool(os.getenv("PORT")) or os.getenv("FLASK_ENV") == "production"


def security_selfcheck():
    """Periksa konfigurasi keamanan saat produksi.

    Dipanggil sekali saat modul di-import. Bila ada masalah, aplikasi TETAP
    dijalankan (supaya container hidup, log mudah dibaca, dan healthcheck bisa
    diakses) TAPI seluruh endpoint admin/write diblokir lewat require_admin(),
    serta healthcheck melaporkan status 'degraded'. Jadi tidak ada celah
    keamanan, namun juga tidak crash total yang membingungkan.
    """
    global _CONFIG_PROBLEMS

    if not _is_production():
        _CONFIG_PROBLEMS = []
        return

    problems = []
    if not config.AUTH_ENABLED:
        problems.append("AUTH_ENABLED=0 -> panel admin terbuka tanpa login.")
    if getattr(config, "AUTH_SECRET", "") in _INSECURE_SECRETS:
        problems.append("AUTH_SECRET masih default/kosong -> token admin mudah dipalsukan.")
    if getattr(config, "DEBUG", False):
        problems.append("APP_DEBUG=1 -> jangan aktifkan debug di produksi.")
    if db.DEFAULT_ADMIN_PASS in ("2026", "") and os.getenv("DEFAULT_ADMIN_PASS") is None:
        problems.append("DEFAULT_ADMIN_PASS masih default -> set DEFAULT_ADMIN_PASS yang kuat.")

    _CONFIG_PROBLEMS = problems

    if problems:
        bar = "!" * 60
        print(bar)
        print("PERINGATAN KEAMANAN: konfigurasi produksi belum lengkap!")
        for p in problems:
            print(f"  - {p}")
        print("Panel admin & operasi tulis DIBLOKIR sampai env diperbaiki.")
        print("Set environment variable berikut di dashboard hosting lalu redeploy:")
        print("  AUTH_SECRET=<string acak panjang>")
        print("  DEFAULT_ADMIN_PASS=<password kuat>")
        print("  APP_DEBUG=0")
        print(bar)


security_selfcheck()


def _startup_init_db():
    """Buat semua tabel saat app start (Railway/gunicorn maupun lokal).

    Best-effort: bila DB belum siap, cukup tampilkan peringatan agar container
    tetap hidup dan healthcheck melaporkan status. Diulang otomatis pada
    request berikutnya lewat ensure_schema().
    """
    try:
        db.ensure_all_tables()
        print("[startup] Skema database siap (products/reviews/admin_users).")
    except Exception as exc:  # noqa: BLE001
        _log_exc("[startup] Peringatan: gagal menyiapkan tabel database", exc)


def _startup_init_db_async():
    """Jalankan _startup_init_db() di thread latar (NON-blocking).

    PENTING untuk Railway: kalau DB lambat/tidak terjangkau, init tabel bisa
    memakan connect_timeout=5s x beberapa percobaan. Menjalankannya langsung
    saat import membuat gunicorn lama belum `listen`, sehingga healthcheck
    Railway (healthcheckPath=/api/health) bisa timeout lebih dulu dan deploy
    ditandai GAGAL/crash padahal aplikasi sehat. Karena itu init dijalankan
    di daemon thread: gunicorn langsung listen, dan bila DB siap tabel
    dibuat; bila belum, ensure_schema() akan mencobanya lagi saat request.
    """
    import threading

    worker = threading.Thread(
        target=_startup_init_db, name="startup-init-db", daemon=True
    )
    worker.start()


_startup_init_db_async()


# ---------------------------------------------------------------------
#  HALAMAN STATIS
# ---------------------------------------------------------------------
@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    """Layani file statis (html/css/js/img) dari folder root."""
    if filename.startswith("api/"):
        abort(404)

    full = os.path.join(BASE_DIR, filename)
    if os.path.isfile(full):
        return send_from_directory(BASE_DIR, filename)

    # Izinkan akses tanpa ekstensi .html (mis. /katalog -> katalog.html)
    if os.path.isfile(full + ".html"):
        return send_from_directory(BASE_DIR, filename + ".html")

    abort(404)


# ---------------------------------------------------------------------
#  API - AUTENTIKASI ADMIN
# ---------------------------------------------------------------------
@app.route("/api/login", methods=["POST"])
@app.route("/api/login.php", methods=["POST"])
def login():
    db.ensure_admin_table()

    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    if not db.auth_enabled():
        return jsonify({"success": True, "message": "Login tidak diperlukan.",
                        "auth": False, "token": None})

    if not username or not password:
        return json_error("Username dan password wajib diisi.", 400)

    if not db.check_admin_login(username, password):
        return json_error("Username atau password salah.", 401, auth=False)

    session = db.issue_admin_token()
    return jsonify({
        "success": True,
        "message": "Login berhasil.",
        "auth": True,
        "token": session["token"],
        "expires_at": session["expires_at"],
    })


@app.route("/api/session", methods=["GET"])
def session_status():
    ok = db.verify_admin_token(request_token())
    return jsonify({"success": True, "auth": db.auth_enabled(), "authenticated": bool(ok)})


@app.route("/api/live", methods=["GET"])
def live():
    """Liveness check SUPER RINGAN - sengaja TIDAK menyentuh database.

    Dipakai Railway sebagai healthcheckPath. Tujuannya hanya memastikan proses
    gunicorn sudah listen & melayani HTTP. Bila endpoint ini bergantung pada DB,
    deploy akan ditandai gagal saat MySQL belum siap / lambat, padahal aplikasi
    sebenarnya sehat. Status DB & config tetap bisa dicek lewat /api/health.
    """
    return jsonify({"success": True, "status": "alive", "commit": COMMIT_SHA})


@app.route("/api/health", methods=["GET"])
def health():
    """Health check untuk Railway/Render. Melaporkan status app & DB."""
    db_ok = True
    db_error = None
    try:
        db.query_one("SELECT 1 AS ok")
    except Exception as exc:  # noqa: BLE001 - laporkan apa pun sebagai tidak sehat
        db_ok = False
        db_error = str(exc)

    config_ok = not _CONFIG_PROBLEMS
    healthy = db_ok and config_ok
    # Healthcheck HTTP tetap 200 selama proses hidup, supaya Railway tidak
    # me-restart container hanya karena DB atau env belum siap. Status rinci
    # ada di field "status"/"config" agar mudah dicek dari browser.
    http_status = 200
    return (
        jsonify({
            "success": healthy,
            "status": "ok" if healthy else "degraded",
            "commit": COMMIT_SHA,
            "auth": db.auth_enabled(),
            "database": "ok" if db_ok else "error",
            "error": db_error,
            "config": "ok" if config_ok else "incomplete",
            "config_problems": list(_CONFIG_PROBLEMS),
        }),
        http_status,
    )


# ---------------------------------------------------------------------
#  API - PRODUK (GET)
# ---------------------------------------------------------------------
@app.route("/api/products", methods=["GET"])
@app.route("/api/products.php", methods=["GET"])
def products_get():
    db.ensure_schema()
    pid = request.args.get("id", "").strip()
    sku = (request.args.get("sku", "") or "").strip()

    try:
        # Cari satu produk lewat ?sku= (dipakai halaman detail.html)
        if sku:
            row = db.query_one("SELECT * FROM products WHERE sku = %s LIMIT 1", (sku,))
            if not row:
                return json_error("Produk tidak ditemukan.", 404)
            return jsonify({"success": True, "product": db.row_to_product(row)})

        if pid:
            if not pid.isdigit():
                return json_error("Parameter ?id= tidak valid.", 400)
            row = db.query_one("SELECT * FROM products WHERE id = %s LIMIT 1", (int(pid),))
            if not row:
                return json_error("Produk tidak ditemukan.", 404)
            return jsonify({"success": True, "product": db.row_to_product(row)})

        sql = "SELECT * FROM products"
        where, params = [], []

        # Filter status: default hanya aktif (kecuali ?include_all=1)
        include_all = request.args.get("include_all") == "1"
        if not include_all:
            where.append("status = 'aktif'")
        elif request.args.get("status"):
            where.append("status = %s")
            params.append(request.args["status"])

        category = request.args.get("category", "")
        if category in db.ALLOWED_CATEGORIES:
            where.append("category = %s")
            params.append(category)

        search = (request.args.get("search", "") or "").strip()
        if search:
            where.append("(name LIKE %s OR description LIKE %s OR sku LIKE %s)")
            like = f"%{search}%"
            params.extend([like, like, like])

        if where:
            sql += " WHERE " + " AND ".join(where)

        sort = request.args.get("sort", "newest")
        order_map = {
            "newest":     "id DESC",
            "price-asc":  "price ASC",
            "price-desc": "price DESC",
            "name":       "name ASC",
            "stock":      "stock DESC",
        }
        sql += " ORDER BY " + order_map.get(sort, "id DESC")

        # Pagination
        limit = request.args.get("limit", "").strip()
        if limit.isdigit() and int(limit) > 0:
            sql += f" LIMIT {min(int(limit), 500)}"

        rows = db.query_all(sql, params)
        return jsonify({
            "success": True,
            "count": len(rows),
            "products": [db.row_to_product(r) for r in rows],
        })

    except DbError as exc:
        return json_error(str(exc), 500)


# ---------------------------------------------------------------------
#  API - PRODUK (POST)
# ---------------------------------------------------------------------
@app.route("/api/products", methods=["POST"])
@app.route("/api/products.php", methods=["POST"])
def products_post():
    db.ensure_schema()
    denied = require_admin()
    if denied:
        return denied

    body, upload_errors = make_request_payload()
    payload, errors = db.validate_product(body)
    if errors:
        return json_error(" ".join(errors), 422)
    if upload_errors:
        return json_error(" ".join(upload_errors), 422)

    try:
        db.execute(
            """INSERT INTO products
                 (name, sku, category, subcategory, brand, price, discount_price, stock,
                  description, img, img_alt, images_json, video_url,
                  material, wood_type, warna, finishing, berat,
                  dimensi_panjang, dimensi_lebar, dimensi_tinggi, kapasitas_beban,
                  garansi, kondisi, perakitan, pelengkap, relasi_tipe, tags, status)
               VALUES
                 (%(name)s, %(sku)s, %(category)s, %(subcategory)s, %(brand)s, %(price)s, %(discount_price)s, %(stock)s,
                  %(description)s, %(img)s, %(img_alt)s, %(images_json)s, %(video_url)s,
                  %(material)s, %(wood_type)s, %(warna)s, %(finishing)s, %(berat)s,
                  %(dimensi_panjang)s, %(dimensi_lebar)s, %(dimensi_tinggi)s, %(kapasitas_beban)s,
                  %(garansi)s, %(kondisi)s, %(perakitan)s, %(pelengkap)s, %(relasi_tipe)s, %(tags)s, %(status)s)""",
            payload,
        )
        row = db.query_one(
            "SELECT * FROM products WHERE sku = %s LIMIT 1", (payload["sku"],)
        )
    except db.pymysql.err.IntegrityError as exc:
        msg = "SKU sudah dipakai. Gunakan SKU lain."
        if "name" in str(exc).lower():
            msg = "Nama produk sudah dipakai. Gunakan nama lain."
        return json_error(msg, 409)
    except DbError as exc:
        return json_error(str(exc), 500)

    return jsonify({
        "success": True,
        "message": "Produk berhasil ditambahkan.",
        "product": db.row_to_product(row),
    }), 201


# ---------------------------------------------------------------------
#  API - PRODUK (PUT)
# ---------------------------------------------------------------------
@app.route("/api/products", methods=["PUT"])
@app.route("/api/products.php", methods=["PUT"])
def products_put():
    db.ensure_schema()
    denied = require_admin()
    if denied:
        return denied

    pid = request.args.get("id", "").strip()
    if not pid.isdigit():
        return json_error("Parameter ?id= wajib diisi.", 400)
    pid = int(pid)

    try:
        exists = db.query_one("SELECT id FROM products WHERE id = %s", (pid,))
        if not exists:
            return json_error("Produk tidak ditemukan.", 404)

        body, upload_errors = make_request_payload()
        # SKU terkunci: saat edit, SKU selalu diambil dari data lama
        # (kode produk tidak boleh diubah agar URL detail ?sku= tetap stabil).
        existing = db.query_one("SELECT sku FROM products WHERE id = %s LIMIT 1", (pid,))
        if existing:
            body["sku"] = existing.get("sku") or ""
        payload, errors = db.validate_product(body)
        if errors:
            return json_error(" ".join(errors), 422)
        if upload_errors:
            return json_error(" ".join(upload_errors), 422)

        payload["id"] = pid
        db.execute(
            """UPDATE products SET
                 name = %(name)s, sku = %(sku)s, category = %(category)s,
                 subcategory = %(subcategory)s, brand = %(brand)s,
                 price = %(price)s, discount_price = %(discount_price)s, stock = %(stock)s,
                 description = %(description)s, img = %(img)s, img_alt = %(img_alt)s,
                 images_json = %(images_json)s, video_url = %(video_url)s,
                 material = %(material)s, wood_type = %(wood_type)s, warna = %(warna)s,
                 finishing = %(finishing)s, berat = %(berat)s,
                 dimensi_panjang = %(dimensi_panjang)s, dimensi_lebar = %(dimensi_lebar)s,
                 dimensi_tinggi = %(dimensi_tinggi)s, kapasitas_beban = %(kapasitas_beban)s,
                 garansi = %(garansi)s, kondisi = %(kondisi)s, perakitan = %(perakitan)s,
                 pelengkap = %(pelengkap)s, relasi_tipe = %(relasi_tipe)s,
                 tags = %(tags)s, status = %(status)s
               WHERE id = %(id)s""",
            payload,
        )
        row = db.query_one("SELECT * FROM products WHERE id = %s LIMIT 1", (pid,))
    except db.pymysql.err.IntegrityError as exc:
        msg = "SKU sudah dipakai. Gunakan SKU lain."
        if "name" in str(exc).lower():
            msg = "Nama produk sudah dipakai. Gunakan nama lain."
        return json_error(msg, 409)
    except DbError as exc:
        return json_error(str(exc), 500)

    return jsonify({
        "success": True,
        "message": "Produk berhasil diperbarui.",
        "product": db.row_to_product(row),
    })


# ---------------------------------------------------------------------
#  API - PRODUK (DELETE)
# ---------------------------------------------------------------------
@app.route("/api/products", methods=["DELETE"])
@app.route("/api/products.php", methods=["DELETE"])
def products_delete():
    denied = require_admin()
    if denied:
        return denied

    pid = request.args.get("id", "").strip()
    if not pid.isdigit():
        return json_error("Parameter ?id= wajib diisi.", 400)
    pid = int(pid)

    try:
        row = db.query_one("SELECT * FROM products WHERE id = %s LIMIT 1", (pid,))
        if not row:
            return json_error("Produk tidak ditemukan.", 404)

        db.execute("DELETE FROM products WHERE id = %s", (pid,))
    except DbError as exc:
        return json_error(str(exc), 500)

    return jsonify({
        "success": True,
        "message": f'Produk "{row["name"]}" berhasil dihapus.',
        "product": db.row_to_product(row),
    })


# ---------------------------------------------------------------------
#  API - UPLOAD FOTO (dari perangkat lokal -> folder img/)
# ---------------------------------------------------------------------
@app.route("/api/upload", methods=["POST"])
@app.route("/api/upload.php", methods=["POST"])
def upload_image():
    denied = require_admin()
    if denied:
        return denied

    files = (
        request.files.getlist("img")
        + request.files.getlist("image")
        + request.files.getlist("foto")
        + request.files.getlist("images[]")
        + request.files.getlist("images")
        + request.files.getlist("gallery")
    )
    files = [f for f in files if f and f.filename]
    if not files:
        return json_error("Tidak ada file yang diunggah. Gunakan field 'img' atau 'images[]'.", 400)

    saved, errors = [], []
    for f in files:
        rel, err = save_uploaded_image(f)
        if err:
            errors.append(err)
        else:
            saved.append(rel)

    if not saved:
        return json_error(" ".join(errors) or "Gagal menyimpan file.", 422)

    return jsonify({
        "success": True,
        "message": f"{len(saved)} file berhasil diunggah.",
        "files": saved,
        "url": saved[0],
        "img": saved[0],
        "errors": errors,
    }), 201


# ---------------------------------------------------------------------
#  API - STATISTIK (kunjungan, produk populer, tren favorit)
# ---------------------------------------------------------------------
@app.route("/api/track/view", methods=["POST"])
@app.route("/api/track/view.php", methods=["POST"])
def track_page_view():
    """Catat kunjungan harian. Publik (tanpa login)."""
    body = request.get_json(silent=True) or {}
    visitor_id = (body.get("visitorId") or body.get("visitor_id")
                  or request.headers.get("X-Visitor-Id") or "").strip()
    page = (body.get("page") or "site").strip()
    if not visitor_id:
        return json_error("visitorId wajib diisi.", 400)
    try:
        db.record_page_view(visitor_id, page)
    except DbError as exc:
        return json_error(str(exc), 503)
    return jsonify({"success": True, "tracked": True}), 201


@app.route("/api/track/product", methods=["POST"])
@app.route("/api/track/product.php", methods=["POST"])
def track_product_view():
    """Catat 1 kali lihat produk. Publik."""
    body = request.get_json(silent=True) or {}
    pid = body.get("productId") or body.get("product_id") or body.get("id")
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return json_error("productId tidak valid.", 400)
    try:
        db.record_product_view(pid)
    except DbError as exc:
        return json_error(str(exc), 503)
    return jsonify({"success": True, "tracked": True}), 201


@app.route("/api/track/favorite", methods=["POST"])
@app.route("/api/track/favorite.php", methods=["POST"])
def track_favorite():
    """Catat tambah/hapus favorit (untuk tren). Publik."""
    body = request.get_json(silent=True) or {}
    pid = body.get("productId") or body.get("product_id") or body.get("id")
    action = (body.get("action") or "add").strip().lower()
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return json_error("productId tidak valid.", 400)
    try:
        db.record_favorite_event(pid, action)
    except DbError as exc:
        return json_error(str(exc), 503)
    return jsonify({"success": True, "tracked": True}), 201


@app.route("/api/admin/stats", methods=["GET"])
@app.route("/api/admin/stats.php", methods=["GET"])
def admin_stats():
    """Ringkasan statistik untuk panel admin (butuh login admin)."""
    denied = require_admin()
    if denied:
        return denied
    days = request.args.get("days", "7")
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 7
    try:
        stats = db.get_statistics(days)
    except DbError as exc:
        return json_error(str(exc), 503)
    return jsonify({"success": True, "stats": stats})


# ---------------------------------------------------------------------
#  API - ULASAN (REVIEWS)
#  GET  /api/reviews?sku=IMJ-0001   -> daftar ulasan produk (publik)
#  POST /api/reviews                -> tambah ulasan (admin)
#  DELETE /api/reviews?id=5         -> hapus ulasan (admin)
# ---------------------------------------------------------------------
@app.route("/api/reviews", methods=["GET"])
@app.route("/api/reviews.php", methods=["GET"])
@app.route("/api/reviews/all", methods=["GET"])
def reviews_get():
    sku = (request.args.get("sku", "") or "").strip()
    pid = (request.args.get("product_id", "") or request.args.get("id", "") or "").strip()

    # Daftar semua ulasan (khusus panel admin).
    if request.args.get("all") == "1" or request.path.endswith("/reviews/all"):
        denied = require_admin()
        if denied:
            return denied
        try:
            reviews = db.list_all_reviews(500)
        except DbError as exc:
            return json_error(str(exc), 503)
        return jsonify({"success": True, "count": len(reviews), "reviews": reviews})

    try:
        if sku:
            row = db.query_one("SELECT id FROM products WHERE sku = %s LIMIT 1", (sku,))
            if not row:
                return json_error("Produk tidak ditemukan.", 404)
            pid = int(row["id"])
        elif pid:
            if not str(pid).isdigit():
                return json_error("Parameter ?product_id= tidak valid.", 400)
            pid = int(pid)
        else:
            return json_error("Parameter ?sku= atau ?product_id= wajib diisi.", 400)

        reviews = db.get_reviews(pid)
    except DbError as exc:
        return json_error(str(exc), 503)

    summary = db.summarize_reviews(reviews)
    return jsonify({"success": True, **summary})


@app.route("/api/reviews", methods=["POST"])
@app.route("/api/reviews.php", methods=["POST"])
def reviews_post():
    denied = require_admin()
    if denied:
        return denied

    body = request.get_json(silent=True) or {}
    try:
        review, errors = db.validate_review(body)
        if errors:
            return json_error(" ".join(errors), 422)
        created = db.create_review(review)
    except DbError as exc:
        return json_error(str(exc), 503)

    return jsonify({
        "success": True,
        "message": "Ulasan berhasil ditambahkan.",
        "review": created,
    }), 201


@app.route("/api/reviews", methods=["DELETE"])
@app.route("/api/reviews.php", methods=["DELETE"])
def reviews_delete():
    denied = require_admin()
    if denied:
        return denied

    rid = (request.args.get("id", "") or "").strip()
    if not rid.isdigit():
        return json_error("Parameter ?id= wajib diisi.", 400)

    try:
        row = db.query_one("SELECT * FROM reviews WHERE id = %s LIMIT 1", (int(rid),))
        if not row:
            return json_error("Ulasan tidak ditemukan.", 404)
        db.execute("DELETE FROM reviews WHERE id = %s", (int(rid),))
    except DbError as exc:
        return json_error(str(exc), 503)

    return jsonify({"success": True, "message": "Ulasan berhasil dihapus."})



# ---------------------------------------------------------------------
#  ERROR HANDLER
# ---------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return json_error("Endpoint tidak ditemukan.", 404)
    # Untuk halaman biasa, tampilkan 404.html (bukan JSON).
    page = os.path.join(BASE_DIR, "404.html")
    if os.path.isfile(page):
        return send_from_directory(BASE_DIR, "404.html"), 404
    return json_error("Halaman tidak ditemukan.", 404)


@app.errorhandler(405)
def method_not_allowed(_e):
    return json_error("Metode HTTP tidak diizinkan untuk endpoint ini.", 405)


@app.errorhandler(413)
def payload_too_large(_e):
    return json_error(
        f"Ukuran berkas terlalu besar. Maksimal {getattr(config, 'MAX_UPLOAD_MB', 5)} MB.", 413
    )


@app.errorhandler(400)
def bad_request(_e):
    if request.path.startswith("/api/"):
        return json_error("Permintaan tidak valid.", 400)
    return json_error("Permintaan tidak valid.", 400)


# ---------------------------------------------------------------------
#  MAIN
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Pastikan stdout bisa mencetak karakter non-ASCII di semua shell (Windows cp1252).
    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    # Hosting (Railway/Render) memberi port lewat variabel environment $PORT.
    port = int(os.getenv("PORT", str(config.PORT)))
    host = os.getenv("APP_HOST", ("0.0.0.0" if os.getenv("PORT") else config.HOST))
    debug = config.DEBUG and not os.getenv("PORT")

    print("=" * 60)
    print("  Ine Mebel Jepara - Flask + MySQL")
    print("=" * 60)
    print(f"  Website : http://{host}:{port}/")
    print(f"  Admin   : http://{host}:{port}/admin.html")
    print(f"  API     : http://{host}:{port}/api/products")
    print(f"  MySQL   : {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    print(f"  Login   : {'AKTIF (tabel admin_users)' if config.AUTH_ENABLED else 'nonaktif'}")
    print("=" * 60)
    print()
    print("  Laragon lokal: pastikan sudah 'Start All' sebelum menjalankan ini.")
    print()
    app.run(host=host, port=port, debug=debug)