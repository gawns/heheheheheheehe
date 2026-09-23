"""
Ine Mebel Jepara - Helper database (Laragon / MySQL)
====================================================
Berisi:
  - get_conn()            : koneksi MySQL (PyMySQL) ke Laragon
  - ensure_schema()       : migrasi otomatis 30 kolom
  - row_to_product()      : mapping baris DB -> dict produk (camelCase)
  - validate_product()    : validasi payload produk
"""

import hmac
import hashlib
import json
import os
import time

import pymysql
import pymysql.cursors

import config

ALLOWED_CATEGORIES = ["kursi", "meja", "sofa", "lemari", "aksesoris", "lainnya", "tempat_tidur"]


# ---------------------------------------------------------------------
#  KONEKSI DATABASE
# ---------------------------------------------------------------------
class DbError(Exception):
    """Gagal terhubung / query ke database."""


def get_conn():
    """Buka koneksi baru ke MySQL. Pemanggil wajib menutupnya."""
    connect_kwargs = dict(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASS,
        database=config.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=5,
    )
    # TLS opsional untuk MySQL terkelola (mis. Railway/produksi).
    if getattr(config, "DB_SSL", False):
        connect_kwargs["ssl"] = {}
    try:
        return pymysql.connect(**connect_kwargs)
    except pymysql.MySQLError as exc:
        raise DbError(
            "Tidak dapat terhubung ke database MySQL. "
            "Lokal: pastikan Laragon sudah dijalankan (klik 'Start All'). "
            "Produksi: periksa env MYSQLHOST/MYSQLUSER/MYSQLPASSWORD/MYSQLDATABASE. "
            f"Target: {config.DB_HOST}:{config.DB_PORT}. "
            f"Detail: {exc}"
        ) from exc


def query_all(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def query_one(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def execute(sql, params=None):
    """Jalankan INSERT/UPDATE/DELETE. Kembalikan (lastrowid, rowcount)."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.lastrowid, cur.rowcount


# ---------------------------------------------------------------------
#  MIGRASI SKEMA - pastikan semua kolom ada
# ---------------------------------------------------------------------
# DDL tabel products. Dipakai ensure_schema() untuk membuat tabel bila belum
# ada (penting saat deploy ke Railway/DB kosong), sekaligus jadi acuan kolom
# yang dipakai MIGRATIONS di bawah. Dijaga sinkron dengan db-init.py.
PRODUCTS_DDL = """
CREATE TABLE IF NOT EXISTS products (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  name            VARCHAR(200)  NOT NULL,
  sku             VARCHAR(80)   NOT NULL UNIQUE,
  category        ENUM('kursi','meja','sofa','lemari','aksesori','tempat_tidur') NOT NULL,
  subcategory     VARCHAR(100)  NOT NULL DEFAULT '',
  brand           VARCHAR(120)  NOT NULL DEFAULT '',
  price           INT UNSIGNED  NOT NULL,
  discount_price  INT UNSIGNED  NULL,
  stock           INT UNSIGNED  NOT NULL DEFAULT 0,
  description     TEXT          NOT NULL,
  img             VARCHAR(500)  NOT NULL DEFAULT '',
  img_alt         VARCHAR(200)  NOT NULL DEFAULT '',
  images_json     TEXT          NULL,
  video_url       VARCHAR(500)  NOT NULL DEFAULT '',
  material        VARCHAR(255)  NOT NULL DEFAULT '',
  wood_type       VARCHAR(80)   NOT NULL DEFAULT '',
  warna           VARCHAR(200)  NOT NULL DEFAULT '',
  finishing       VARCHAR(200)  NOT NULL DEFAULT '',
  berat           VARCHAR(60)   NOT NULL DEFAULT '',
  dimensi_panjang DECIMAL(8,2)  NOT NULL DEFAULT 0,
  dimensi_lebar   DECIMAL(8,2)  NOT NULL DEFAULT 0,
  dimensi_tinggi  DECIMAL(8,2)  NOT NULL DEFAULT 0,
  kapasitas_beban DECIMAL(8,2)  NULL,
  garansi         VARCHAR(150)  NOT NULL DEFAULT '',
  kondisi         ENUM('baru','bekas') NOT NULL DEFAULT 'baru',
  perakitan       ENUM('sudah','perlu') NOT NULL DEFAULT 'sudah',
  pelengkap       VARCHAR(120)  NOT NULL DEFAULT '',
  relasi_tipe     VARCHAR(60)   NOT NULL DEFAULT '',
  tags            VARCHAR(300)  NOT NULL DEFAULT '',
  status          ENUM('aktif','nonaktif','draft') NOT NULL DEFAULT 'aktif',
  created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_category (category),
  INDEX idx_status (status),
  INDEX idx_price (price),
  INDEX idx_sku (sku)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def ensure_products_table():
    """Buat tabel products bila belum ada (aman diulang / idempotent)."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(PRODUCTS_DDL)


MIGRATIONS = {
    "sku":             "VARCHAR(80) NOT NULL DEFAULT '' AFTER name",
    "subcategory":     "VARCHAR(100) NOT NULL DEFAULT '' AFTER category",
    "brand":           "VARCHAR(120) NOT NULL DEFAULT '' AFTER subcategory",
    "discount_price":  "INT UNSIGNED NULL AFTER price",
    "stock":           "INT UNSIGNED NOT NULL DEFAULT 0 AFTER discount_price",
    "images_json":     "TEXT NULL AFTER img_alt",
    "video_url":       "VARCHAR(500) NOT NULL DEFAULT '' AFTER images_json",
    "wood_type":       "VARCHAR(80) NOT NULL DEFAULT '' AFTER material",
    "dimensi_panjang": "DECIMAL(8,2) NOT NULL DEFAULT 0 AFTER berat",
    "dimensi_lebar":   "DECIMAL(8,2) NOT NULL DEFAULT 0 AFTER dimensi_panjang",
    "dimensi_tinggi":  "DECIMAL(8,2) NOT NULL DEFAULT 0 AFTER dimensi_lebar",
    "kapasitas_beban": "DECIMAL(8,2) NULL AFTER dimensi_tinggi",
    "kondisi":         "ENUM('baru','bekas') NOT NULL DEFAULT 'baru' AFTER garansi",
    "perakitan":       "ENUM('sudah','perlu') NOT NULL DEFAULT 'sudah' AFTER kondisi",
    "relasi_tipe":     "VARCHAR(60) NOT NULL DEFAULT '' AFTER pelengkap",
    "tags":            "VARCHAR(300) NOT NULL DEFAULT '' AFTER relasi_tipe",
    "status":          "ENUM('aktif','nonaktif','draft') NOT NULL DEFAULT 'aktif' AFTER tags",
}


def ensure_schema():
    """Pastikan skema siap pakai.

    - Membuat tabel products bila belum ada (penting di Railway/DB kosong).
    - Menambah kolom yang belum ada + backfill data lama.
    Idempotent: aman dipanggil berkali-kali.
    """
    try:
        # Buat tabel bila belum ada, supaya DB baru tetap bisa dipakai.
        ensure_products_table()

        with get_conn() as conn, conn.cursor() as cur:
            for col, definition in MIGRATIONS.items():
                cur.execute(f"SHOW COLUMNS FROM products LIKE '{col}'")
                if not cur.fetchone():
                    cur.execute(f"ALTER TABLE products ADD COLUMN {col} {definition}")

            # Backfill SKU dari id (untuk data lama)
            cur.execute(
                "UPDATE products SET sku = CONCAT('IMJ-', LPAD(id, 4, '0')) "
                "WHERE sku = '' OR sku IS NULL"
            )
            # Pastikan status default aktif
            cur.execute(
                "UPDATE products SET status = 'aktif' "
                "WHERE status IS NULL OR status = ''"
            )
            # Perbaiki path gambar lokal lama
            cur.execute("""
                UPDATE products
                SET img = 'img/produk-sofa-klasik-marun.jpeg'
                WHERE img IS NULL OR img = ''
            """)
    except Exception:
        pass

    # Tabel ulasan (reviews) - dipakai halaman detail & panel admin
    try:
        ensure_reviews_table()
    except Exception:
        pass


def ensure_all_tables():
    """Pastikan semua tabel inti ada. Dipakai saat startup aplikasi.

    Berbeda dengan ensure_schema() (yang menelan error agar request tetap
    jalan), fungsi ini membiarkan error naik supaya masalah DB terlihat jelas
    di log deploy. Tetap idempotent.
    """
    ensure_products_table()
    ensure_reviews_table()
    ensure_admin_table()


# ---------------------------------------------------------------------
#  ULASAN PRODUK (REVIEWS)
# ---------------------------------------------------------------------
REVIEWS_TABLE = "reviews"

REVIEWS_DDL = """
    CREATE TABLE IF NOT EXISTS reviews (
        id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        product_id INT UNSIGNED    NOT NULL,
        sku        VARCHAR(80)     NOT NULL DEFAULT '',
        name       VARCHAR(120)    NOT NULL DEFAULT '',
        rating     TINYINT UNSIGNED NOT NULL DEFAULT 5,
        comment    TEXT            NOT NULL,
        created_at TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_review_product (product_id),
        KEY idx_review_sku (sku)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def ensure_reviews_table():
    """Buat tabel reviews bila belum ada."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(REVIEWS_DDL)


def _row_to_review(row: dict) -> dict:
    return {
        "id":        int(row.get("id") or 0),
        "productId": int(row.get("product_id") or 0),
        "sku":       row.get("sku") or "",
        "name":      row.get("name") or "",
        "rating":    int(row.get("rating") or 0),
        "comment":   row.get("comment") or "",
        "createdAt": str(row.get("created_at") or ""),
    }


def get_reviews(product_id: int):
    """Ambil semua ulasan untuk satu produk (terbaru lebih dulu)."""
    ensure_reviews_table()
    rows = query_all(
        f"SELECT * FROM {REVIEWS_TABLE} WHERE product_id = %s ORDER BY id DESC",
        (int(product_id),),
    )
    return [_row_to_review(r) for r in rows]


def list_all_reviews(limit: int = 200):
    """Ambil semua ulasan (untuk panel admin), terbaru lebih dulu."""
    ensure_reviews_table()
    rows = query_all(
        f"SELECT * FROM {REVIEWS_TABLE} ORDER BY id DESC LIMIT %s",
        (max(1, min(int(limit or 200), 1000)),),
    )
    return [_row_to_review(r) for r in rows]


def summarize_reviews(reviews) -> dict:
    """Ringkas daftar ulasan -> {reviews, count, average, ratingCount}."""
    reviews = reviews or []
    count = len(reviews)
    average = round(sum(r.get("rating", 0) for r in reviews) / count, 1) if count else 0.0
    return {
        "reviews": reviews,
        "count": count,
        "average": average,
    }


def validate_review(body: dict):
    """Validasi payload ulasan. Kembalikan (review, errors)."""
    errors = []

    sku = str(body.get("sku") or body.get("productSku") or "").strip()
    pid = body.get("productId") or body.get("product_id")
    if sku:
        row = query_one("SELECT id, sku FROM products WHERE sku = %s LIMIT 1", (sku,))
        if not row:
            errors.append("Produk dengan SKU tersebut tidak ditemukan.")
            pid = None
        else:
            pid = int(row["id"])
    else:
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            errors.append("Produk wajib dipilih.")
            pid = None

    name = str(body.get("name") or "").strip()
    comment = str(body.get("comment") or "").strip()
    try:
        rating = int(body.get("rating") or 5)
    except (TypeError, ValueError):
        rating = 5

    if not name:
        errors.append("Nama pengulas wajib diisi.")
    if not comment:
        errors.append("Isi ulasan wajib diisi.")
    if rating < 1 or rating > 5:
        errors.append("Rating harus antara 1 sampai 5.")

    if errors:
        return None, errors

    return {
        "product_id": pid,
        "sku": sku,
        "name": name,
        "rating": rating,
        "comment": comment,
    }, []


def create_review(review: dict) -> dict:
    """Simpan ulasan baru, kembalikan objek ulasan yang dibuat."""
    ensure_reviews_table()
    if not review.get("sku"):
        row = query_one("SELECT sku FROM products WHERE id = %s LIMIT 1", (review["product_id"],))
        review["sku"] = (row or {}).get("sku") or ""
    execute(
        f"INSERT INTO {REVIEWS_TABLE} (product_id, sku, name, rating, comment) "
        "VALUES (%s, %s, %s, %s, %s)",
        (
            review["product_id"],
            review["sku"],
            review["name"],
            review["rating"],
            review["comment"],
        ),
    )
    row = query_one(
        f"SELECT * FROM {REVIEWS_TABLE} WHERE product_id = %s ORDER BY id DESC LIMIT 1",
        (review["product_id"],),
    )
    return _row_to_review(row or {})


# ---------------------------------------------------------------------
#  STATISTIK - kunjungan harian, produk populer, tren favorit
# ---------------------------------------------------------------------
ANALYTICS_TABLES = {
    "page_views": """
        CREATE TABLE IF NOT EXISTS page_views (
            id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            visitor_id VARCHAR(64)  NOT NULL DEFAULT '',
            page       VARCHAR(80)  NOT NULL DEFAULT '',
            view_date  DATE         NOT NULL,
            created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_view_date (view_date),
            KEY idx_visitor_date (visitor_id, view_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "product_views": """
        CREATE TABLE IF NOT EXISTS product_views (
            product_id BIGINT UNSIGNED NOT NULL,
            view_date  DATE            NOT NULL,
            views      INT UNSIGNED    NOT NULL DEFAULT 0,
            PRIMARY KEY (product_id, view_date),
            KEY idx_pv_date (view_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "favorite_events": """
        CREATE TABLE IF NOT EXISTS favorite_events (
            id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            product_id BIGINT UNSIGNED NOT NULL,
            action     ENUM('add','remove') NOT NULL DEFAULT 'add',
            event_date DATE         NOT NULL,
            created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_fe_date (event_date),
            KEY idx_fe_product (product_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
}


def ensure_analytics_tables():
    """Buat tabel-tabel statistik bila belum ada."""
    with get_conn() as conn, conn.cursor() as cur:
        for ddl in ANALYTICS_TABLES.values():
            cur.execute(ddl)


def record_page_view(visitor_id: str, page: str = "site"):
    """Catat satu kunjungan harian. 1 visitor dihitung sekali per hari."""
    ensure_analytics_tables()
    vid = (str(visitor_id) or "")[:64]
    pg = (str(page) or "site")[:80] or "site"
    execute(
        "INSERT INTO page_views (visitor_id, page, view_date) "
        "VALUES (%s, %s, CURDATE())",
        (vid, pg),
    )


def record_product_view(product_id: int):
    """Tambah 1 hitungan tampil untuk produk pada hari ini."""
    ensure_analytics_tables()
    execute(
        "INSERT INTO product_views (product_id, view_date, views) "
        "VALUES (%s, CURDATE(), 1) "
        "ON DUPLICATE KEY UPDATE views = views + 1",
        (int(product_id),),
    )


def record_favorite_event(product_id: int, action: str):
    """Catat penambahan/penghapusan favorit untuk tren."""
    ensure_analytics_tables()
    act = "remove" if str(action).lower() == "remove" else "add"
    execute(
        "INSERT INTO favorite_events (product_id, action, event_date) "
        "VALUES (%s, %s, CURDATE())",
        (int(product_id), act),
    )


# ---------------------------------------------------------------------
#  MAPPING & VALIDASI PRODUK
# ---------------------------------------------------------------------
def row_to_product(row: dict) -> dict:
    """Ubah baris DB menjadi dict produk (camelCase agar cocok dgn frontend)."""
    images = []
    try:
        if row.get("images_json"):
            images = json.loads(row["images_json"])
    except Exception:
        images = []

    return {
        "id":              int(row.get("id") or 0),
        "name":            row.get("name") or "",
        "sku":             row.get("sku") or "",
        "category":        row.get("category") or "",
        "subcategory":     row.get("subcategory") or "",
        "brand":           row.get("brand") or "",
        "price":           int(row.get("price") or 0),
        "discountPrice":   int(row["discount_price"]) if row.get("discount_price") else None,
        "stock":           int(row.get("stock") or 0),
        "desc":            row.get("description") or "",
        "img":             row.get("img") or "",
        "imgAlt":          row.get("img_alt") or "",
        "images":          images if isinstance(images, list) else [],
        "videoUrl":        row.get("video_url") or "",
        "material":        row.get("material") or "",
        "woodType":        row.get("wood_type") or "",
        "warna":           row.get("warna") or "",
        "finishing":       row.get("finishing") or "",
        "berat":           row.get("berat") or "",
        "dimensiPanjang":  float(row.get("dimensi_panjang") or 0),
        "dimensiLebar":    float(row.get("dimensi_lebar") or 0),
        "dimensiTinggi":   float(row.get("dimensi_tinggi") or 0),
        "kapasitasBeban":  float(row["kapasitas_beban"]) if row.get("kapasitas_beban") else None,
        "garansi":         row.get("garansi") or "",
        "kondisi":         row.get("kondisi") or "baru",
        "perakitan":       row.get("perakitan") or "sudah",
        "pelengkap":       row.get("pelengkap") or "",
        "relasiTipe":      row.get("relasi_tipe") or "",
        "tags":            [t.strip() for t in (row.get("tags") or "").split(",") if t.strip()],
        "status":          row.get("status") or "aktif",
    }


def get_statistics(days: int = 7) -> dict:
    """Ringkasan statistik untuk panel admin (kunjungan, populer, tren favorit)."""
    days = max(1, min(int(days or 7), 90))
    ensure_analytics_tables()

    per_day = query_all(
        "SELECT view_date AS d, COUNT(DISTINCT visitor_id) AS n "
        "FROM page_views "
        "WHERE view_date >= (CURDATE() - INTERVAL %s DAY) "
        "GROUP BY view_date ORDER BY view_date ASC",
        (days - 1,),
    )
    per_day = [{"date": str(r["d"]), "count": int(r["n"] or 0)} for r in per_day]

    today = query_one(
        "SELECT COUNT(DISTINCT visitor_id) AS n FROM page_views WHERE view_date = CURDATE()"
    )
    total = query_one("SELECT COUNT(DISTINCT visitor_id) AS n FROM page_views")

    popular = query_all(
        """
        SELECT p.id, p.name, p.sku, p.img, p.category,
               COALESCE(v.total_views, 0) AS views,
               COALESCE(f.total_favs, 0)  AS favorites
        FROM products p
        LEFT JOIN (
            SELECT product_id, SUM(views) AS total_views
            FROM product_views GROUP BY product_id
        ) v ON v.product_id = p.id
        LEFT JOIN (
            SELECT product_id, COUNT(*) AS total_favs
            FROM favorite_events WHERE action = 'add' GROUP BY product_id
        ) f ON f.product_id = p.id
        ORDER BY views DESC, favorites DESC, p.id DESC
        LIMIT 10
        """
    )
    popular = [{
        "id": int(r["id"]),
        "name": r.get("name") or "",
        "sku": r.get("sku") or "",
        "img": r.get("img") or "",
        "category": r.get("category") or "",
        "views": int(r.get("views") or 0),
        "favorites": int(r.get("favorites") or 0),
    } for r in popular]

    trend = query_all(
        "SELECT event_date AS d, "
        "  SUM(action = 'add')    AS added, "
        "  SUM(action = 'remove') AS removed "
        "FROM favorite_events "
        "WHERE event_date >= (CURDATE() - INTERVAL %s DAY) "
        "GROUP BY event_date ORDER BY event_date ASC",
        (days - 1,),
    )
    trend = [{
        "date": str(r["d"]),
        "added": int(r.get("added") or 0),
        "removed": int(r.get("removed") or 0),
    } for r in trend]

    categories = query_all(
        "SELECT category, COUNT(*) AS n FROM products GROUP BY category ORDER BY n DESC"
    )
    categories = [{"category": r.get("category") or "", "count": int(r.get("n") or 0)}
                  for r in categories]

    return {
        "days": days,
        "visitors": {
            "today": int((today or {}).get("n") or 0),
            "total": int((total or {}).get("n") or 0),
            "perDay": per_day,
        },
        "popular": popular,
        "favoriteTrend": trend,
        "categories": categories,
    }


def _digits(value) -> int:
    """Ambil angka murni dari nilai apa pun (mis. '3.500.000' -> 3500000)."""
    s = "".join(ch for ch in str(value or "") if ch.isdigit())
    return int(s) if s else 0


def _to_float(value, default=0.0) -> float:
    try:
        return float(value) if value not in (None, "") else default
    except (ValueError, TypeError):
        return default


def validate_product(body: dict):
    """
    Validasi payload produk (28 field).
    Kembalikan (payload, errors). payload=None bila ada errors.
    """
    name = str(body.get("name") or "").strip()
    sku = str(body.get("sku") or "").strip()
    category = str(body.get("category") or "").strip()
    desc = str(body.get("desc") or "").strip()
    price = _digits(body.get("price"))
    discount_raw = body.get("discountPrice")
    discount = _digits(discount_raw) if discount_raw else None
    stock = _digits(body.get("stock"))
    material = str(body.get("material") or "").strip()
    warna = str(body.get("warna") or "").strip()
    status = str(body.get("status") or "aktif").strip()

    errors = []
    if not name:
        errors.append("Nama produk wajib diisi.")
    if not sku:
        errors.append("SKU wajib diisi.")
    if category not in ALLOWED_CATEGORIES:
        errors.append(f"Kategori tidak valid (pilih: {', '.join(ALLOWED_CATEGORIES)}).")
    if not desc:
        errors.append("Deskripsi wajib diisi.")
    if price <= 0:
        errors.append("Harga harus lebih besar dari 0.")
    if not material:
        errors.append("Material wajib diisi.")
    if not warna:
        errors.append("Warna wajib diisi.")
    if status not in ("aktif", "nonaktif", "draft"):
        errors.append("Status tidak valid.")

    if errors:
        return None, errors

    # Serialisasi images (array) -> JSON string
    try:
        images = body.get("images") or []
        if not isinstance(images, list):
            images = []
        images_json = json.dumps(images, ensure_ascii=False) if images else None
    except Exception:
        images_json = None

    # Serialisasi tags (array) -> comma string
    tags_raw = body.get("tags") or []
    if isinstance(tags_raw, list):
        tags = ",".join(str(t).strip() for t in tags_raw if str(t).strip())
    else:
        tags = str(tags_raw).strip()

    payload = {
        "name": name,
        "sku": sku,
        "category": category,
        "subcategory": str(body.get("subcategory") or "").strip(),
        "brand": str(body.get("brand") or "").strip(),
        "price": price,
        "discount_price": discount,
        "stock": stock,
        "description": desc,
        "img": str(body.get("img") or "").strip(),
        "img_alt": name,
        "images_json": images_json,
        "video_url": str(body.get("videoUrl") or "").strip(),
        "material": material,
        "wood_type": str(body.get("woodType") or "").strip(),
        "warna": warna,
        "finishing": str(body.get("finishing") or "").strip(),
        "berat": str(body.get("berat") or "").strip(),
        "dimensi_panjang": _to_float(body.get("dimensiPanjang")),
        "dimensi_lebar":   _to_float(body.get("dimensiLebar")),
        "dimensi_tinggi":  _to_float(body.get("dimensiTinggi")),
        "kapasitas_beban": _to_float(body.get("kapasitasBeban")) or None,
        "garansi": str(body.get("garansi") or "").strip(),
        "kondisi": str(body.get("kondisi") or "baru").strip(),
        "perakitan": str(body.get("perakitan") or "sudah").strip(),
        "pelengkap": str(body.get("pelengkap") or "").strip(),
        "relasi_tipe": str(body.get("relasiTipe") or "").strip(),
        "tags": tags,
        "status": status,
    }
    return payload, []


# ---------------------------------------------------------------------
#  AUTENTIKASI ADMIN (password disimpan di tabel admin_users)
# ---------------------------------------------------------------------
ADMIN_TABLE = "admin_users"
DEFAULT_ADMIN_USER = getattr(config, "DEFAULT_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASS = getattr(config, "DEFAULT_ADMIN_PASS", "2026")


def _hash_password(password: str, salt: str | None = None) -> str:
    """Buat hash PBKDF2 untuk password. Format: pbkdf2$<salt>$<hex>."""
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", str(password).encode(), salt.encode(), 120_000)
    return f"pbkdf2${salt}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    """Cek password terhadap hash tersimpan (PBKDF2)."""
    try:
        scheme, salt, digest = str(stored).split("$", 2)
        if scheme != "pbkdf2":
            return False
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", str(password).encode(), salt.encode(), 120_000)
    return hmac.compare_digest(candidate.hex(), digest)


def ensure_admin_table():
    """Buat tabel admin_users bila belum ada, lalu isi admin default."""
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {ADMIN_TABLE} (
                    id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    username      VARCHAR(60)  NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                              ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uniq_username (username)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute(f"SELECT COUNT(*) AS n FROM {ADMIN_TABLE}")
            if int((cur.fetchone() or {}).get("n") or 0) == 0:
                cur.execute(
                    f"INSERT INTO {ADMIN_TABLE} (username, password_hash) VALUES (%s, %s)",
                    (DEFAULT_ADMIN_USER, _hash_password(DEFAULT_ADMIN_PASS)),
                )
    except Exception:
        pass


def auth_enabled() -> bool:
    return bool(getattr(config, "AUTH_ENABLED", False))


def check_admin_login(username: str, password: str) -> bool:
    """Validasi login admin terhadap tabel admin_users."""
    if not auth_enabled():
        return False
    try:
        ensure_admin_table()
        row = query_one(
            f"SELECT password_hash FROM {ADMIN_TABLE} WHERE username = %s LIMIT 1",
            (str(username),),
        )
    except Exception:
        return False
    if not row:
        return False
    return _verify_password(password, row.get("password_hash") or "")


def set_admin_password(username: str, new_password: str) -> bool:
    """Ganti / set password admin langsung dari database."""
    ensure_admin_table()
    row = query_one(f"SELECT id FROM {ADMIN_TABLE} WHERE username = %s LIMIT 1", (str(username),))
    hashed = _hash_password(new_password)
    if row:
        execute(f"UPDATE {ADMIN_TABLE} SET password_hash = %s WHERE username = %s",
                (hashed, str(username)))
    else:
        execute(f"INSERT INTO {ADMIN_TABLE} (username, password_hash) VALUES (%s, %s)",
                (str(username), hashed))
    return True


def issue_admin_token() -> dict:
    expires = int(time.time()) + int(getattr(config, "TOKEN_TTL", 8 * 60 * 60))
    sig = hmac.new(
        getattr(config, "AUTH_SECRET", "").encode(),
        f"admin|{expires}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return {"token": f"{expires}.{sig}", "expires_at": expires}


def verify_admin_token(token: str | None) -> bool:
    if not auth_enabled():
        return True
    if not token or "." not in token:
        return False
    expires, _, sig = token.partition(".")
    if not expires.isdigit() or not sig:
        return False
    if int(expires) < time.time():
        return False
    expected = hmac.new(
        getattr(config, "AUTH_SECRET", "").encode(),
        f"admin|{expires}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, sig)