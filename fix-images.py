"""
Perbaikan gambar produk: ganti URL Unsplash dengan foto milik sendiri (img/).
Jalankan sekali: python fix-images.py
"""

import config
import pymysql

# Mapping SKU -> file gambar lokal
IMG_MAP = {
    "IMJ-0001": "img/produk-wa-03.jpeg",
    "IMJ-0002": "img/produk-wa-02.jpeg",
    "IMJ-0005": "img/produk-wa-01.jpeg",
    "IMJ-0006": "img/produk-wa-03.jpeg",
    "IMJ-0007": "img/produk-wa-02.jpeg",
    "IMJ-0009": "img/produk-sofa-klasik-marun.jpeg",
    "IMJ-0010": "img/produk-wa-04.jpeg",
}


def main():
    conn = pymysql.connect(
        host=config.DB_HOST, port=config.DB_PORT,
        user=config.DB_USER, password=config.DB_PASS,
        database=config.DB_NAME, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor, autocommit=True,
    )
    with conn, conn.cursor() as cur:
        # 1) Ganti SKU yang diketahui
        for sku, path in IMG_MAP.items():
            cur.execute("UPDATE products SET img = %s WHERE sku = %s", (path, sku))
            print(f"  {sku} -> {path} ({cur.rowcount} baris)")

        # 2) Sisa yang masih mengarah ke Unsplash (foto di luar repo).
        cur.execute(
            "UPDATE products SET img = 'img/produk-sofa-klasik-marun.jpeg' "
            "WHERE img LIKE '%%images.unsplash.com%%'"
        )
        print(f"  sisa unsplash diganti default: {cur.rowcount} baris")

        # 3) Gambar yang menunjuk file hilang -> pakai gambar default.
        import os
        base = os.path.dirname(os.path.abspath(__file__))
        cur.execute("SELECT id, sku, img FROM products")
        for row in cur.fetchall():
            path = row["img"] or ""
            if path.startswith("img/") and not os.path.isfile(os.path.join(base, path)):
                cur.execute(
                    "UPDATE products SET img = 'img/produk-sofa-klasik-marun.jpeg' WHERE id = %s",
                    (row["id"],),
                )
                print(f"  file hilang {row['sku']} ({path}) -> default")

        cur.execute("SELECT COUNT(*) AS n FROM products WHERE img LIKE '%%unsplash%%'")
        print("  sisa baris unsplash:", cur.fetchone()["n"])


if __name__ == "__main__":
    main()
