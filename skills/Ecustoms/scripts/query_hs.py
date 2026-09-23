#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Công cụ tra cứu HS độc lập (tự xây dựng, không dựa trên nội dung của
bất kỳ skill bên thứ ba nào). Dữ liệu nền là văn bản pháp luật công
khai do bạn tự nhập qua các script import_*.py trong cùng thư mục.

Cách dùng:
    python query_hs.py code 72287010
    python query_hs.py search "thep hinh"
    python query_hs.py chapter 72
    python query_hs.py heading 7228
    python query_hs.py gri
    python query_hs.py gri 3
    python query_hs.py refs
    python query_hs.py refs "chong ban pha gia"
    python query_hs.py case "thep hinh H"
"""
import sys
import io
import os
import json
import argparse
import re
import unicodedata

# Ép output UTF-8 để tránh lỗi mã hóa trên Windows console (cp1252/cp437)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
REFS = os.path.join(BASE, "references")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ilms_api  # noqa: E402  — có ILMS_URL thì code/search/chapter/gri/refs/vanban đọc kho ILMSv2


def _ma(c):
    return f"{c[:4]}.{c[4:6]}.{c[6:]}" if len(c) == 8 else c


def api_code(code):
    code_n = re.sub(r"\D", "", code)
    try:
        r = ilms_api.get(f"/hs/{code_n}")
    except SystemExit as e:
        if "404" not in str(e):
            raise
        ds = ilms_api.get("/hs", q=code_n[:6], limit=50)["ket_qua"]
        print(f"Không có mã 8 số '{code_n}' trong Biểu thuế ILMS.")
        if ds:
            print(f"Các mã con thực sự tồn tại với tiền tố {code_n[:6]} (prefix_6):")
            for x in ds:
                print(f"  {x['code']}  {x['desc_vn'][:80]}")
        return
    print(f"Mã tra: {r['code']} — khớp kiểu: exact (nguồn: ILMS, Biểu thuế {r['bieu_thue_nam']})")
    print(f"Mô tả VN: {r['desc_vn']}")
    if r.get("desc_en"):
        print(f"Mô tả EN: {r['desc_en']}")
    print(f"{r.get('section') or ''}, Chương {r['chapter']} | Đơn vị: {r.get('unit') or ''}")
    print(f"Thuế NK thông thường: {r.get('thue_tt') or ''} | MFN: {r.get('mfn') or ''} | VAT: {r.get('vat') or ''}")
    if r.get("fta"):
        print("FTA: " + ", ".join(f"{k}={v}" for k, v in r["fta"].items()))
    if r.get("chinh_sach"):
        print(f"Chính sách mặt hàng: {r['chinh_sach']}")
    if r.get("van_ban_lien_quan"):
        print("Văn bản trong kho nhắc tới mã này:")
        for v in r["van_ban_lien_quan"]:
            print(f"  [{v['id']}] {v['so_hieu']} — {v['ten']}")


def api_search(keyword):
    ds = ilms_api.get("/hs", q=keyword, limit=20)["ket_qua"]
    if not ds:
        print(f"Không tìm thấy kết quả cho '{keyword}'. (Chỉ là gợi ý từ khóa — luôn đọc Chú giải trước khi kết luận.)")
        return
    print(f"Kết quả cho '{keyword}' (CHỈ LÀ GỢI Ý — luôn đọc Chú giải trước khi kết luận):")
    for x in ds:
        print(f"  {x['code']}  MFN={x.get('mfn') or ''}  {x['desc_vn'][:90]}")


def api_chapter(num):
    r = ilms_api.get(f"/chuong/{int(num)}")
    print(f"=== Chú giải Chương {int(num)} ===")
    print(r["noi_dung"])


def api_gri(so=None):
    for r in ilms_api.get("/gri"):
        if so and str(r["so"]) != str(so):
            continue
        print(f"--- {r['ten']} ---")
        print(r["noi_dung"])
        print()


def api_refs(keyword=None, category=None):
    ds = ilms_api.get("/van-ban", q=keyword or "", loai=category or "", limit=100)["ket_qua"]
    if not ds:
        print("Không có văn bản nào khớp trong kho ILMS.")
        return
    for v in ds:
        print(f"[{v['id']}] {v['so_hieu']} ({v['loai']}, {v.get('ngay_ban_hanh') or '—'}) — {v['ten']}")
        if v.get("doan_khop"):
            print("    ..." + re.sub(r"</?b>", "**", v["doan_khop"]).replace(chr(10), " ") + "...")
    print(chr(10) + "Đọc toàn văn: query_hs.py vanban <id>")


def api_vanban(ma):
    if not str(ma).isdigit():
        ds = ilms_api.get("/van-ban", q=ma, limit=1)["ket_qua"]
        if not ds:
            raise SystemExit(f"Không có văn bản '{ma}' trong kho ILMS.")
        ma = ds[0]["id"]
    v = ilms_api.get(f"/van-ban/{ma}")
    print(f"=== {v['so_hieu']} — {v['ten']} ===")
    print(f"Loại: {v['loai']} | Ban hành: {v.get('ngay_ban_hanh') or '—'} | Cơ quan: {v.get('co_quan') or '—'}")
    if v.get("ma_hs"):
        print("Mã HS nhắc tới: " + ", ".join(v["ma_hs"]))
    print()
    print(v["noi_dung"])


def load_json(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def strip_accents(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def cmd_code(code):
    tree = load_json("hs_tree.json")
    codes = tree.get("codes", {})
    code_n = re.sub(r"\D", "", code)
    if code_n in codes:
        entry = codes[code_n]
        match_type = "exact"
    else:
        # thử khớp theo tiền tố 6 số / 4 số nếu chưa có mã 8 số cụ thể
        entry = None
        match_type = None
        for prefix_len, label in ((6, "prefix_6"), (4, "prefix_4")):
            prefix = code_n[:prefix_len]
            candidates = [c for c in codes if c.startswith(prefix)]
            if candidates:
                print(f"Không có mã 8 số '{code_n}' trong dữ liệu đã nhập.")
                print(f"Các mã con thực sự tồn tại với tiền tố {prefix} ({label}):")
                for c in sorted(candidates):
                    print(f"  {c}  {codes[c].get('desc_vn','')[:80]}")
                return
        if entry is None:
            print(f"Không tìm thấy mã {code_n} trong dữ liệu đã nhập.")
            print("Dữ liệu Biểu thuế có thể chưa được nạp — chạy scripts/import_tariff.py trước.")
            return
    print(f"Mã tra: {code_n} — khớp kiểu: {match_type}")
    print(f"Mô tả VN: {entry.get('desc_vn','')}")
    if entry.get("desc_en"):
        print(f"Mô tả EN: {entry.get('desc_en')}")
    print(f"{entry.get('section','')}, Chương {entry.get('chapter','')} | Đơn vị: {entry.get('unit','')}")
    print(f"Thuế NK thông thường: {entry.get('thue_nk_thong_thuong','')} | MFN: {entry.get('mfn','')} | VAT: {entry.get('vat','')}")
    fta = entry.get("fta", {})
    if fta:
        print("FTA: " + ", ".join(f"{k}={v}" for k, v in fta.items()))
    if entry.get("chinh_sach"):
        print(f"Chính sách mặt hàng: {entry.get('chinh_sach')}")


def cmd_search(keyword):
    tree = load_json("hs_tree.json")
    codes = tree.get("codes", {})
    kw = strip_accents(keyword)
    results = []
    for code, entry in codes.items():
        text = strip_accents(entry.get("desc_vn", "") + " " + entry.get("desc_en", ""))
        if kw in text:
            results.append((code, entry))
    if not results:
        print(f"Không tìm thấy kết quả cho '{keyword}'. (Chỉ là gợi ý từ khóa — luôn đọc Chú giải trước khi kết luận.)")
        return
    print(f"Kết quả cho '{keyword}' (CHỈ LÀ GỢI Ý — luôn đọc Chú giải trước khi kết luận):")
    for code, entry in results[:20]:
        print(f"  {code}  MFN={entry.get('mfn','')}  {entry.get('desc_vn','')[:90]}")


def cmd_chapter(num):
    notes = load_json("chapter_notes.json").get("chapters", {})
    key = str(int(num))
    if key not in notes:
        print(f"Chưa có dữ liệu Chú giải Chương {key}. Nhập qua import_notes.py.")
        return
    print(f"=== Chú giải Chương {key} ===")
    print(notes[key])


def cmd_heading(num):
    notes = load_json("heading_notes.json").get("headings", {})
    key = re.sub(r"\D", "", str(num))[:4]
    if key not in notes:
        print(f"Chưa có dữ liệu Chú giải nhóm {key}. Nhập qua import_notes.py.")
        return
    print(f"=== Chú giải nhóm {key} ===")
    print(notes[key])


def cmd_gri(so=None):
    data = load_json("gri_rules.json")
    rules = data.get("rules", [])
    if so:
        rules = [r for r in rules if str(r.get("so")) == str(so)]
    for r in rules:
        print(f"--- {r.get('ten')} ---")
        print(r.get("noi_dung"))
        print()


def find_ref_files(category=None):
    base = os.path.join(REFS, category) if category else REFS
    if not os.path.isdir(base):
        return []
    result = []
    for root, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith((".txt", ".md")) and not f.startswith("_"):
                full = os.path.join(root, f)
                rel = os.path.relpath(full, REFS)
                result.append((rel, full))
    return sorted(result)


def cmd_refs(keyword=None, category=None):
    files = find_ref_files(category)
    if not files:
        print("Chưa có văn bản tham khảo nào (trong danh mục đã chọn). Dùng scripts/add_reference.py để thêm.")
        return
    if not keyword:
        print("Danh sách văn bản tham khảo:")
        for rel, _full in files:
            print(f"  {rel}")
        return
    kw = strip_accents(keyword)
    found_any = False
    for rel, full in files:
        with open(full, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if kw in strip_accents(content):
            found_any = True
            print(f"=== Khớp trong: {rel} ===")
            # in đoạn ngữ cảnh quanh từ khóa đầu tiên
            idx = strip_accents(content).find(kw)
            start = max(0, idx - 300)
            end = min(len(content), idx + 500)
            print("..." + content[start:end] + "...")
            print()
    if not found_any:
        print(f"Không tìm thấy '{keyword}' trong các văn bản tham khảo hiện có.")


def cmd_case(keyword=None):
    path = os.path.join(DATA, "case_notes.md")
    if not os.path.exists(path):
        print("Chưa có file case_notes.md.")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if not keyword:
        print(content)
        return
    kw = strip_accents(keyword)
    blocks = content.split("\n## ")
    found = False
    for b in blocks:
        if kw in strip_accents(b):
            found = True
            print("## " + b.strip())
            print()
    if not found:
        print(f"Không có case nào khớp '{keyword}' trong case_notes.md.")


def main():
    p = argparse.ArgumentParser(description="Công cụ tra cứu HS độc lập")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("code")
    sp.add_argument("code")

    sp = sub.add_parser("search")
    sp.add_argument("keyword")

    sp = sub.add_parser("chapter")
    sp.add_argument("num")

    sp = sub.add_parser("heading")
    sp.add_argument("num")

    sp = sub.add_parser("gri")
    sp.add_argument("so", nargs="?")

    sp = sub.add_parser("refs")
    sp.add_argument("keyword", nargs="?")
    sp.add_argument("--category", default=None, help="Giới hạn tra trong 1 danh mục (vd chinh_sach_phap_luat, cbpg_pvtm)")

    sp = sub.add_parser("case")
    sp.add_argument("keyword", nargs="?")

    sp = sub.add_parser("vanban", help="Đọc toàn văn 1 văn bản trong kho ILMS (id hoặc số hiệu)")
    sp.add_argument("ma")

    args = p.parse_args()

    if ilms_api.bat():
        chuyen = {"code": lambda: api_code(args.code), "search": lambda: api_search(args.keyword),
                  "chapter": lambda: api_chapter(args.num), "gri": lambda: api_gri(args.so),
                  "refs": lambda: api_refs(args.keyword, args.category), "vanban": lambda: api_vanban(args.ma)}
        if args.cmd in chuyen:
            return chuyen[args.cmd]()
    elif args.cmd == "vanban":
        raise SystemExit("Lệnh vanban cần ILMS_URL (đọc kho văn bản của ILMSv2).")

    if args.cmd == "code":
        cmd_code(args.code)
    elif args.cmd == "search":
        cmd_search(args.keyword)
    elif args.cmd == "chapter":
        cmd_chapter(args.num)
    elif args.cmd == "heading":
        cmd_heading(args.num)
    elif args.cmd == "gri":
        cmd_gri(args.so)
    elif args.cmd == "refs":
        cmd_refs(args.keyword, args.category)
    elif args.cmd == "case":
        cmd_case(args.keyword)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
