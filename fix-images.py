"""
Perbaikan gambar produk: pastikan setiap produk punya file gambar lokal (img/).
Jalankan sekali: python fix-images.py
"""

import os

import config
import pymysql

DEFAULT_IMG = "img/produk-sofa-klasik-marun.jpeg"


def main():
    conn = pymysql.connect(
        host=config.DB_HOST, port=config.DB_PORT,
        user=config.DB_USER, password=config.DB_PASS,
        database=config.DB_NAME, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor, autocommit=True,
    )
    with conn, conn.cursor() as cur:
        # 1) Gambar yang masih mengarah ke Unsplash (foto di luar repo) -> default.
        cur.execute(
            "UPDATE products SET img = %s WHERE img LIKE '%%images.unsplash.com%%'",
            (DEFAULT_IMG,),
        )
        print(f"  sisa unsplash diganti default: {cur.rowcount} baris")

        # 2) Gambar yang menunjuk file hilang -> pakai gambar default.
        base = os.path.dirname(os.path.abspath(__file__))
        cur.execute("SELECT id, sku, img FROM products")
        for row in cur.fetchall():
            path = row["img"] or ""
            if not path.startswith("img/") or os.path.isfile(os.path.join(base, path)):
                continue
            cur.execute(
                "UPDATE products SET img = %s WHERE id = %s",
                (DEFAULT_IMG, row["id"]),
            )
            print(f"  file hilang {row['sku']} ({path}) -> default")

        cur.execute("SELECT COUNT(*) AS n FROM products WHERE img LIKE '%%unsplash%%'")
        print("  sisa baris unsplash:", cur.fetchone()["n"])


if __name__ == "__main__":
    main()

