"""Cek koneksi MySQL Laragon & status database."""
import sys
import pymysql
import config


def main():
    print("=" * 60)
    print("  Cek Koneksi MySQL Laragon")
    print("=" * 60)
    print(f"  Host : {config.DB_HOST}:{config.DB_PORT}")
    print(f"  User : {config.DB_USER}")
    print(f"  DB   : {config.DB_NAME}")
    print("-" * 60)

    try:
        conn = pymysql.connect(
            host=config.DB_HOST, port=config.DB_PORT,
            user=config.DB_USER, password=config.DB_PASS,
            connect_timeout=5,
        )
    except pymysql.MySQLError as exc:
        print(f"  GAGAL koneksi ke MySQL: {exc}")
        print()
        print("  Pastikan Laragon sudah 'Start All'.")
        return 1

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            ver = cur.fetchone()[0]
            print(f"  OK — MySQL terhubung. Versi: {ver}")

            cur.execute(f"SHOW DATABASES LIKE '{config.DB_NAME}'")
            if not cur.fetchone():
                print(f"  Database '{config.DB_NAME}' belum ada.")
                print(f"     Jalankan: python db-init.py")
                return 1
            print(f"  OK — Database '{config.DB_NAME}' ada.")

            cur.execute(f"USE `{config.DB_NAME}`")
            cur.execute("SHOW TABLES LIKE 'products'")
            if not cur.fetchone():
                print("  Tabel 'products' belum ada.")
                print("     Jalankan: python db-init.py")
                return 1
            print("  OK — Tabel 'products' ada.")

            cur.execute("SELECT COUNT(*) FROM products")
            total = cur.fetchone()[0]
            cur.execute("SELECT status, COUNT(*) FROM products GROUP BY status")
            by_status = cur.fetchall()
            print(f"  OK — Total produk: {total}")
            for status, count in by_status:
                print(f"       - {status}: {count}")

    print("=" * 60)
    print("  Semua OK. Jalankan: python app.py")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())