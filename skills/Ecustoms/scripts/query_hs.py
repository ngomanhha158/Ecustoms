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
import os
import json
import urllib.parse
import argparse
import re
import unicodedata
from datetime import datetime, timezone

# Ép output UTF-8 để tránh lỗi mã hóa trên Windows console (cp1252/cp437)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
REFS = os.path.join(BASE, "references")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ilms_api  # noqa: E402  — CHỈ dùng khi đồng bộ (`dongbo`); tra cứu luôn đọc dữ liệu trên máy
import pvtm_local as pl  # noqa: E402


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


def cmd_tom_tat(kho):
    """Một dòng mỗi vụ: đang áp trước, rồi hiệu lực mới trước."""
    ds = sorted(kho["vu_viec"], key=lambda v: v["hieu_luc_tu"], reverse=True)
    ds.sort(key=lambda v: not pl.dang_ap(v))
    print(f"=== {len(ds)} vụ phòng vệ thương mại (dữ liệu đồng bộ {kho['dong_bo_luc'][:10]}) ===")
    for v in ds:
        nuoc = ", ".join(f"{n['nuoc']} {_pt(n['muc_toan_quoc'])}" for n in v["nuoc"]) or "mọi xuất xứ"
        tt = "ĐANG ÁP" if pl.dang_ap(v) else pl.NHAN_GIAI_DOAN.get(v["giai_doan"], v["giai_doan"])
        dc = "" if v.get("da_doi_chieu") else " · chưa đối chiếu"
        print(f"  [{v['ma_vu_viec']}] {v['ten_hang']}")
        print(f"      {tt}{dc} · {v.get('so_hieu') or '—'} · đến {v.get('hieu_luc_den') or 'chưa ghi'} · "
              f"{len(v['ma_hs'])} mã HS · không C/O {_pt(v['muc_khong_chung_tu'])} · {nuoc}")
    print(chr(10) + "Xem hồ sơ: query_hs.py vu <mã vụ> · Tìm: query_hs.py cbpg <từ khóa>")


def _nhan_mien(x):
    t = x.get("thu_tuc")
    return f"  [{pl.NHAN_THU_TUC_MIEN_TRU[t]}]" if t in pl.NHAN_THU_TUC_MIEN_TRU else ""


def cmd_cbpg(tu_khoa=None, kieu=None):
    if not tu_khoa:
        return cmd_tom_tat(_kho())
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
                print(f"  KHÔNG THUỘC PHẠM VI: {x['noi_dung']}{_nhan_mien(x)}  ← {vu}")
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
                print(f"  {x['noi_dung'] or x.get('ma_hs')}{_nhan_mien(x)}")
    if v.get("ghi_chu"):
        print(chr(10) + "Ghi chú: " + v["ghi_chu"])


def _soat_dac_tinh(code_n, dac_tinh):
    if not dac_tinh:
        return
    e = load_json("hs_tree.json").get("codes", {}).get(code_n)
    if e:
        c = pl.lech_phu(dac_tinh, e.get("desc_vn", "") + " " + e.get("desc_en", ""))
        if c:
            print(c + chr(10))


def cmd_thue(code, nuoc=None, nsx=None, nxk=None, mac=None, tc=None, dac_tinh=None, quy_cach=None):
    kho = _kho()
    _soat_dac_tinh(re.sub(r"\D", "", code), dac_tinh)
    r = pl.tinh_cho_lo(kho, {"code": code, "nuoc_co": nuoc, "nha_sx": nsx, "nha_xk": nxk,
                             "mac_thep": mac, "tieu_chuan": tc, **(quy_cach or {})})
    if len(r["vu_viec"]) > 1:
        print(f"! Mã {_ma(r['code'])} thuộc {len(r['vu_viec'])} vụ đang áp "
              f"({', '.join(k['ma_vu_viec'] for k in r['vu_viec'])}) — xác định hàng đúng mô tả của vụ nào "
              "trước khi chọn mức thuế (xem `vu <mã vụ>`)." + chr(10))
    if not r["vu_viec"]:
        print(f"Mã {_ma(r['code'])}: KHÔNG thuộc vụ phòng vệ thương mại nào đang áp (dữ liệu trên máy).")
        return
    for k in r["vu_viec"]:
        print(f"=== [{k['ma_vu_viec']}] {k.get('tieu_de') or k['ten_hang']} · {k['so_hieu']} ===")
        for i, b in enumerate(k["cac_buoc"], 1):
            dau = {True: "✓", False: "✗"}.get(b["dat"], "?")
            print(f"  {i}. {b['buoc']}: {b['ket_qua']} {dau}  ({b['can_cu']})")
        kl = k["ket_luan"]
        print("  => " + (f"BỊ ÁP {_pt(k['muc_thue'])}" if kl == "ap" else pl.NHAN_KET_LUAN.get(kl, kl).upper()))
        if k.get("thieu"):
            co = " ".join(f"--{x}" for x in k["thieu_khoa"])
            print(f"  ? Cần thêm: {', '.join(k['thieu'])}  (nhập bằng {co})")
        for c in k["canh_bao"]:
            print(f"  ! {c}")
        for c in k.get("tu_doi_chieu") or []:
            print(f"  · Tự đối chiếu: {c}")
    if r.get("chua_du"):
        print(chr(10) + "CHƯA ĐỦ DỮ LIỆU ở ít nhất một vụ — không kết luận 'không áp'; hỏi thêm các thông số ở dòng '? Cần thêm'.")


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
    trung = pl.trung_ma(pl.doc_kho())
    if trung:
        print(f"Mã HS thuộc từ 2 vụ đang áp trở lên ({len(trung)} mã) — khi tính thuế phải chọn vụ theo mô tả hàng:")
        for c, ds in trung.items():
            print(f"  {_ma(c)}: {', '.join(ds)}")
    import kiem_khop
    so_lo, lech = kiem_khop.chay(in_chi_tiet=False)
    print(f"So luật tính thuế trên máy với ILMS: {so_lo} lô, {lech} lệch."
          + (" -> CHẠY scripts/kiem_khop.py xem chi tiết, chưa dùng `thue` được." if lech else ""))
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


def cmd_code(code, dac_tinh=None):
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
    _soat_dac_tinh(code_n, dac_tinh)


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
    kq = xep_hang(files, keyword)
    if not kq:
        print(f"Không tìm thấy '{keyword}' trong các văn bản tham khảo hiện có.")
        return
    tong = len(kq)
    print(f"{tong} văn bản khớp '{keyword}' (xếp theo độ liên quan, hiện {min(tong, 10)}):" + chr(10))
    for diem, rel, dau, doan in kq[:10]:
        print(f"=== {dau.get('Số hiệu') or rel} — {dau.get('Tiêu đề', '')[:110]}  (điểm {diem})")
        for d in doan:
            print("    ..." + d + "...")
        print()
    print("Đọc toàn văn: query_hs.py vanban <số hiệu>")


_TU_NHO = {"va", "cua", "cac", "cho", "voi", "la", "the", "nhung", "mot", "trong", "theo", "ve", "tu", "den", "hoac",
           "và", "của", "các", "cho", "với", "là", "thì", "những", "một", "trong", "theo", "về", "từ", "đến", "hoặc"}


def _chuan(s, co_dau):
    """Gõ CÓ dấu thì so có dấu (chỉ hạ chữ) — 'cán' không được khớp 'căn cứ'.
    Gõ không dấu thì so không dấu. Cả hai giữ nguyên độ dài chuỗi NFC -> vị trí khớp
    dùng lại được trên bản gốc để trích đoạn."""
    s = unicodedata.normalize("NFC", s)
    return s.lower() if co_dau else strip_accents(s)


def xep_hang(files, keyword):
    """Xếp văn bản theo độ liên quan (kiểu BM25 rút gọn):
    - từ nào có trong hầu hết văn bản ('căn cứ', 'quyết định') thì nhẹ ký (idf);
    - văn bản càng dài thì mỗi lần khớp càng nhẹ ký (chuẩn hóa độ dài);
    - đủ mọi từ mới tính; không văn bản nào đủ thì hạ xuống 'có ít nhất một từ';
    - cụm nguyên văn, các từ đứng GẦN nhau (≤ 12 từ), khớp ở số hiệu/tiêu đề: cộng thêm.
    Trả [(điểm, rel, phần đầu, [≤2 đoạn trích tô **từ khớp**])]."""
    import math
    co_dau = strip_accents(keyword) != unicodedata.normalize("NFC", keyword).lower()
    cum = " ".join(_chuan(keyword, co_dau).split())
    tu = list(dict.fromkeys(t for t in cum.split() if t not in _TU_NHO)) or cum.split()
    mau = {t: re.compile(r"(?<!\w)" + re.escape(t) + r"(?!\w)") for t in tu}
    vb = []
    for rel, full in files:
        with open(full, "r", encoding="utf-8", errors="replace") as fh:
            goc = unicodedata.normalize("NFC", fh.read())
        vb.append((rel, goc, _chuan(goc, co_dau)))
    df = {t: sum(1 for _r, _g, c in vb if mau[t].search(c)) for t in tu}
    tb = sum(len(c) for _r, _g, c in vb) / max(len(vb), 1)   # độ dài trung bình (BM25: văn bản dài không tự được cộng)
    idf = {t: math.log(1 + len(vb) / df[t]) if df[t] else 0 for t in tu}
    ds = []
    for rel, goc, c in vb:
        vt = {t: [m.start() for m in mau[t].finditer(c)] for t in tu}
        if not any(vt.values()):
            continue
        du = all(vt.values())
        dau = _doc_dau(goc)
        tieu = _chuan(" ".join(dau.values()), co_dau)
        ti_le = 0.25 + 0.75 * len(c) / tb
        diem = sum(idf[t] * len(v) * 2.2 / (len(v) + 1.2 * ti_le) for t, v in vt.items() if v)
        diem += sum(2 * idf[t] for t in tu if mau[t].search(tieu))
        gan = _cua_so_gan(vt, c) if du and len(tu) > 1 else None
        if cum in c:
            diem += 5 * sum(idf.values())
        elif gan:
            diem += 3 * sum(idf.values())
        tam = c.find(cum) if cum in c else (gan if gan is not None else
                                             min((v[0] for t, v in vt.items() if v), key=lambda x: x))
        ds.append((du, round(diem, 1), rel, dau, _trich(goc, c, tam, tu, mau)))
    co_du = any(x[0] for x in ds)
    ds = [x for x in ds if x[0] or not co_du]
    ds.sort(key=lambda x: -x[1])
    return [(diem, rel, dau, doan) for _du, diem, rel, dau, doan in ds]


def _cua_so_gan(vt, c, tran=12):
    """Vị trí đầu của đoạn NGẮN NHẤT chứa đủ mọi từ, nếu đoạn ấy ≤ `tran` từ; không thì None."""
    moc = sorted((i, t) for t, v in vt.items() for i in v)
    can, dem, trai, tot = len(vt), {}, 0, None
    for phai, (i, t) in enumerate(moc):
        dem[t] = dem.get(t, 0) + 1
        while len(dem) == can:
            a, ta = moc[trai]
            if len(c[a:i].split()) <= tran and (tot is None or i - a < tot[1] - tot[0]):
                tot = (a, i)
            dem[ta] -= 1
            if not dem[ta]:
                del dem[ta]
            trai += 1
    return tot[0] if tot else None


def _trich(goc, c, tam, tu, mau, rong=170):
    """Đoạn quanh vị trí `tam` (cụm / cửa sổ gần nhất / lần khớp đầu), tô **từ khớp**."""
    a, b = max(0, tam - rong // 3), min(len(goc), tam + rong)
    khoang = sorted({(m.start(), m.end()) for t in tu for m in mau[t].finditer(c[a:b])})
    ra, i, s = [], 0, goc[a:b]
    for x, y in khoang:
        if x < i:
            continue
        ra.append(s[i:x] + "**" + s[x:y] + "**")
        i = y
    return [" ".join(("".join(ra) + s[i:]).split())]


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
    sp.add_argument("--dac-tinh", help="Đặc tính hàng (vd 'đã sơn lót') — soát lệch với mô tả mã về phủ/mạ/sơn")

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
    sp.add_argument("tu_khoa", nargs="?", help="Bỏ trống = bảng tóm tắt mọi vụ")
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
    sp.add_argument("--day", help="Độ dày lô (mm), vd 2,5")
    sp.add_argument("--rong", help="Chiều rộng lô (mm), vd 1250")
    sp.add_argument("--carbon", help="Hàm lượng carbon (%% khối lượng), vd 0,16")
    sp.add_argument("--loi", help="Đường kính lõi dây/que hàn (mm)")
    sp.add_argument("--dang", help="Dạng hàng: tam | cuon")
    sp.add_argument("--dac-tinh", help="Đặc tính hàng (vd 'đã sơn lót') — soát lệch với mô tả mã về phủ/mạ/sơn")

    args = p.parse_args()

    if args.cmd == "dongbo":
        if not ilms_api.bat():
            raise SystemExit("dongbo cần ILMS_URL + ILMS_USER/ILMS_PASS (nơi lấy dữ liệu).")
        return api_dongbo(args.chi_keo)
    chuyen = {"vanban": lambda: cmd_vanban(args.ma), "cbpg": lambda: cmd_cbpg(args.tu_khoa, args.kieu),
              "vu": lambda: cmd_vu(args.ma),
              "thue": lambda: cmd_thue(args.code, args.nuoc, args.nsx, args.nxk, args.mac, args.tc, args.dac_tinh,
                                       {k: getattr(args, k) for k in ("day", "rong", "carbon", "loi", "dang")})}
    if args.cmd in chuyen:
        return chuyen[args.cmd]()

    if args.cmd == "code":
        cmd_code(args.code, args.dac_tinh)
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
