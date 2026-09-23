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
import urllib.parse
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
    pv = [v for v in r.get("pvtm", []) if v["dang_ap"]]
    if pv:
        print("!!! ĐANG BỊ ÁP THUẾ PHÒNG VỆ THƯƠNG MẠI:")
        for v in pv:
            print(f"  [{v['ma_vu_viec']}] {v['ten_hang']} — {v['so_hieu']}")
        print(f"  Tính mức cho lô: query_hs.py thue {r['code']} --nuoc <nước C/O> --nsx <nhà SX> --nxk <nhà XK>")
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


# ---------------------------------------------------------------- phòng vệ thương mại (CBPG)
# Đọc kho PVTM của ILMSv2 (/api/tracuu/pvtm). Luật tính thuế nằm ở MÁY CHỦ
# (services/pvtm.tinh_muc_thue) — skill chỉ hiển thị, không tự tính.
_META = None


def _meta():
    global _META
    if _META is None:
        _META = ilms_api.get("/meta")["pvtm"]
    return _META


def _pt(v):
    return "—" if v is None else f"{float(v):.2f}".replace(".", ",") + "%"


def _trang_thai(v):
    gd = _meta()["giai_doan"].get(v["giai_doan"], v["giai_doan"])
    s = ("ĐANG ÁP · " if v["dang_ap"] else "") + gd
    return s + ("" if v.get("da_doi_chieu") else " · CHƯA ĐỐI CHIẾU BẢN GIẤY")


def api_cbpg(tu_khoa, kieu=None):
    r = ilms_api.get("/pvtm/tim", q=tu_khoa, kieu=kieu or "", limit=50)
    if not r["nhom"]:
        print(f"Không có vụ phòng vệ thương mại nào khớp '{tu_khoa}'.")
        return
    nhan = {k["code"]: k["label"] for k in _meta()["kieu_tim"]}
    for g in r["nhom"]:
        print(f"=== {nhan.get(g['kieu'], g['kieu'])} · {g['tong']} ===")
        for x in g["ket_qua"]:
            vu = f"[{x['ma_vu_viec']}] {x['ten_hang']}" + ("" if x["dang_ap"] else " (hết hiệu lực)")
            if g["kieu"] in ("nha_sx", "cong_ty_tm"):
                muc = "Không áp" if x["khong_ap"] else _pt(x["muc_thue"])
                ten = x["ten"] + (f" — công ty TM của {x['nha_sx']}" if g["kieu"] == "cong_ty_tm" else "")
                print(f"  {ten} ({x['nuoc']}): {muc}  ← {vu}")
            elif g["kieu"] in ("mac_thep", "tieu_chuan"):
                print(f"  LOẠI TRỪ: {x['mac_thep']} theo {x['tieu_chuan']}  ← {vu}")
            elif g["kieu"] == "loai_tru":
                print(f"  KHÔNG THUỘC PHẠM VI: {x['noi_dung']}  ← {vu}")
            elif g["kieu"] == "ma_hs":
                print(f"  {_ma(x['code'])}  ← {vu}")
            elif g["kieu"] == "so_qd":
                print(f"  {x['so_hieu']}  ← {vu}")
            else:
                print(f"  {vu}")
    print(chr(10) + "Xem hồ sơ: query_hs.py vu <mã vụ> · Tính thuế: query_hs.py thue <mã HS> --nuoc KR --nsx ... --nxk ...")


def api_vu(ma):
    v = ilms_api.get(f"/pvtm/vu-viec/{urllib.parse.quote(ma, safe='')}")
    m = _meta()
    print(f"=== [{v['ma_vu_viec']}] {v['ten_hang']} ===")
    print(f"{m['loai'].get(v['loai'], v['loai'])} · {_trang_thai(v)}")
    print(f"Căn cứ: {v.get('so_hieu') or '—'} · Hiệu lực {v['hieu_luc_tu']} → {v.get('hieu_luc_den') or 'chưa ghi'}")
    if v.get("doi_chieu_ten"):
        print(f"Đối chiếu bản giấy: {v['doi_chieu_ten']} lúc {v['doi_chieu_luc']}")
    print(f"Không nộp C/O: {_pt(v['muc_khong_chung_tu'])}")
    for q in v["quy_cach"]:
        print(f"{q['ten']}: {q['gia_tri']}")
    print(chr(10) + "Mô tả: " + v["mo_ta"])
    print(chr(10) + f"Mã HS ({len(v['ma_hs'])}): " + ", ".join(_ma(c) for c in v["ma_hs"]))
    for n in v["nuoc"] or [{"nuoc": "*", "ten_nuoc": "Mọi xuất xứ", "muc_toan_quoc": v["muc_khong_chung_tu"]}]:
        print(chr(10) + f"--- {n['ten_nuoc']} · mức toàn quốc {_pt(n['muc_toan_quoc'])} ---")
        for s in [x for x in v["nha_sx"] if x["nuoc"] == n["nuoc"]]:
            muc = "Không áp" if s["khong_ap"] else _pt(s["muc_thue"])
            print(f"  {s['ten']}{' [' + s['nhom'] + ']' if s.get('nhom') else ''}: {muc}")
            if s["cong_ty_tm"]:
                print("      công ty TM: " + "; ".join(s["cong_ty_tm"]))
    if v["loai_tru"]:
        print(chr(10) + "--- Loại trừ ---")
        for x in v["loai_tru"]:
            if x["kieu"] == "mac_thep":
                print(f"  Mác {x['mac_thep']} theo {x['tieu_chuan']}")
            else:
                print(f"  {x['noi_dung'] or x.get('ma_hs')}")
    if v.get("ghi_chu"):
        print(chr(10) + "Ghi chú: " + v["ghi_chu"])


def api_thue(code, nuoc=None, nsx=None, nxk=None, mac=None, tc=None):
    r = ilms_api.post("/pvtm/tinh-thue", {"code": code, "nuoc_co": nuoc, "nha_sx": nsx, "nha_xk": nxk,
                                          "mac_thep": mac, "tieu_chuan": tc})
    if not r["vu_viec"]:
        print(f"Mã {_ma(r['code'])}: KHÔNG thuộc vụ phòng vệ thương mại nào đang áp trong kho ILMS.")
        return
    for k in r["vu_viec"]:
        print(f"=== [{k['ma_vu_viec']}] {k['ten_hang']} · {k['so_hieu']} ===")
        for i, b in enumerate(k["cac_buoc"], 1):
            print(f"  {i}. {b['buoc']}: {b['ket_qua']} {'✓' if b['dat'] else '✗'}  ({b['can_cu']})")
        ket = f"BỊ ÁP {_pt(k['muc_thue'])}" if k["ket_luan"] == "ap" else "KHÔNG ÁP"
        print(f"  => {ket}")
        for c in k["canh_bao"]:
            print(f"  ! {c}")


# ---------------------------------------------------------------- đồng bộ kho văn bản với ILMSv2
# ILMS là NGUỒN CHÍNH. Kéo: mọi văn bản ILMS về references/<loai>/ (tra được khi mất mạng).
# Đẩy: văn bản chỉ có trên máy (có dòng [Số hiệu], ILMS chưa có) lên ILMS.
# Tệp định dạng cũ (không có [Số hiệu]) được chuyển vào references/_cu/ để khỏi trùng.
SO_DO = os.path.join(DATA, "ilms_dong_bo.json")


def _doc_dau(noi_dung):
    meta = {}
    for dong in noi_dung.splitlines()[:8]:
        m = re.match(r"\[(Số hiệu|Tiêu đề|Ngày ban hành|Cơ quan)\]\s*(.*)", dong.strip())
        if m:
            meta[m.group(1)] = m.group(2).strip()
    return meta


def _ten_tep(so_hieu, ten):
    goc = strip_accents(f"{so_hieu} {ten}")
    return re.sub(r"[^a-z0-9]+", "_", goc).strip("_")[:60] + ".txt"


def api_dongbo(chi_keo=False):
    import shutil
    ds = ilms_api.get("/van-ban", limit=100)["ket_qua"]
    tren_ilms = {v["so_hieu"]: v for v in ds}
    so_do = {}
    if os.path.exists(SO_DO):
        with open(SO_DO, encoding="utf-8") as f:
            so_do = json.load(f)
    # 1. Đẩy lên: tệp máy có [Số hiệu] mà ILMS chưa có.
    day = 0
    if not chi_keo:
        for rel, full in find_ref_files():
            with open(full, encoding="utf-8", errors="replace") as fh:
                nd = fh.read()
            meta = _doc_dau(nd)
            sh = meta.get("Số hiệu")
            if not sh or sh in tren_ilms or rel in so_do.values():
                continue
            loai = rel.replace("\\", "/").split("/")[0]
            if loai not in ("chinh_sach_phap_luat", "cbpg_pvtm", "cong_van_huong_dan"):
                print(f"  bỏ qua {rel}: nằm ngoài 3 thư mục loại văn bản")
                continue
            than = nd.split("-" * 20, 1)[-1].lstrip("-").strip()
            row = ilms_api.them_van_ban({"so_hieu": sh, "ten": meta.get("Tiêu đề") or sh, "loai": loai,
                                         "ngay_ban_hanh": meta.get("Ngày ban hành"), "co_quan": meta.get("Cơ quan", "")}, than)
            print(f"  ĐẨY LÊN ILMS: {row['so_hieu']}")
            day += 1
        if day:
            tren_ilms = {v["so_hieu"]: v for v in ilms_api.get("/van-ban", limit=100)["ket_qua"]}
    # 2. Dời tệp định dạng cũ (không [Số hiệu]) sang references/_cu/ — nội dung đã có trên ILMS.
    doi = 0
    for rel, full in find_ref_files():
        with open(full, encoding="utf-8", errors="replace") as fh:
            dau = fh.read(2000)
        if "Số hiệu" not in _doc_dau(dau) and rel not in so_do.values():
            dich = os.path.join(REFS, "_cu", rel)
            os.makedirs(os.path.dirname(dich), exist_ok=True)
            shutil.move(full, dich)
            doi += 1
    # 3. Kéo về: ghi đè bản máy bằng bản ILMS (ILMS là nguồn chính); xóa bản kéo cũ của văn bản ILMS đã xóa.
    moi = {}
    for sh, v in tren_ilms.items():
        full = ilms_api.get(f"/van-ban/{v['id']}")
        rel = os.path.join(v["loai"], _ten_tep(sh, v["ten"]))
        path = os.path.join(REFS, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"[Số hiệu] {sh}\n[Tiêu đề] {full['ten']}\n[Ngày ban hành] {full.get('ngay_ban_hanh') or ''}\n"
                    f"[Cơ quan] {full.get('co_quan') or ''}\n" + "-" * 60 + "\n\n" + full["noi_dung"])
        moi[sh] = rel
    xoa = 0
    for sh, rel in so_do.items():
        if sh not in moi and os.path.exists(os.path.join(REFS, rel)):
            os.remove(os.path.join(REFS, rel))
            xoa += 1
    with open(SO_DO, "w", encoding="utf-8") as f:
        json.dump(moi, f, ensure_ascii=False, indent=2)
    print(f"Đồng bộ xong: kéo {len(moi)} văn bản từ ILMS, đẩy {day} lên ILMS, "
          f"dời {doi} tệp định dạng cũ vào references/_cu/, xóa {xoa} bản đã bị xóa trên ILMS.")


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
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith("_")]
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

    sp = sub.add_parser("dongbo", help="Đồng bộ kho văn bản 2 chiều với ILMSv2 (ILMS là nguồn chính)")
    sp.add_argument("--chi-keo", action="store_true", help="Chỉ kéo từ ILMS về, không đẩy lên")

    sp = sub.add_parser("cbpg", help="Tìm vụ CBPG/PVTM theo tên hàng, mã HS, nhà SX, công ty TM, mác thép, tiêu chuẩn, số QĐ")
    sp.add_argument("tu_khoa")
    sp.add_argument("--kieu", default=None, help="mat_hang|ma_hs|nha_sx|cong_ty_tm|mac_thep|tieu_chuan|so_qd|loai_tru")

    sp = sub.add_parser("vu", help="Hồ sơ đủ một vụ CBPG (mã vụ, vd AD19)")
    sp.add_argument("ma")

    sp = sub.add_parser("thue", help="Tính thuế CBPG cho một lô theo thủ tục trong QĐ")
    sp.add_argument("code")
    sp.add_argument("--nuoc", help="Nước trên C/O (ISO-2 hoặc tên); bỏ trống = không có C/O")
    sp.add_argument("--nsx", help="Nhà sản xuất trên giấy chứng nhận chất lượng")
    sp.add_argument("--nxk", help="Nhà xuất khẩu trên hóa đơn")
    sp.add_argument("--mac", help="Mác thép")
    sp.add_argument("--tc", help="Tiêu chuẩn đi kèm mác thép (ghi cả năm)")

    args = p.parse_args()

    if ilms_api.bat():
        chuyen = {"code": lambda: api_code(args.code), "search": lambda: api_search(args.keyword),
                  "chapter": lambda: api_chapter(args.num), "gri": lambda: api_gri(args.so),
                  "refs": lambda: api_refs(args.keyword, args.category), "vanban": lambda: api_vanban(args.ma),
                  "cbpg": lambda: api_cbpg(args.tu_khoa, args.kieu), "dongbo": lambda: api_dongbo(args.chi_keo), "vu": lambda: api_vu(args.ma),
                  "thue": lambda: api_thue(args.code, args.nuoc, args.nsx, args.nxk, args.mac, args.tc)}
        if args.cmd in chuyen:
            return chuyen[args.cmd]()
    elif args.cmd in ("vanban", "cbpg", "vu", "thue", "dongbo"):
        raise SystemExit(f"Lệnh {args.cmd} cần ILMS_URL (đọc kho của ILMSv2).")

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
