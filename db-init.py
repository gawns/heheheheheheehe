"""
Ine Mebel Jepara - Inisialisasi database MySQL Laragon
======================================================
Jalankan SEKALI dari command line:

    python db-init.py

Script ini akan:
  1. Membuat database `jepara_nusantara` (jika belum ada)
  2. Membuat tabel products (30 kolom)
  3. Mengisi seed 12 produk awal

Aman dijalankan berulang kali (idempotent).
"""

import pymysql
import config


def _seed_row(
    name, sku, category, subcategory, brand, description,
    price, discount_price, stock, img, img_alt,
    material, wood_type, warna, finishing, berat,
    dimensi_panjang, dimensi_lebar, dimensi_tinggi, kapasitas_beban,
    garansi, kondisi, perakitan, pelengkap, relasi_tipe, tags, status,
    images=None, video_url=""
):
    """Helper: bikin dict lengkap semua key yang dibutuhkan INSERT_SQL."""
    return {
        "name": name,
        "sku": sku,
        "category": category,
        "subcategory": subcategory,
        "brand": brand,
        "price": price,
        "discount_price": discount_price,
        "stock": stock,
        "description": description,
        "img": img,
        "img_alt": img_alt,
        "images_json": None,  # kolom TEXT NULL
        "video_url": video_url,
        "material": material,
        "wood_type": wood_type,
        "warna": warna,
        "finishing": finishing,
        "berat": berat,
        "dimensi_panjang": dimensi_panjang,
        "dimensi_lebar": dimensi_lebar,
        "dimensi_tinggi": dimensi_tinggi,
        "kapasitas_beban": kapasitas_beban,
        "garansi": garansi,
        "kondisi": kondisi,
        "perakitan": perakitan,
        "pelengkap": pelengkap,
        "relasi_tipe": relasi_tipe,
        "tags": tags,
        "status": status,
    }


SEED = [
    _seed_row(
        name="Kursi Tamarind", sku="IMJ-0001", category="kursi",
        subcategory="Kursi Makan", brand="Ine Mebel Jepara",
        description="Kursi makan dari kayu jati grade A dengan bantalan kain katun tenun alami. Konstruksi sambungan baji tradisional Jepara yang terbukti kuat selama puluhan tahun.",
        price=3850000, discount_price=3450000, stock=24,
        img="img/produk-wa-03.jpeg",
        img_alt="Kursi makan kayu jati bergaya modern",
        material="Kayu Jati + Kain Katun", wood_type="Jati",
        warna="Krem, Cokelat, Abu-abu, Hitam", finishing="Natural Oil",
        berat="8.5", dimensi_panjang=52, dimensi_lebar=55, dimensi_tinggi=88,
        kapasitas_beban=120, garansi="5 tahun rangka",
        kondisi="baru", perakitan="sudah",
        pelengkap="Meja Ardea", relasi_tipe="Pelengkap",
        tags="minimalis,jati,modern", status="aktif",
    ),
    _seed_row(
        name="Meja Ardea", sku="IMJ-0002", category="meja",
        subcategory="Meja Makan", brand="Ine Mebel Jepara",
        description="Meja makan solid kayu jati 6 cm dengan kaki silang. Muat 6 orang. Finishing natural oil semi-gloss yang menonjolkan serat kayu alami.",
        price=6200000, discount_price=None, stock=12,
        img="img/produk-wa-02.jpeg",
        img_alt="Meja makan kayu solid minimalis",
        material="Kayu Jati Solid", wood_type="Jati",
        warna="Natural Teak, Walnut", finishing="Natural Matte",
        berat="45", dimensi_panjang=180, dimensi_lebar=90, dimensi_tinggi=75,
        kapasitas_beban=200, garansi="5 tahun rangka",
        kondisi="baru", perakitan="perlu",
        pelengkap="Kursi Tamarind", relasi_tipe="Pasangan",
        tags="makan,jati,solid", status="aktif",
    ),
    _seed_row(
        name="Sofa Havana", sku="IMJ-0003", category="sofa",
        subcategory="Sofa 3 Dudukan", brand="Ine Mebel Jepara",
        description="Sofa tiga dudukan bergaya Scandinavian dengan kaki kayu jati dan pelapis beludru premium. Rangka kayu solid, busa rebonded 25D, nyaman untuk keluarga.",
        price=12500000, discount_price=11200000, stock=5,
        img="img/produk-sofa-klasik-marun.jpeg",
        img_alt="Sofa beludru dengan kaki kayu jati",
        material="Pinus + Beludru", wood_type="Jati",
        warna="Emerald, Navy, Beige, Charcoal", finishing="Walnut",
        berat="35", dimensi_panjang=210, dimensi_lebar=85, dimensi_tinggi=80,
        kapasitas_beban=250, garansi="3 tahun rangka",
        kondisi="baru", perakitan="sudah",
        pelengkap="Meja Kopi Minimalis", relasi_tipe="Pelengkap",
        tags="beludru,scandinavian,premium", status="aktif",
    ),
    _seed_row(
        name="Lemari Pakaian Jepara Classic", sku="IMJ-0004", category="lemari",
        subcategory="Lemari 2 Pintu", brand="Ine Mebel Jepara",
        description="Lemari pakaian 2 pintu dengan ukiran khas Jepara. Dilengkapi 3 laci dan gantungan baju. Cocok untuk kamar utama dengan sentuhan klasik.",
        price=8750000, discount_price=None, stock=8,
        img="img/produk-lemari-2-pintu-rotan.jpeg",
        img_alt="Lemari pakaian kayu jati dengan ukiran",
        material="Kayu Jati Solid", wood_type="Jati",
        warna="Cokelat Tua, Natural", finishing="Duco Glossy",
        berat="62", dimensi_panjang=120, dimensi_lebar=55, dimensi_tinggi=200,
        kapasitas_beban=None, garansi="5 tahun",
        kondisi="baru", perakitan="perlu",
        pelengkap="", relasi_tipe="",
        tags="ukir,classic,jati", status="aktif",
    ),
    _seed_row(
        name="Meja Kerja Minimalis Kayu", sku="IMJ-0005", category="meja",
        subcategory="Meja Kerja", brand="Ine Mebel Jepara",
        description="Meja kerja minimalis dengan 2 laci penyimpanan. Cocok untuk WFH dan kantor home office dengan desain bersih dan modern.",
        price=2750000, discount_price=2350000, stock=30,
        img="img/produk-wa-01.jpeg",
        img_alt="Meja kerja kayu minimalis dengan laci",
        material="Kayu Mahoni", wood_type="Mahoni",
        warna="Natural, Cokelat", finishing="Matte",
        berat="22", dimensi_panjang=120, dimensi_lebar=60, dimensi_tinggi=75,
        kapasitas_beban=60, garansi="2 tahun",
        kondisi="baru", perakitan="perlu",
        pelengkap="Kursi Kerja Ergo", relasi_tipe="Pasangan",
        tags="wfh,minimalis,mahoni", status="aktif",
    ),
    _seed_row(
        name="Kursi Kerja Ergo", sku="IMJ-0006", category="kursi",
        subcategory="Kursi Kerja", brand="Ine Mebel Jepara",
        description="Kursi kerja dengan sandaran ergonomis, bantalan memory foam, dan rangka kayu solid. Nyaman untuk kerja berjam-jam.",
        price=3200000, discount_price=None, stock=18,
        img="img/produk-wa-03.jpeg",
        img_alt="Kursi kerja ergonomis kayu solid",
        material="Kayu + Memory Foam", wood_type="Jati",
        warna="Hitam, Cokelat", finishing="Natural",
        berat="14", dimensi_panjang=60, dimensi_lebar=60, dimensi_tinggi=100,
        kapasitas_beban=130, garansi="2 tahun",
        kondisi="baru", perakitan="perlu",
        pelengkap="Meja Kerja Minimalis Kayu", relasi_tipe="Pasangan",
        tags="ergonomis,kantor,modern", status="aktif",
    ),
    _seed_row(
        name="Meja Kopi Minimalis", sku="IMJ-0007", category="meja",
        subcategory="Meja Kopi", brand="Ine Mebel Jepara",
        description="Meja kopi minimalis dengan top marble dan kaki kayu jati. Cocok untuk ruang tamu modern dan menjadi focal point ruangan.",
        price=4200000, discount_price=3850000, stock=15,
        img="img/produk-wa-02.jpeg",
        img_alt="Meja kopi marble dengan kaki kayu jati",
        material="Marble + Jati", wood_type="Jati",
        warna="Putih Marble + Natural", finishing="Glossy",
        berat="28", dimensi_panjang=100, dimensi_lebar=60, dimensi_tinggi=45,
        kapasitas_beban=80, garansi="3 tahun",
        kondisi="baru", perakitan="perlu",
        pelengkap="Sofa Havana", relasi_tipe="Pelengkap",
        tags="marble,minimalis,modern", status="aktif",
    ),
    _seed_row(
        name="Lemari Buku Terbuka", sku="IMJ-0008", category="lemari",
        subcategory="Rak Buku", brand="Ine Mebel Jepara",
        description="Rak buku terbuka 5 tingkat dari kayu jati. Desain minimalis untuk ruang baca dan kantor dengan tampilan rapi.",
        price=3450000, discount_price=None, stock=22,
        img="img/produk-lemari-3-pintu-rotan.jpeg",
        img_alt="Rak buku terbuka kayu jati 5 tingkat",
        material="Kayu Jati", wood_type="Jati",
        warna="Natural", finishing="Matte",
        berat="32", dimensi_panjang=80, dimensi_lebar=35, dimensi_tinggi=180,
        kapasitas_beban=90, garansi="3 tahun",
        kondisi="baru", perakitan="perlu",
        pelengkap="", relasi_tipe="",
        tags="rak,buku,minimalis", status="aktif",
    ),
    _seed_row(
        name="Sofa L Minimalis", sku="IMJ-0009", category="sofa",
        subcategory="Sofa L", brand="Ine Mebel Jepara",
        description="Sofa L dengan bahan kain linen premium. Rangka kayu solid, busa high-density. Ideal untuk ruang keluarga besar.",
        price=15800000, discount_price=14200000, stock=3,
        img="img/produk-sofa-klasik-marun.jpeg",
        img_alt="Sofa L kain linen premium ruang keluarga",
        material="Linen + Kayu Solid", wood_type="Jati",
        warna="Beige, Abu-abu", finishing="Natural",
        berat="58", dimensi_panjang=280, dimensi_lebar=180, dimensi_tinggi=80,
        kapasitas_beban=400, garansi="3 tahun",
        kondisi="baru", perakitan="perlu",
        pelengkap="Meja Kopi Minimalis", relasi_tipe="Pelengkap",
        tags="L-shape,linen,keluarga", status="aktif",
    ),
    _seed_row(
        name="Kursi Bar Stool Industrial", sku="IMJ-0010", category="kursi",
        subcategory="Bar Stool", brand="Ine Mebel Jepara",
        description="Kursi bar tinggi dengan kombinasi kayu dan besi industrial. Tinggi dudukan 75 cm, cocok untuk bar counter atau cafe.",
        price=1850000, discount_price=None, stock=40,
        img="img/produk-wa-04.jpeg",
        img_alt="Kursi bar stool industrial kayu besi",
        material="Kayu + Besi", wood_type="Trembesi",
        warna="Cokelat + Hitam", finishing="Matte",
        berat="7", dimensi_panjang=40, dimensi_lebar=40, dimensi_tinggi=75,
        kapasitas_beban=100, garansi="1 tahun",
        kondisi="baru", perakitan="perlu",
        pelengkap="", relasi_tipe="",
        tags="industrial,bar,cafe", status="aktif",
    ),
    _seed_row(
        name="Nakas Samping Tempat Tidur", sku="IMJ-0011", category="lemari",
        subcategory="Nakas", brand="Ine Mebel Jepara",
        description="Nakas samping tempat tidur dengan 2 laci. Desain Scandinavian minimalis, cocok untuk kamar tidur modern.",
        price=1450000, discount_price=1250000, stock=35,
        img="img/produk-wa-06.jpeg",
        img_alt="Nakas samping tempat tidur kayu minimalis",
        material="Kayu Jati", wood_type="Jati",
        warna="Natural, White", finishing="Matte",
        berat="12", dimensi_panjang=45, dimensi_lebar=40, dimensi_tinggi=55,
        kapasitas_beban=30, garansi="2 tahun",
        kondisi="baru", perakitan="perlu",
        pelengkap="", relasi_tipe="",
        tags="nakas,kamar,minimalis", status="aktif",
    ),
    _seed_row(
        name="Meja Rias Vintage", sku="IMJ-0012", category="meja",
        subcategory="Meja Rias", brand="Ine Mebel Jepara",
        description="Meja rias vintage dengan cermin besar dan 5 laci penyimpanan. Ukiran tangan khas Jepara, sentuhan klasik elegan.",
        price=6800000, discount_price=None, stock=0,
        img="img/produk-lemari-3-pintu-rotan.jpeg",
        img_alt="Meja rias vintage dengan cermin dan ukiran",
        material="Kayu Jati + Cermin", wood_type="Jati",
        warna="Cokelat Tua", finishing="Duco Glossy",
        berat="38", dimensi_panjang=120, dimensi_lebar=45, dimensi_tinggi=150,
        kapasitas_beban=None, garansi="3 tahun",
        kondisi="baru", perakitan="perlu",
        pelengkap="", relasi_tipe="",
        tags="rias,vintage,ukir", status="nonaktif",
    ),
]


CREATE_TABLE_SQL = """
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


INSERT_SQL = """
INSERT INTO products
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
   %(garansi)s, %(kondisi)s, %(perakitan)s, %(pelengkap)s, %(relasi_tipe)s, %(tags)s, %(status)s)
"""


def main() -> int:
    print("=" * 60)
    print("  Ine Mebel Jepara - Inisialisasi Database (Laragon)")
    print("=" * 60)
    print(f"  Host : {config.DB_HOST}:{config.DB_PORT}")
    print(f"  User : {config.DB_USER}")
    print(f"  DB   : {config.DB_NAME}")
    print("=" * 60)
    print()

    try:
        conn = pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASS,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=5,
        )
    except pymysql.MySQLError as exc:
        print("GAGAL terhubung ke MySQL Laragon:")
        print(f"  {exc}")
        print()
        print("Solusi:")
        print("  1. Buka aplikasi Laragon")
        print("  2. Klik tombol 'Start All'")
        print("  3. Pastikan ikon MySQL di Laragon berwarna hijau")
        print("  4. Jalankan ulang: python db-init.py")
        return 1

    with conn:
        with conn.cursor() as cur:
            print(f"[1/3] Membuat database `{config.DB_NAME}` ...")
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cur.execute(f"USE `{config.DB_NAME}`")
            print("      OK")

            print("[2/3] Membuat tabel products ...")
            cur.execute(CREATE_TABLE_SQL)
            print("      OK")

            print("[3/3] Mengisi produk awal ...")
            cur.execute("SELECT COUNT(*) FROM products")
            count = cur.fetchone()[0]
            if count > 0:
                print(f"      Sudah ada {count} produk - seeding dilewati.")
            else:
                for row in SEED:
                    cur.execute(INSERT_SQL, row)
                print(f"      {len(SEED)} produk awal dimasukkan.")

    print()
    print("=" * 60)
    print(f"Database siap: {config.DB_NAME} @ {config.DB_HOST}:{config.DB_PORT}")
    print("=" * 60)
    print()
    print("Langkah berikutnya:")
    print("  1. python app.py")
    print("  2. Buka http://127.0.0.1:5000/")
    print("  3. Buka http://127.0.0.1:5000/admin.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())