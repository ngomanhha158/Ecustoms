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
from datetime import datetime, timezone

# Ép output UTF-8 để tránh lỗi mã hóa trên Windows console (cp1252/cp437)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
REFS = os.path.join(BASE, "references")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ilms_api  # noqa: E402  — CHỈ dùng khi đồng bộ (`dongbo`); tra cứu luôn đọc dữ liệu trên máy
import pvtm_local as pl  # noqa: E402
import hieu_luc as hl  # noqa: E402


def _ma(c):
    return f"{c[:4]}.{c[4:6]}.{c[6:]}" if len(c) == 8 else c


# ---------------------------------------------------------------- phòng vệ thương mại (CBPG)
# Đọc data/pvtm.json trên máy (kéo về bằng `dongbo`). Luật tính thuế: pvtm_local.py
# (bản chép của ILMS, canh lệch bằng kiem_khop.py).
def _pt(v):
    return "—" if v is None else f"{float(v):.2f}".replace(".", ",") + "%"


def _trang_thai(v):
    gd = pl.NHAN_GIAI_DOAN.get(v["giai_doan"], v["giai_doan"])
    s = ("ĐANG ÁP · " if pl.dang_ap(v) else "") + gd
    return s + ("" if v.get("da_doi_chieu") else " · CHƯA ĐỐI CHIẾU BẢN GIẤY")


def _kho():
    kho = pl.doc_kho()
    cu = pl.canh_bao_cu(kho)
    if cu:
        print(cu + chr(10))
    return kho


def cmd_cbpg(tu_khoa, kieu=None):
    nhom = pl.tim(_kho(), tu_khoa, kieu or "")
    if not nhom:
        print(f"Không có vụ phòng vệ thương mại nào khớp '{tu_khoa}'.")
        return
    for g in nhom:
        print(f"=== {pl.NHAN_KIEU_TIM[g['kieu']]} · {g['tong']} ===")
        for x in g["ket_qua"][:50]:
            vu = f"[{x['ma_vu_viec']}] {x['ten_hang']}" + ("" if x["dang_ap"] else " (hết hiệu lực)")
            if g["kieu"] in ("nha_sx", "cong_ty_tm"):
                muc = "Không áp" if x["khong_ap"] else _pt(x["muc_thue"])
                ten = x["ten"] + (f" — công ty TM của {x['nha_sx']}" if g["kieu"] == "cong_ty_tm" else "")
                print(f"  {ten} ({x['nuoc']}): {muc}  ← {vu}")
            elif g["kieu"] in ("mac_thep", "tieu_chuan"):
                print(f"  LOẠI TRỪ: {x['mac_thep']} theo {x['tieu_chuan']}  ← {vu}")
            elif g["kieu"] == "loai_tru":
                print(f"  KHÔNG THUỘC PHẠM VI: {x['noi_dung']}  ← {vu}")
            elif g["kieu"] == "quy_cach":
                print(f"  {x['noi_dung']}  ← {vu}")
            elif g["kieu"] == "ma_hs":
                print(f"  {_ma(x['code'])}  ← {vu}")
            elif g["kieu"] == "so_qd":
                print(f"  {x['so_hieu']}  ← {vu}")
            else:
                print(f"  {vu}")
    print(chr(10) + "Xem hồ sơ: query_hs.py vu <mã vụ> · Tính thuế: query_hs.py thue <mã HS> --nuoc KR --nsx ... --nxk ...")


def cmd_vu(ma):
    kho = _kho()
    v = next((x for x in kho["vu_viec"] if x["ma_vu_viec"].lower() == ma.strip().lower()), None)
    if not v:
        raise SystemExit(f"Không có vụ '{ma}'. Các vụ: " + ", ".join(x["ma_vu_viec"] for x in kho["vu_viec"]))
    print(f"=== [{v['ma_vu_viec']}] {v['ten_hang']} ===")
    print(f"{pl.NHAN_LOAI.get(v['loai'], v['loai'])} · {_trang_thai(v)}")
    print(f"Căn cứ: {v.get('so_hieu') or '—'} · Hiệu lực {v['hieu_luc_tu']} → {v.get('hieu_luc_den') or 'chưa ghi'}")
    if v.get("doi_chieu_ten"):
        print(f"Đối chiếu bản giấy: {v['doi_chieu_ten']} lúc {v['doi_chieu_luc']}")
    for b in v.get("van_ban", []):
        print(f"  Văn bản: {b['so_hieu']} ({b['vai']}, {b.get('ngay_ban_hanh') or '—'}) {b.get('link_goc') or ''}")
    print(f"Không nộp C/O: {_pt(v['muc_khong_chung_tu'])}")
    for q in v["quy_cach"]:
        print(f"{q['ten']}: {q['gia_tri']}")
    print(chr(10) + "Mô tả: " + v["mo_ta"])
    print(chr(10) + f"Mã HS ({len(v['ma_hs'])}): " + ", ".join(_ma(c) for c in v["ma_hs"]))
    for n in v["nuoc"] or [{"nuoc": "*", "ten_nuoc": "Mọi xuất xứ", "muc_toan_quoc": v["muc_khong_chung_tu"]}]:
        print(chr(10) + f"--- {n['ten_nuoc']} · mức toàn quốc {_pt(n['muc_toan_quoc'])} ---")
        for x in [x for x in v["nha_sx"] if n["nuoc"] in ("*", x["nuoc"])]:
            muc = "Không áp" if x["khong_ap"] else _pt(x["muc_thue"])
            print(f"  {x['ten']}{' [' + x['nhom'] + ']' if x.get('nhom') else ''}: {muc}")
            if x["cong_ty_tm"]:
                print("      công ty TM: " + "; ".join(x["cong_ty_tm"]))
    if v["loai_tru"]:
        print(chr(10) + "--- Loại trừ ---")
        for x in v["loai_tru"]:
            if x["kieu"] == "mac_thep":
                print(f"  Mác {x['mac_thep']} theo {x['tieu_chuan']}")
            else:
                print(f"  {x['noi_dung'] or x.get('ma_hs')}")
    if v.get("ghi_chu"):
        print(chr(10) + "Ghi chú: " + v["ghi_chu"])


def cmd_thue(code, nuoc=None, nsx=None, nxk=None, mac=None, tc=None):
    r = pl.tinh_cho_lo(_kho(), {"code": code, "nuoc_co": nuoc, "nha_sx": nsx, "nha_xk": nxk,
                                "mac_thep": mac, "tieu_chuan": tc})
    if not r["vu_viec"]:
        print(f"Mã {_ma(r['code'])}: KHÔNG thuộc vụ phòng vệ thương mại nào đang áp (dữ liệu trên máy).")
        return
    for k in r["vu_viec"]:
        print(f"=== [{k['ma_vu_viec']}] {k['ten_hang']} · {k['so_hieu']} ===")
        for i, b in enumerate(k["cac_buoc"], 1):
            print(f"  {i}. {b['buoc']}: {b['ket_qua']} {'✓' if b['dat'] else '✗'}  ({b['can_cu']})")
        ket = f"BỊ ÁP {_pt(k['muc_thue'])}" if k["ket_luan"] == "ap" else "KHÔNG ÁP"
        print(f"  => {ket}")
        for c in k["canh_bao"]:
            print(f"  ! {c}")


def _cbpg_cua_ma(code_n):
    """Dòng cảnh báo CBPG cho lệnh `code` — im lặng nếu máy chưa đồng bộ PVTM."""
    try:
        kho = pl.doc_kho()
    except pl.ChuaDongBo:
        return
    pv = pl.vu_theo_ma(kho, code_n, chi_dang_ap=True)
    if pv:
        print("!!! ĐANG BỊ ÁP THUẾ PHÒNG VỆ THƯƠNG MẠI:")
        for v in pv:
            print(f"  [{v['ma_vu_viec']}] {v['ten_hang']} — {v['so_hieu']}")
        print(f"  Tính mức cho lô: query_hs.py thue {code_n} --nuoc <nước C/O> --nsx <nhà SX> --nxk <nhà XK>")


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


TRANG = 100   # trần `limit` của GET /api/tracuu/van-ban


def _moi_van_ban_ilms():
    """Cả kho văn bản ILMS, lấy từng trang 100 bằng `offset`.

    Thiếu dù một văn bản là bước 3 của dongbo XÓA NHẦM bản trên máy, nên:
    ILMS cũ chưa hiểu `offset` sẽ trả lại trang đầu -> thấy id trùng là dừng
    hẳn, không đoán."""
    ds, da_thay = [], set()
    while True:
        trang = ilms_api.get("/van-ban", limit=TRANG, offset=len(ds))["ket_qua"]
        moi = [v for v in trang if v["id"] not in da_thay]
        if len(moi) != len(trang):
            raise SystemExit("ILMS chưa hỗ trợ lấy từng trang (offset) mà kho đã từ 100 văn bản — "
                             "cập nhật ILMS rồi chạy lại dongbo.")
        ds += trang
        da_thay |= {v["id"] for v in trang}
        if len(trang) < TRANG:
            return ds


def api_dongbo(chi_keo=False):
    import shutil
    ds = _moi_van_ban_ilms()
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
            tren_ilms = {v["so_hieu"]: v for v in _moi_van_ban_ilms()}
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
            than = full["noi_dung"]
            if _doc_dau(than).get("Số hiệu"):   # văn bản đẩy lên từ máy đã mang sẵn phần đầu — bỏ để khỏi in hai lần
                than = than.split("-" * 20, 1)[-1].lstrip("-").strip()
            f.write(f"[Số hiệu] {sh}\n[Tiêu đề] {full['ten']}\n[Ngày ban hành] {full.get('ngay_ban_hanh') or ''}\n"
                    f"[Cơ quan] {full.get('co_quan') or ''}\n" + "-" * 60 + "\n\n" + than)
        moi[sh] = rel
    xoa = 0
    for sh, rel in so_do.items():
        if sh not in moi and os.path.exists(os.path.join(REFS, rel)):
            os.remove(os.path.join(REFS, rel))
            xoa += 1
    with open(SO_DO, "w", encoding="utf-8") as f:
        json.dump(moi, f, ensure_ascii=False, indent=2)
    # 4. Kéo kho phòng vệ thương mại (đủ hồ sơ từng vụ) về data/pvtm.json.
    ds_vu = [ilms_api.get(f"/pvtm/vu-viec/{urllib.parse.quote(v['ma_vu_viec'], safe='')}")
             for v in ilms_api.get("/pvtm/vu-viec")]
    tmp = pl.TEP + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"nguon": ilms_api.URL, "dong_bo_luc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "vu_viec": ds_vu}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, pl.TEP)   # ghi xong mới thay: đứt mạng giữa chừng không để lại tệp dở
    print(f"Kéo {len(ds_vu)} vụ phòng vệ thương mại về data/pvtm.json.")
    print(f"Đồng bộ xong: kéo {len(moi)} văn bản từ ILMS, đẩy {day} lên ILMS, "
          f"dời {doi} tệp định dạng cũ vào references/_cu/, xóa {xoa} bản đã bị xóa trên ILMS.")


def cmd_vanban(ma):
    """Toàn văn một văn bản trên máy, tìm theo số hiệu (vd '1959/QĐ-BCT' hoặc '1959')."""
    k = strip_accents(ma).replace(" ", "")
    for _rel, full in find_ref_files():
        with open(full, encoding="utf-8", errors="replace") as fh:
            nd = fh.read()
        sh = strip_accents(_doc_dau(nd).get("Số hiệu", "")).replace(" ", "")
        if sh and (sh == k or sh.split("/")[0] == k):
            print(nd)
            return
    raise SystemExit(f"Không có văn bản '{ma}' trên máy. Chạy `query_hs.py dongbo` rồi thử lại, "
                     "hoặc `query_hs.py refs <từ khóa>` để tìm.")


# ---------------------------------------------------------------- tra hàng loạt
# Mỗi dòng: mã HS [, nước C/O, nhà SX, nhà XK, mác thép, tiêu chuẩn] — phân cách tab, phẩy hoặc chấm phẩy.
# Xuất TSV để dán vào ô A1 của Excel. Mã in dạng 7210.49.11 để Excel giữ nguyên số 0 đầu.
COT_LO = ("code", "nuoc_co", "nha_sx", "nha_xk", "mac_thep", "tieu_chuan")


def doc_lo(dong):
    """[(so_dong, {code, nuoc_co, ...})] — bỏ dòng trống, dòng '#', và dòng tiêu đề (ô đầu không có số)."""
    import csv
    ra = []
    dong = [d for d in dong if d.strip() and not d.lstrip().startswith("#")]
    if not dong:
        return ra
    try:
        kieu = csv.Sniffer().sniff(dong[0], delimiters="\t,;")
    except csv.Error:
        kieu = csv.excel_tab
    for i, o in enumerate(csv.reader(dong, kieu), 1):
        o = [x.strip() for x in o]
        if i == 1 and not re.search(r"\d{4}", o[0]):
            continue
        ra.append((i, {k: (o[j] if j < len(o) and o[j] else None) for j, k in enumerate(COT_LO)}))
    return ra


def _o(v):
    return re.sub(r"[\t\r\n]+", " ", str(v or "")).strip()


def dong_lo(codes, kho, lo, fta):
    """Một dòng kết quả (list ô) cho một lô."""
    code = re.sub(r"\D", "", lo["code"] or "")
    e = codes.get(code)
    if len(code) != 8 or not e:
        return [_o(lo["code"]), "KHÔNG CÓ MÃ 8 SỐ NÀY TRONG BIỂU THUẾ"] + [""] * (5 + len(fta))
    o = [_ma(code), e.get("desc_vn", ""), e.get("unit", ""), e.get("thue_nk_thong_thuong", ""),
         e.get("mfn", ""), e.get("vat", "")] + [e.get("fta", {}).get(f, "") for f in fta] + [e.get("chinh_sach", "")]
    if kho is None:
        o.append("chưa đồng bộ CBPG")
    elif not pl.vu_theo_ma(kho, code, chi_dang_ap=True):
        o.append("-")
    elif not any(lo[k] for k in COT_LO[1:]):
        o.append("ĐANG ÁP: " + "; ".join(f"{v['ma_vu_viec']} {v['so_hieu']}"
                                          for v in pl.vu_theo_ma(kho, code, chi_dang_ap=True))
                 + " — thêm nước/NSX/NXK để tính mức")
    else:
        try:
            r = pl.tinh_cho_lo(kho, lo)
            o.append("; ".join(f"{k['ma_vu_viec']}: " + (f"ÁP {_pt(k['muc_thue'])}" if k["ket_luan"] == "ap"
                                                          else "không áp") for k in r["vu_viec"]))
        except SystemExit as loi:
            o.append(f"LỖI: {loi}")
    return [_o(x) for x in o]


def cmd_lo(tep, fta="", ra=None):
    codes = load_json("hs_tree.json").get("codes", {})
    if not codes:
        raise SystemExit("Chưa có dữ liệu Biểu thuế — chạy scripts/import_tariff.py trước.")
    if tep == "-":
        dong = sys.stdin.read().splitlines()
    else:
        with open(tep, encoding="utf-8-sig", errors="replace") as fh:
            dong = fh.read().splitlines()
    fta = [f.strip().lower() for f in fta.split(",") if f.strip()]
    try:
        kho = pl.doc_kho()
        cu = pl.canh_bao_cu(kho)
        if cu:
            print(cu, file=sys.stderr)
    except pl.ChuaDongBo:
        kho = None
    dau = ["Mã HS", "Mô tả", "ĐVT", "NK thông thường", "MFN", "VAT"] + [f.upper() for f in fta] \
        + ["Chính sách mặt hàng", "Phòng vệ thương mại"]
    bang = [dau] + [dong_lo(codes, kho, lo, fta) for _i, lo in doc_lo(dong)]
    tsv = "\n".join("\t".join(h) for h in bang) + "\n"
    if ra:
        with open(ra, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(tsv)
        print(f"Ghi {len(bang) - 1} dòng ra {ra}.")
    else:
        sys.stdout.write(tsv)


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
    _cbpg_cua_ma(code_n)


# ---------------------------------------------------------------- tìm mã theo từ khóa
# Khớp theo TỪ (không phân biệt dấu, thứ tự tùy ý): "thep hinh" khớp "Thép ... dạng hình".
# Xếp hạng: đủ mọi từ > thiếu từ; cụm liền mạch; mã 8 số; mô tả ngắn (sát nghĩa hơn).
def _tu(s):
    return re.findall(r"[a-z0-9]+", strip_accents(s))


def xep_hang(codes, keyword, chuong=None):
    """[(diem, code, entry, du_tu)] đã xếp; du_tu=False là kết quả nới lỏng (thiếu từ)."""
    tu = list(dict.fromkeys(_tu(keyword)))
    if not tu:
        return []
    cum = " ".join(tu)
    ra = []
    for code, e in codes.items():
        if chuong and not code.startswith(f"{int(chuong):02d}"):
            continue
        vn = " ".join(_tu(e.get("desc_vn", "")))
        chu = set(vn.split()) | set(_tu(e.get("desc_en", "")))
        khop = sum(1 for t in tu if t in chu or any(c.startswith(t) for c in chu if len(t) >= 3))
        if not khop:
            continue
        diem = khop / len(tu) * 100 + (30 if cum in vn else 0) + (10 if len(code) == 8 else 0) \
            - min(len(vn), 400) / 40
        ra.append((diem, code, e, khop == len(tu)))
    ra.sort(key=lambda r: (-r[0], r[1]))
    du = [r for r in ra if r[3]]
    # Có kết quả đủ từ thì bỏ kết quả thiếu; không có thì chỉ giữ kết quả khớp >= nửa số từ.
    return du or [r for r in ra if r[0] >= 50 - 400 / 40]


def cmd_search(keyword, chuong=None, n=20):
    codes = load_json("hs_tree.json").get("codes", {})
    kq = xep_hang(codes, keyword, chuong)
    if not kq:
        print(f"Không tìm thấy kết quả cho '{keyword}'. (Chỉ là gợi ý từ khóa — luôn đọc Chú giải trước khi kết luận.)")
        return
    if not kq[0][3]:
        print(f"! Không mã nào chứa đủ các từ '{keyword}' — dưới đây là mã khớp MỘT PHẦN.")
    print(f"Kết quả cho '{keyword}': {len(kq)} mã, hiện {min(n, len(kq))} (CHỈ LÀ GỢI Ý — luôn đọc Chú giải trước khi kết luận):")
    nhom_da_in = set()
    for _d, code, e, _du in kq[:n]:
        nhom = code[:4]
        if nhom not in nhom_da_in:
            nhom_da_in.add(nhom)
            print(f"— Nhóm {nhom}: {codes.get(nhom, {}).get('desc_vn', '')[:90]}")
        if len(code) == 8:
            print(f"    {_ma(code)}  MFN={e.get('mfn', '')}  {e.get('desc_vn', '')[:100]}")
    chuong_ds = sorted({c[:2] for _d, c, _e, _du in kq})
    if len(chuong_ds) > 1:
        print(f"Các Chương có mã khớp: {', '.join(chuong_ds)} — lọc bằng --chuong <số>.")


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


def kho_van_ban(category=None):
    """Mọi văn bản trên máy kèm dòng đầu [Số hiệu]/[Ngày ban hành]/[Cơ quan] và quan hệ hiệu lực."""
    ds = []
    for rel, full in find_ref_files(category):
        with open(full, "r", encoding="utf-8", errors="replace") as fh:
            nd = fh.read()
        m = _doc_dau(nd)
        ds.append({"rel": rel, "noi_dung": nd, "so_hieu": m.get("Số hiệu", ""), "tieu_de": m.get("Tiêu đề", ""),
                   "ngay": m.get("Ngày ban hành", ""), "co_quan": m.get("Cơ quan", "")})
    return hl.lap_chi_muc(ds)


def _loc(ds, nam=None, co_quan=None):
    if nam:
        ds = [v for v in ds if v["ngay"].startswith(str(nam)) or f"/{nam}/" in v["so_hieu"]]
    if co_quan:
        k = strip_accents(co_quan)
        ds = [v for v in ds if k in strip_accents(v["co_quan"] + " " + v["so_hieu"])]
    return ds


def _dong_vb(v):
    dau = f"{v['so_hieu'] or v['rel']} ({v['ngay'] or '—'}, {v['co_quan'] or '—'})"
    tt = hl.tinh_trang(v)
    return dau + (f" {tt}" if tt else "")


def cmd_refs(keyword=None, category=None, nam=None, co_quan=None):
    # quan hệ hiệu lực dò trên CẢ kho: văn bản thay thế có thể nằm ở danh mục khác
    ds = [v for v in _loc(kho_van_ban(), nam, co_quan)
          if not category or v["rel"].startswith(category + os.sep) or v["rel"].startswith(category + "/")]
    if not ds:
        print("Chưa có văn bản tham khảo nào (trong danh mục/bộ lọc đã chọn). Dùng scripts/add_reference.py để thêm.")
        return
    if not keyword:
        print(f"Danh sách văn bản tham khảo ({len(ds)}):")
        for v in sorted(ds, key=lambda v: v["ngay"], reverse=True):
            print(f"  {_dong_vb(v)}")
            print(f"      {v['tieu_de'][:110] or v['rel']}")
        return
    kw = strip_accents(keyword)
    found_any = False
    for v in ds:
        content = v["noi_dung"]
        idx = strip_accents(content).find(kw)
        if idx < 0:
            continue
        found_any = True
        print(f"=== {_dong_vb(v)} — {v['rel']} ===")
        start = max(0, idx - 300)
        end = min(len(content), idx + 500)
        print("..." + content[start:end] + "...")
        print()
    if not found_any:
        print(f"Không tìm thấy '{keyword}' trong các văn bản tham khảo hiện có.")


def cmd_hieuluc(ma=None):
    """Quan hệ hiệu lực của một văn bản; không có số hiệu -> mọi văn bản đã có văn bản khác tác động."""
    ds = kho_van_ban()
    print("(Dò tự động trên kho văn bản trên máy — chỉ là GỢI Ý, đối chiếu văn bản gốc trước khi trích dẫn.)")
    if not ma:
        bi = [v for v in ds if v["bi_tac_dong"]]
        if not bi:
            print("Chưa phát hiện văn bản nào trong kho bị văn bản khác trong kho sửa đổi/thay thế.")
            return
        for v in sorted(bi, key=lambda v: v["so_hieu"]):
            print(f"  {_dong_vb(v)}")
        return
    v = next((v for v in ds if v["so_hieu"] and hl.trung_so(v["so_hieu"], ma)), None)
    if not v:
        # văn bản không có trên máy nhưng có thể được văn bản trên máy nhắc tới
        print(f"Không có văn bản '{ma}' trên máy.")
        nhac = [(l, n, t) for n in ds for l, d, t in n["tac_dong"] if hl.trung_so(d, ma)]
    else:
        print(f"=== {v['so_hieu']} — {v['tieu_de']} ===")
        print(f"Ban hành: {v['ngay'] or '—'} · {v['co_quan'] or '—'} · Hiệu lực từ: "
              f"{v['ngay_hl'] or 'không ghi ngày cụ thể (xem Điều khoản thi hành)'}")
        if v["tac_dong"]:
            print("\nVăn bản này tác động lên:")
            for loai, dich, trich in v["tac_dong"]:
                print(f"  • {hl.NHAN[loai]}: {dich}\n      {trich[:260]}")
        nhac = v["bi_tac_dong"]
    if nhac:
        print("\nVăn bản trong kho tác động lên văn bản này:")
        for loai, n, trich in nhac:
            print(f"  • {hl.NHAN[loai]} bởi {n['so_hieu']} ({n['ngay'] or '—'})\n      {trich[:260]}")
    else:
        print("\nChưa thấy văn bản nào trong kho sửa đổi/thay thế văn bản này — KHÔNG có nghĩa là còn "
              "hiệu lực; kho chỉ gồm văn bản đã đồng bộ.")


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
    sp.add_argument("--chuong", help="Chỉ tìm trong 1 Chương (vd 72)")
    sp.add_argument("--n", type=int, default=20, help="Số mã hiển thị (mặc định 20)")

    sp = sub.add_parser("chapter")
    sp.add_argument("num")

    sp = sub.add_parser("heading")
    sp.add_argument("num")

    sp = sub.add_parser("gri")
    sp.add_argument("so", nargs="?")

    sp = sub.add_parser("refs")
    sp.add_argument("keyword", nargs="?")
    sp.add_argument("--category", default=None, help="Giới hạn tra trong 1 danh mục (vd chinh_sach_phap_luat, cbpg_pvtm)")
    sp.add_argument("--nam", help="Lọc theo năm ban hành (vd 2026)")
    sp.add_argument("--co-quan", help="Lọc theo cơ quan ban hành hoặc ký hiệu (vd 'Bộ Tài chính', BCT)")

    sp = sub.add_parser("hieuluc", help="Quan hệ sửa đổi/thay thế/bãi bỏ giữa các văn bản trong kho")
    sp.add_argument("ma", nargs="?", help="Số hiệu (vd 13/2015/TT-BTC); bỏ trống = liệt kê văn bản đã bị tác động")

    sp = sub.add_parser("lo", help="Tra hàng loạt mã HS từ tệp CSV/TSV/TXT, xuất bảng TSV dán thẳng vào Excel")
    sp.add_argument("tep", help="Tệp đầu vào ('-' = đọc từ bàn phím/pipe)")
    sp.add_argument("--fta", default="", help="Các cột FTA cần in, vd acfta,atiga,evfta")
    sp.add_argument("--ra", help="Ghi TSV ra tệp (UTF-8 có BOM để Excel đọc đúng tiếng Việt)")

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

    if args.cmd == "dongbo":
        if not ilms_api.bat():
            raise SystemExit("dongbo cần ILMS_URL + ILMS_USER/ILMS_PASS (nơi lấy dữ liệu).")
        return api_dongbo(args.chi_keo)
    chuyen = {"vanban": lambda: cmd_vanban(args.ma), "cbpg": lambda: cmd_cbpg(args.tu_khoa, args.kieu),
              "vu": lambda: cmd_vu(args.ma), "hieuluc": lambda: cmd_hieuluc(args.ma),
              "lo": lambda: cmd_lo(args.tep, args.fta, args.ra),
              "thue": lambda: cmd_thue(args.code, args.nuoc, args.nsx, args.nxk, args.mac, args.tc)}
    if args.cmd in chuyen:
        return chuyen[args.cmd]()

    if args.cmd == "code":
        cmd_code(args.code)
    elif args.cmd == "search":
        cmd_search(args.keyword, args.chuong, args.n)
    elif args.cmd == "chapter":
        cmd_chapter(args.num)
    elif args.cmd == "heading":
        cmd_heading(args.num)
    elif args.cmd == "gri":
        cmd_gri(args.so)
    elif args.cmd == "refs":
        cmd_refs(args.keyword, args.category, args.nam, args.co_quan)
    elif args.cmd == "case":
        cmd_case(args.keyword)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
