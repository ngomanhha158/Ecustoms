# -*- coding: utf-8 -*-
"""Nạp văn bản dạng PDF/ảnh SCAN vào kho ILMSv2 — OCR, soát, rồi mới lưu.

Hai bước, cố ý tách rời (bài học 22-09: OCR văn bản pháp lý dài dễ sai mã HS/CAS
mà không ai soát):

    python scripts/nap_vb.py ocr  "C:\\...\\QD_1624.pdf" [--doc "C:\\...\\QD_1624.doc"]
        ILMS OCR bằng Gemini (không lưu gì). Ghi bản chờ duyệt vào data/ocr_cho_duyet/
        <tên>.json + <tên>.txt, in số hiệu / tên / ngày, số chỗ 【…】 Gemini tự đánh dấu
        không chắc, cảnh báo. Có --doc (bản Word gốc, kể cả font cũ mất dấu) thì đối
        chiếu MỌI con số (mã HS, %, ngày) giữa bản OCR và bản Word.

    python scripts/nap_vb.py luu <tên> --loai cbpg_pvtm --da-soat
        Sau khi người đọc lại tệp .txt (sửa trực tiếp trong .txt nếu cần — tệp .txt
        là bản được lưu), gửi lên kho ILMS rồi kéo bản chuẩn về máy (dongbo --chi-keo).
        Còn 【…】 trong .txt thì từ chối — soát xong xóa dấu mới lưu.

Cần ILMS_URL + ILMS_USER/ILMS_PASS; lưu cần quyền tracuu.manage.
"""
import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ilms_api  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHO = os.path.join(GOC, "data", "ocr_cho_duyet")
LOAI = ("chinh_sach_phap_luat", "cbpg_pvtm", "cong_van_huong_dan")
_SO = re.compile(r"\d+(?:[.,/]\d+)*")


def _cac_so(t):
    """Mọi số ≥ 2 chữ số, gom '7212.30.14' / '72123014' và '4,28' / '4.28' về một dạng."""
    return collections.Counter(re.sub(r"[.,]", "", s) for s in _SO.findall(t) if len(re.sub(r"\D", "", s)) >= 2)


def doi_chieu_so(noi_dung, tep_doc):
    """Bản Word cũ (font TCVN3/VNI) mất dấu nhưng CÒN NGUYÊN chữ số -> thước đo cho OCR."""
    if not shutil.which("antiword"):
        print("  (bỏ qua đối chiếu số: máy không có antiword)")
        return
    doc = subprocess.run(["antiword", tep_doc], capture_output=True).stdout.decode("latin-1")
    a, b = _cac_so(noi_dung), _cac_so(doc)
    thua, thieu = a - b, b - a
    print(f"  Đối chiếu số với bản Word: OCR {sum(a.values())} số, Word {sum(b.values())} số")
    if not thua and not thieu:
        print("    Khớp hoàn toàn.")
        return
    if thua:
        print(f"    OCR có mà Word không (nghi đọc sai, hoặc dấu chữ ký số / số chú thích): {dict(thua)}")
    if thieu:
        print(f"    Word có mà OCR không (nghi bỏ sót): {dict(thieu)}")


def cmd_ocr(duong_dan, tep_doc=None):
    d = ilms_api.ocr_van_ban(duong_dan)
    os.makedirs(CHO, exist_ok=True)
    ten = os.path.splitext(os.path.basename(duong_dan))[0]
    with open(os.path.join(CHO, ten + ".json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    with open(os.path.join(CHO, ten + ".txt"), "w", encoding="utf-8") as f:
        f.write(d.get("noi_dung", ""))
    nd = d.get("noi_dung", "")
    print(f"== {ten}")
    print(f"  Số hiệu: {d.get('so_hieu') or '—'} · Ngày: {d.get('ngay_ban_hanh') or '—'} · Cơ quan: {d.get('co_quan') or '—'}")
    print(f"  Tên: {d.get('ten') or '—'}")
    print(f"  {len(nd)} ký tự · {nd.count('【')} chỗ Gemini đánh dấu không chắc 【…】")
    for c in d.get("canh_bao") or []:
        print(f"  ! {c}")
    if tep_doc:
        doi_chieu_so(nd, tep_doc)
    print(f"  Bản chờ duyệt: {os.path.join(CHO, ten + '.txt')}")
    print(f"  Soát xong: python scripts/nap_vb.py luu {ten} --loai <loại> --da-soat")


def cmd_luu(ten, loai, da_soat, so_hieu=None, tieu_de=None, ngay=None):
    if not da_soat:
        raise SystemExit("Thêm --da-soat để xác nhận đã đọc lại bản OCR (tệp .txt) trước khi lưu vào kho.")
    if loai not in LOAI:
        raise SystemExit(f"--loai phải thuộc {LOAI}")
    if not os.path.exists(os.path.join(CHO, ten + ".json")):
        co = sorted(x[:-5] for x in os.listdir(CHO) if x.endswith(".json")) if os.path.isdir(CHO) else []
        raise SystemExit(f"Không có bản chờ duyệt '{ten}'. Đang chờ: {', '.join(co) or 'không có'} — chạy `nap_vb.py ocr` trước.")
    with open(os.path.join(CHO, ten + ".json"), encoding="utf-8") as f:
        d = json.load(f)
    with open(os.path.join(CHO, ten + ".txt"), encoding="utf-8") as f:
        nd = f.read()
    if "【" in nd:
        raise SystemExit(f"Bản .txt còn {nd.count('【')} chỗ 【…】 — soát với bản gốc, sửa và xóa dấu rồi lưu lại.")
    meta = {"so_hieu": so_hieu or d.get("so_hieu"), "ten": tieu_de or d.get("ten"), "loai": loai,
            "ngay_ban_hanh": ngay or d.get("ngay_ban_hanh"), "co_quan": (d.get("co_quan") or "").title()}
    if not (meta["so_hieu"] and meta["ten"]):
        raise SystemExit("OCR không đọc được số hiệu / tên — truyền --so-hieu và --ten.")
    r = ilms_api.them_van_ban(meta, nd)
    print(f"Đã lưu vào kho ILMS: [{r['id']}] {r['so_hieu']} · {r['so_ma_hs']} mã HS trích được")
    for tep in (ten + ".json", ten + ".txt"):
        os.remove(os.path.join(CHO, tep))
    import query_hs
    query_hs.api_dongbo(chi_keo=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("ocr", help="OCR một PDF/ảnh scan qua ILMS, ghi bản chờ duyệt")
    sp.add_argument("tep")
    sp.add_argument("--doc", help="Bản Word gốc để đối chiếu mọi con số")
    sp = sub.add_parser("luu", help="Lưu bản đã soát vào kho ILMS")
    sp.add_argument("ten", help="Tên bản chờ duyệt (tên tệp PDF, bỏ đuôi)")
    sp.add_argument("--loai", required=True, help=" | ".join(LOAI))
    sp.add_argument("--da-soat", action="store_true", help="Xác nhận đã đọc lại bản .txt")
    sp.add_argument("--so-hieu")
    sp.add_argument("--ten-vb", dest="tieu_de")
    sp.add_argument("--ngay", help="YYYY-MM-DD")
    a = p.parse_args()
    if not ilms_api.bat():
        raise SystemExit("Cần ILMS_URL + ILMS_USER/ILMS_PASS.")
    if a.cmd == "ocr":
        cmd_ocr(a.tep, a.doc)
    else:
        cmd_luu(a.ten, a.loai, a.da_soat, a.so_hieu, a.tieu_de, a.ngay)


if __name__ == "__main__":
    main()
