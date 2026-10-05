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
import pvtm_local as pl
import doi_chieu as dc  # noqa: E402
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


def cmd_tom_tat(kho):
    """Một dòng mỗi vụ: đang áp trước, rồi hiệu lực mới trước."""
    ds = sorted(kho["vu_viec"], key=lambda v: v["hieu_luc_tu"], reverse=True)
    ds.sort(key=lambda v: not pl.dang_ap(v))
    print(f"=== {len(ds)} vụ phòng vệ thương mại (dữ liệu đồng bộ {kho['dong_bo_luc'][:10]}) ===")
    for v in ds:
        nuoc = ", ".join(f"{n['nuoc']} {_pt(n['muc_toan_quoc'])}" for n in v["nuoc"]) or "mọi xuất xứ"
        tt = "ĐANG ÁP" if pl.dang_ap(v) else pl.NHAN_GIAI_DOAN.get(v["giai_doan"], v["giai_doan"])
        dc_ = "" if v.get("da_doi_chieu") else " · chưa đối chiếu"
        print(f"  [{v['ma_vu_viec']}] {v['ten_hang']}")
        print(f"      {tt}{dc_} · {v.get('so_hieu') or '—'} · đến {v.get('hieu_luc_den') or 'chưa ghi'} · "
              f"{len(v['ma_hs'])} mã HS · không C/O {_pt(v['muc_khong_chung_tu'])} · {nuoc}")
    print(chr(10) + "Xem hồ sơ: query_hs.py vu <mã vụ> · Tìm: query_hs.py cbpg <từ khóa>")


def _nhan_mien(x):
    """(1) Cách được miễn của dòng loại trừ (ILMS phase141): tự động qua kiểm định, hay phải có QĐ miễn trừ."""
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
    print(f"=== [{v['ma_vu_viec']}] {pl.tieu_de(v['mo_ta'], v['ten_hang'])} ===")
    print(f"{pl.NHAN_LOAI.get(v['loai'], v['loai'])} · {_trang_thai(v)}")
    print(f"Căn cứ: {v.get('so_hieu') or '—'} · Hiệu lực {v['hieu_luc_tu']} → {v.get('hieu_luc_den') or 'chưa ghi'}")
    if v.get("doi_chieu_ten"):
        print(f"Đối chiếu bản giấy: {v['doi_chieu_ten']} lúc {v['doi_chieu_luc']}")
    for b in v.get("van_ban", []):
        print(f"  Văn bản: {b['so_hieu']} ({b['vai']}, {b.get('ngay_ban_hanh') or '—'}) {b.get('link_goc') or ''}")
    print(f"Không nộp C/O: {_pt(v['muc_khong_chung_tu'])}")
    for q in v["quy_cach"]:
        print(f"{q['ten']}: {q['gia_tri']}")
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
    """(2) Đặc tính hàng người dùng tả lệch nhóm đã/chưa phủ-mạ-sơn của mã -> nhắc soát lại mã."""
    if not dac_tinh:
        return
    e = load_json("hs_tree.json").get("codes", {}).get(code_n)
    if e:
        c = pl.lech_phu(dac_tinh, e.get("desc_vn", "") + " " + e.get("desc_en", ""))
        if c:
            print(c + chr(10))


def cmd_thue(code, nuoc=None, nsx=None, nxk=None, mac=None, tc=None, day=None, rong=None, carbon=None,
             loi=None, dang=None, dac_tinh=None):
    lo = {"code": code, "nuoc_co": nuoc, "nha_sx": nsx, "nha_xk": nxk, "mac_thep": mac, "tieu_chuan": tc,
          "day": day, "rong": rong, "carbon": carbon, "loi": loi, "dang": dang}
    kho = _kho()
    _soat_dac_tinh(re.sub(r"\D", "", code), dac_tinh)
    r = pl.tinh_cho_lo(kho, lo)
    if len(r["vu_viec"]) > 1:   # (4)
        print(f"! Mã {_ma(r['code'])} thuộc {len(r['vu_viec'])} vụ đang áp "
              f"({', '.join(k['ma_vu_viec'] for k in r['vu_viec'])}) — xác định hàng đúng mô tả của vụ nào "
              "trước khi chọn mức thuế (xem `vu <mã vụ>`)." + chr(10))
    _in_thue(r)


def _in_thue(r):
    if not r["vu_viec"]:
        print(f"Mã {_ma(r['code'])}: KHÔNG thuộc vụ phòng vệ thương mại nào đang áp (dữ liệu trên máy).")
        return
    dau = {True: "✓", False: "✗", None: "?"}
    for k in r["vu_viec"]:
        print(f"=== [{k['ma_vu_viec']}] {k['tieu_de']} · {k['so_hieu']} ===")
        for i, b in enumerate(k["cac_buoc"], 1):
            print(f"  {i}. {b['buoc']}: {b['ket_qua']} {dau[b['dat']]}  ({b['can_cu']})")
        ket = {"ap": f"BỊ ÁP {_pt(k['muc_thue'])}", "khong_ap": "KHÔNG ÁP",
               "khong_thuoc_pham_vi": "KHÔNG THUỘC PHẠM VI VỤ NÀY (không áp)",
               "chua_du": "CHƯA ĐỦ DỮ LIỆU ĐỂ KẾT LUẬN — cần: " + ", ".join(k.get("thieu", []))}[k["ket_luan"]]
        print(f"  => {ket}")
        for c in k["canh_bao"]:
            print(f"  ! {c}")
        if k.get("tu_doi_chieu") and k["ket_luan"] != "khong_thuoc_pham_vi":
            print("  Tự đối chiếu (công cụ không kiểm được bằng số):")
            for x in k["tu_doi_chieu"]:
                print(f"    - {x}")


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
        json.dump({"nguon": "ILMSv2", "dong_bo_luc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "vu_viec": ds_vu}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, pl.TEP)   # ghi xong mới thay: đứt mạng giữa chừng không để lại tệp dở
    print(f"Kéo {len(ds_vu)} vụ phòng vệ thương mại về data/pvtm.json.")
    trung = pl.trung_ma(pl.doc_kho())
    if trung:
        print(f"Mã HS thuộc từ 2 vụ đang áp trở lên ({len(trung)} mã) — khi tính thuế phải chọn vụ theo mô tả hàng:")
        for c, ds in trung.items():
            print(f"  {_ma(c)}: {', '.join(ds)}")
    import kiem_khop   # (6) ILMS đổi luật mà skill chưa chép lại thì biết NGAY, không đợi tính sai
    so, lech = kiem_khop.chay(in_chi_tiet=False)
    print(f"So luật tính thuế trên máy với ILMS: {so} lô + tiêu đề, {lech} lệch."
          + (" -> CHẠY scripts/chep_luat_ilms.py rồi scripts/kiem_khop.py, chưa dùng `thue` được." if lech else ""))
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
COT_LO = ("code", "nuoc_co", "nha_sx", "nha_xk", "mac_thep", "tieu_chuan", "day", "rong", "carbon", "dang")


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


def _ket_luan_o(k):
    """Như ô Phòng vệ của tra hàng loạt ILMS: thiếu thông số thì nói rõ — ÁP khi thiếu là ÁP GIẢ ĐỊNH."""
    txt = f"ÁP {_pt(k['muc_thue'])}" if k["ket_luan"] == "ap" else pl.NHAN_KET_LUAN[k["ket_luan"]].lower()
    if k["thieu"]:
        txt += (" (giả định — " if k["ket_luan"] == "ap" else " (") + "cần: " + ", ".join(k["thieu"]) + ")"
    return txt


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
            o.append("; ".join(f"{k['ma_vu_viec']}: " + _ket_luan_o(k) for k in r["vu_viec"]))
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


# ---------------------------------------------------------------- tìm mã theo từ khóa
# Khớp theo TỪ (không phân biệt dấu, thứ tự tùy ý): "thep hinh" khớp "Thép ... dạng hình".
# Xếp hạng: đủ mọi từ > thiếu từ; cụm liền mạch; mã 8 số; mô tả ngắn (sát nghĩa hơn).
# Luật xếp hạng là BẢN CHÉP nguyên văn của ILMS (scripts/hs_xep_hang.py, sinh bằng chep_xep_hang_ilms.py).
# Ở đây chỉ còn phần riêng của skill: chỉ mục trên hs_tree.json (thay cho tsvector + ts_stat của ILMS) và
# tiền lệ đọc từ data/tien_le.tsv (thay cho hs_goi_y_log).
import hs_xep_hang as hx  # noqa: E402

_tu = hx.tach_tu
tu_bi_phu_dinh = hx.tu_bi_phu_dinh
TU_CHUNG = hx.TU_CHUNG


def dem_cum_lien(tu, vn, bo_chung=False):
    """Số cặp từ liền nhau của người dùng cũng liền nhau trong mô tả `vn` (chuỗi không dấu, cách bằng khoảng trắng).
    bo_chung=True: không đếm cặp mà cả hai từ đều chung chung ("xu ly", "tu dong")."""
    vn = f" {vn} "
    return sum(1 for a, b in zip(tu, tu[1:])
               if f" {a} {b} " in vn and not (bo_chung and a in TU_CHUNG and b in TU_CHUNG))


def mo_ta_nhom(codes, nhom):
    """Mô tả dòng 4 số; nhóm chỉ có một mã (vd 7221.00.00) thì dòng 4 số trống → lấy đoạn đầu mã 8 số."""
    mt = codes.get(nhom, {}).get("desc_vn", "")
    if mt:
        return mt
    for c in sorted(codes):
        if c.startswith(nhom) and len(c) == 8:
            return doan(codes[c].get("desc_vn", ""))[0]
    return ""


_DOAN = re.compile(r"\s-(?:\s-)+\s")   # Biểu thuế nối các cấp bằng " - - ", " - - - "…


def doan(desc):
    """Các đoạn theo cấp của một mô tả: [mô tả nhóm, cấp 6 số, cấp 8 số…]."""
    return [d.strip(" :") for d in _DOAN.split(desc or "")]


_CHI_MUC = {}   # (id(codes), len) -> {"idf": …, "mo_ta": {(vn, en): hx.MoTa}} — dựng một lần cho mỗi bảng mã


def chi_muc(codes):
    """IDF mỗi từ của Biểu thuế + bản phân tích sẵn từng mô tả (hx.MoTa). Bảng thật (> 1000 mã) đọc/ghi bản dựng
    sẵn trên đĩa — dựng mới ~6 s, đọc lại ~0,3 s; khóa theo kích thước + mtime của hs_tree.json và của bản chép
    luật (đổi luật là tự dựng lại). Nạp xong thì hx.phan_tich đọc thẳng từ đây thay cho lru_cache."""
    import math
    # Bảng thật (> 1000 mã) dùng MỘT chỉ mục, kể cả khi người gọi lọc bớt thành dict mới (phanloai bỏ Chương 98):
    # khóa theo id() thì mỗi lượt dựng lại ~10 s. IDF tính trên cả Biểu thuế — đúng nghĩa "từ phổ biến".
    k = "bang_that" if len(codes) > 1000 else (id(codes), len(codes))
    if k not in _CHI_MUC:
        _CHI_MUC.clear()          # giữ một bảng — tránh phình bộ nhớ khi test đổi bảng liên tục
        _CHI_MUC[k] = _doc_hoac_dung(codes, math)
    cm = _CHI_MUC[k]
    lru = _PHAN_TICH_GOC
    hx.phan_tich = lambda vn, en, _m=cm["mo_ta"]: _m.get((vn, en)) or lru(vn, en)
    return cm


_PHAN_TICH_GOC = hx.phan_tich


def _doc_hoac_dung(codes, math):
    tep_goc = os.path.join(DATA, "hs_tree.json")
    tep_cache = os.path.join(DATA, ".chi_muc.pickle") if len(codes) > 1000 and os.path.exists(tep_goc) else None
    khoa = None
    if tep_cache:
        import pickle
        st, sl = os.stat(tep_goc), os.stat(hx.__file__)
        khoa = (st.st_size, int(st.st_mtime), len(codes), sl.st_size, int(sl.st_mtime), 2)
        try:
            with open(tep_cache, "rb") as f:
                goi = pickle.load(f)
            if goi.get("khoa") == khoa:
                return goi["chi_muc"]
        except (OSError, pickle.UnpicklingError, EOFError, AttributeError, KeyError, TypeError):
            pass   # cache hỏng/thiếu/bản cũ thì dựng lại rồi ghi đè
    df, mo_ta = {}, {}
    for e in codes.values():
        vn, en = e.get("desc_vn", "") or "", e.get("desc_en", "") or ""
        m = mo_ta[(vn, en)] = hx.MoTa(vn, en)
        for t in m.chu:
            df[t] = df.get(t, 0) + 1
    cm = {"idf": hx.idf_tu_df(df, len(codes)), "mo_ta": mo_ta}
    if tep_cache:
        import pickle
        tam = tep_cache + ".tmp"
        with open(tam, "wb") as f:
            pickle.dump({"khoa": khoa, "chi_muc": cm}, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tam, tep_cache)   # ghi xong mới thay — hai lệnh chạy song song không đọc phải tệp dở
    return cm


TEP_TIEN_LE = os.path.join(DATA, "tien_le.tsv")


def tien_le():
    """Tiền lệ của người dùng: data/tien_le.tsv (cột ten_hang, ma_hs) → [(số dòng, tập từ, mã 8 số)].
    Bản trên máy của hs_goi_y_log.ma_chon ở ILMS — ghi bằng `tienle them`."""
    if not os.path.exists(TEP_TIEN_LE):
        return []
    import csv
    with open(TEP_TIEN_LE, encoding="utf-8") as f:
        return [(i, hx.tap_tu(r["ten_hang"]), re.sub(r"\D", "", r["ma_hs"]))
                for i, r in enumerate(csv.DictReader(f, delimiter="\t"), 1) if r.get("ten_hang") and r.get("ma_hs")]


def xep_hang(codes, keyword, chuong=None, noi_long=False, tien_le_ds=None, bo_tien_le_id=None, ten_goc=None):
    """[(diem, code, entry, du_tu)] đã xếp; du_tu=False là kết quả nới lỏng (thiếu từ). Luật chấm: hx.cham
    (bản chép ILMS) + đổi từ đồng nghĩa + cộng điểm tiền lệ — giống tra_cuu.tim_ma của ILMS, chỉ khác là xét MỌI
    mã trên máy thay cho 400 ứng viên tsv.
    noi_long=True: trả MỌI mã khớp ≥ 1 từ (đã xếp hạng) — `phanloai` dùng để tìm nhóm cạnh tranh.
    tien_le_ds: None = đọc data/tien_le.tsv; [] = bỏ tiền lệ (đo luật thuần). ten_goc: tên hàng nguyên văn để so
    với tiền lệ (mặc định = keyword) — phanloai truyền tên chưa bỏ nhãn hiệu, như ILMS so mo_ta nguyên văn."""
    if not _tu(keyword):
        return []
    idf = chi_muc(codes)["idf"]
    q, _da = hx.doi_dong_nghia(keyword)
    tv = hx.TruyVan(q, idf)
    if not tv.tu:
        return []
    thuong = hx.thuong_tien_le(ten_goc or keyword, tien_le() if tien_le_ds is None else tien_le_ds, bo_tien_le_id)
    ra = []
    for code, e in codes.items():
        if chuong and not code.startswith(f"{int(chuong):02d}"):
            continue
        d, du = hx.cham(tv, e.get("desc_vn", "") or "", e.get("desc_en", "") or "")
        t = thuong.get(code)
        if t:
            d, du, e = (d if d != float("-inf") else 0.0) + t[0], True, dict(e, tien_le=t[1])
        if d == float("-inf"):
            continue
        ra.append((d + (0 if len(code) == 8 else -10), code, e, du))   # ILMS chỉ có mã 8 số; ở đây dòng 4/6 số lùi sau
    ra.sort(key=lambda r: (-r[0], r[1]))
    if noi_long:
        return ra
    return loc_du_tu(ra)


# Ngưỡng giữ kết quả thiếu từ: khớp ≥ nửa số từ (50 điểm) sau khi trừ tối đa cho mô tả dài (400/40).
NGUONG_NOI_LONG = hx.NGUONG_NOI_LONG


def loc_du_tu(ra):
    """Có kết quả đủ từ thì bỏ kết quả thiếu; không có thì chỉ giữ kết quả khớp >= nửa số từ."""
    du = [r for r in ra if r[3]]
    return du or [r for r in ra if r[0] >= NGUONG_NOI_LONG]


def cmd_tienle(ten=None, ma=None):
    """Không đối số: liệt kê tiền lệ. Có tên + mã: ghi thêm một dòng (mã phải có trong Biểu thuế, 8 số)."""
    if not ten:
        ds = tien_le()
        print(f"{len(ds)} tiền lệ trong {TEP_TIEN_LE}" if ds else f"Chưa có tiền lệ ({TEP_TIEN_LE}).")
        if os.path.exists(TEP_TIEN_LE):
            with open(TEP_TIEN_LE, encoding="utf-8") as f:
                for dong in list(f)[1:]:
                    print("  " + dong.rstrip("\n").replace("\t", "  →  "))
        return
    code = re.sub(r"\D", "", ma or "")
    codes = load_json("hs_tree.json").get("codes", {})
    if len(code) != 8 or code not in codes:
        raise SystemExit(f"Mã '{ma}' không phải mã 8 số có trong Biểu thuế — không ghi.")
    moi = not os.path.exists(TEP_TIEN_LE)
    with open(TEP_TIEN_LE, "a", encoding="utf-8") as f:
        if moi:
            f.write("ten_hang\tma_hs\n")
        f.write(f"{ten.replace(chr(9), ' ').strip()}\t{code}\n")
    print(f"Đã ghi tiền lệ: {ten.strip()} → {_ma(code)}  ({codes[code].get('desc_vn', '')[:80]})")


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
            print(f"— Nhóm {nhom}: {mo_ta_nhom(codes, nhom)[:90]}")
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
    kq = xep_hang_vb(ds, keyword)
    if not kq:
        print(f"Không tìm thấy '{keyword}' trong các văn bản tham khảo hiện có.")
        return
    print(f"{len(kq)} văn bản khớp '{keyword}' (xếp theo độ liên quan, hiện {min(len(kq), 10)}):" + chr(10))
    for diem, v, doan in kq[:10]:
        print(f"=== {_dong_vb(v)} — {v['tieu_de'][:100] or v['rel']}  (điểm {diem})")
        for d in doan:
            print("    ..." + d + "...")
        print()
    print("Đọc toàn văn: query_hs.py vanban <số hiệu>")


_TU_NHO_VB = {"va", "cua", "cac", "cho", "voi", "la", "the", "nhung", "mot", "trong", "theo", "ve", "tu", "den",
              "hoac", "và", "của", "các", "với", "là", "thì", "những", "một", "về", "từ", "đến", "hoặc"}


def _chuan_vb(s, co_dau):
    """Gõ CÓ dấu thì so có dấu (chỉ hạ chữ) — 'cán' không khớp 'căn cứ'. Gõ không dấu thì so không dấu.
    Cả hai giữ nguyên độ dài chuỗi NFC -> vị trí khớp dùng lại trên bản gốc để trích đoạn."""
    s = unicodedata.normalize("NFC", s)
    return s.lower() if co_dau else strip_accents(s)


def xep_hang_vb(ds, keyword):
    """(7) Xếp văn bản theo độ liên quan (BM25 rút gọn):
    - từ có trong hầu hết văn bản ('căn cứ', 'quyết định') nhẹ ký (idf); văn bản dài không tự được cộng;
    - đủ mọi từ mới tính; không văn bản nào đủ thì hạ xuống 'có ít nhất một từ';
    - cụm nguyên văn, các từ GẦN nhau (≤ 12 từ), khớp ở số hiệu/tiêu đề: cộng thêm.
    Trả [(điểm, văn bản, [đoạn trích tô **từ khớp**])]."""
    import math
    co_dau = strip_accents(keyword) != unicodedata.normalize("NFC", keyword).lower()
    cum = " ".join(_chuan_vb(keyword, co_dau).split())
    tu = list(dict.fromkeys(t for t in cum.split() if t not in _TU_NHO_VB)) or cum.split()
    mau = {t: re.compile(r"(?<!\w)" + re.escape(t) + r"(?!\w)") for t in tu}
    vb = [(v, unicodedata.normalize("NFC", v["noi_dung"])) for v in ds]
    vb = [(v, g, _chuan_vb(g, co_dau)) for v, g in vb]
    df = {t: sum(1 for _v, _g, c in vb if mau[t].search(c)) for t in tu}
    idf = {t: math.log(1 + len(vb) / df[t]) if df[t] else 0 for t in tu}
    tb = sum(len(c) for _v, _g, c in vb) / max(len(vb), 1)
    kq = []
    for v, goc, c in vb:
        vt = {t: [m.start() for m in mau[t].finditer(c)] for t in tu}
        if not any(vt.values()):
            continue
        du = all(vt.values())
        tieu = _chuan_vb(v["so_hieu"] + " " + v["tieu_de"], co_dau)
        ti_le = 0.25 + 0.75 * len(c) / tb
        diem = sum(idf[t] * len(x) * 2.2 / (len(x) + 1.2 * ti_le) for t, x in vt.items() if x)
        diem += sum(2 * idf[t] for t in tu if mau[t].search(tieu))
        gan = _cua_so_gan(vt, c) if du and len(tu) > 1 else None
        if cum in c:
            diem += 5 * sum(idf.values())
        elif gan is not None:
            diem += 3 * sum(idf.values())
        tam = c.find(cum) if cum in c else (gan if gan is not None else min(x[0] for x in vt.values() if x))
        kq.append((du, round(diem, 1), v, _trich_vb(goc, c, tam, tu, mau)))
    co_du = any(x[0] for x in kq)
    kq = sorted((x for x in kq if x[0] or not co_du), key=lambda x: -x[1])
    return [(diem, v, doan) for _du, diem, v, doan in kq]


def _cua_so_gan(vt, c, tran=12):
    """Vị trí đầu của đoạn NGẮN NHẤT chứa đủ mọi từ, nếu đoạn ấy ≤ `tran` từ; không thì None."""
    moc = sorted((i, t) for t, v in vt.items() for i in v)
    dem, trai, tot = {}, 0, None
    for i, t in moc:
        dem[t] = dem.get(t, 0) + 1
        while len(dem) == len(vt):
            a, ta = moc[trai]
            if len(c[a:i].split()) <= tran and (tot is None or i - a < tot[1] - tot[0]):
                tot = (a, i)
            dem[ta] -= 1
            if not dem[ta]:
                del dem[ta]
            trai += 1
    return tot[0] if tot else None


def _trich_vb(goc, c, tam, tu, mau, rong=170):
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


def cmd_canhbao(ngay=90, ngay_vb=30, hom_nay=None):
    """Việc cần theo dõi: vụ PVTM sắp hết hạn / quá hạn / tạm thời / rà soát, văn bản mới ban hành."""
    from datetime import date, timedelta
    hn = date.fromisoformat(hom_nay) if hom_nay else date.today()
    print(f"=== CẢNH BÁO THỜI HẠN — tính đến {hn:%d/%m/%Y}, nhìn trước {ngay} ngày ===")
    try:
        kho = pl.doc_kho()
    except pl.ChuaDongBo as loi:
        kho = None
        print(f"! {loi}")
    if kho:
        cu = pl.canh_bao_cu(kho)
        if cu:
            print(cu)
        con_ap = [v for v in kho["vu_viec"] if v["giai_doan"] in pl.GIAI_DOAN_CON_AP]
        het = []
        for v in con_ap:
            den = v.get("hieu_luc_den")
            if den and hn <= date.fromisoformat(den) <= hn + timedelta(days=ngay):
                het.append((date.fromisoformat(den), v))
        print(chr(10) + f"A. Vụ sắp hết hiệu lực trong {ngay} ngày ({len(het)}):")
        for den, v in sorted(het, key=lambda x: x[0]):
            print(f"  [{v['ma_vu_viec']}] {v['ten_hang']} — {v['so_hieu']}: hết {den:%d/%m/%Y} "
                  f"(còn {(den - hn).days} ngày). Theo dõi QĐ rà soát cuối kỳ / gia hạn.")
        qua = [v for v in con_ap if v.get("hieu_luc_den") and date.fromisoformat(v["hieu_luc_den"]) < hn]
        print(chr(10) + f"B. Đã quá ngày hết hiệu lực nhưng dữ liệu vẫn ghi còn áp ({len(qua)}):")
        for v in qua:
            print(f"  [{v['ma_vu_viec']}] {v['so_hieu']}: hết {v['hieu_luc_den']} — kiểm QĐ gia hạn rồi chạy dongbo.")
        theo_doi = [v for v in con_ap if v["giai_doan"] in ("tam_thoi", "ra_soat")]
        print(chr(10) + f"C. Vụ đang tạm thời / đang rà soát — mức thuế có thể đổi ({len(theo_doi)}):")
        for v in theo_doi:
            den = v.get("hieu_luc_den") or "chưa ghi"
            print(f"  [{v['ma_vu_viec']}] {v['ten_hang']} — {v['so_hieu']} · "
                  f"{pl.NHAN_GIAI_DOAN[v['giai_doan']]} · hiệu lực {v['hieu_luc_tu']} → {den}")
    moi = [v for v in kho_van_ban() if v["ngay"] and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v["ngay"])
           and hn - timedelta(days=ngay_vb) <= date.fromisoformat(v["ngay"]) <= hn]
    print(chr(10) + f"D. Văn bản trong kho ban hành trong {ngay_vb} ngày qua ({len(moi)}):")
    for v in sorted(moi, key=lambda v: v["ngay"], reverse=True):
        print(f"  {_dong_vb(v)}")
        print(f"      {v['tieu_de'][:110]}")


def cmd_chungtu(tep, tsv=False):
    """Đối chiếu chéo chứng từ (JSON do Claude trích) rồi soát thuế PVTM cho lô."""
    with open(tep, encoding="utf-8") as fh:
        ho_so = json.load(fh)
    dong, lo, canh_bao = dc.doi_chieu(ho_so)
    cot = [l for l in dc.LOAI if any(l in d["gia_tri"] for d in dong)]
    dau = ["Trường"] + [dc.LOAI[l] for l in cot] + ["Kết quả"]
    bang = [dau] + [[d["nhan"]] + [d["gia_tri"].get(l, "") for l in cot] + [d["ket"]] for d in dong]
    print("=== ĐỐI CHIẾU CHÉO CHỨNG TỪ ===")
    if tsv:
        print("\n".join("\t".join(_o(x) for x in h) for h in bang))
    else:
        rong = [max(len(str(h[i])) for h in bang) for i in range(len(dau))]
        for h in bang:
            print("  " + " | ".join(str(x).ljust(rong[i]) for i, x in enumerate(h)))
    kho = _kho()
    for c in canh_bao + dc.canh_bao_cach_viet_mac(kho, lo):
        print(f"! {c}")
    print()
    print("=== SOÁT THUẾ PHÒNG VỆ THƯƠNG MẠI (theo giá trị ưu tiên ở trên) ===")
    chua_ro = [d["nhan"] for d in dong if d["ket"].startswith(("✗", "?"))]
    if chua_ro:
        print(f"!!! KẾT LUẬN DƯỚI ĐÂY CHỈ LÀ TẠM — còn {len(chua_ro)} điểm lệch/đọc không chắc: "
              + ", ".join(chua_ro) + ". Làm rõ trước khi xác định thuế.")
    _in_thue(pl.tinh_cho_lo(kho, dc.lo_tinh_thue(lo)))


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
    sp.add_argument("--dac-tinh", help="Đặc tính hàng (vd 'đã sơn lót') — soát lệch với mô tả mã về phủ/mạ/sơn")

    sp = sub.add_parser("search")
    sp.add_argument("keyword")
    sp.add_argument("--chuong", help="Chỉ tìm trong 1 Chương (vd 72)")
    sp.add_argument("--n", type=int, default=20, help="Số mã hiển thị (mặc định 20)")

    sp = sub.add_parser("phanloai", help="Gợi ý mã HS từ TÊN HÀNG theo 6 quy tắc GRI (trình bày từng quy tắc + câu hỏi)")
    sp.add_argument("ten", help="Tên hàng khai báo, vd 'Thép không gỉ dạng thanh tròn cán nóng, hiệu POSCO'")
    sp.add_argument("--chuong", help="Chỉ xét trong 1 Chương (vd 72)")
    sp.add_argument("--n", type=int, default=8, help="Số mã hiển thị mỗi nhóm (mặc định 8)")
    sp.add_argument("--json", action="store_true", help="Xuất JSON có cấu trúc (cho ILMS/agent dùng)")

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

    sp = sub.add_parser("chungtu", help="Đối chiếu chéo Mill Test/C-O/hóa đơn/tờ khai (JSON) rồi soát thuế PVTM")
    sp.add_argument("tep", help="Tệp JSON hồ sơ chứng từ (xem scripts/doi_chieu.py)")
    sp.add_argument("--tsv", action="store_true", help="In bảng đối chiếu dạng TSV để dán Excel")

    sp = sub.add_parser("canhbao", help="Vụ PVTM sắp hết hạn/quá hạn/tạm thời/rà soát, văn bản mới ban hành")
    sp.add_argument("--ngay", type=int, default=90, help="Nhìn trước bao nhiêu ngày (mặc định 90)")
    sp.add_argument("--ngay-vb", type=int, default=30, help="Văn bản ban hành trong bao nhiêu ngày qua (mặc định 30)")
    sp.add_argument("--hom-nay", help="Tính như thể hôm nay là ngày này (YYYY-MM-DD)")

    sp = sub.add_parser("tienle", help="Tiền lệ: tên hàng → mã đã chốt (data/tien_le.tsv); phanloai/search cộng điểm mã ấy")
    sp.add_argument("ten", nargs="?", help="Tên hàng (bỏ trống = liệt kê)")
    sp.add_argument("ma", nargs="?", help="Mã HS 8 số đã chốt cho tên hàng này")

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
    sp.add_argument("--day", help="Độ dày (mm)")
    sp.add_argument("--rong", help="Chiều rộng (mm)")
    sp.add_argument("--carbon", help="Hàm lượng carbon (%% khối lượng; với dây hàn là carbon của lõi)")
    sp.add_argument("--loi", help="Đường kính lõi (mm) — dây hàn, que hàn")
    sp.add_argument("--dang", help="tam (tấm) hoặc cuon (cuộn)")
    sp.add_argument("--dac-tinh", help="Đặc tính hàng (vd 'đã sơn lót') — soát lệch với mô tả mã về phủ/mạ/sơn")

    args = p.parse_args()

    if args.cmd == "dongbo":
        if not ilms_api.bat():
            raise SystemExit("dongbo cần ILMS_URL + ILMS_USER/ILMS_PASS (nơi lấy dữ liệu).")
        return api_dongbo(args.chi_keo)
    chuyen = {"vanban": lambda: cmd_vanban(args.ma), "cbpg": lambda: cmd_cbpg(args.tu_khoa, args.kieu),
              "vu": lambda: cmd_vu(args.ma), "hieuluc": lambda: cmd_hieuluc(args.ma),
              "lo": lambda: cmd_lo(args.tep, args.fta, args.ra),
              "canhbao": lambda: cmd_canhbao(args.ngay, args.ngay_vb, args.hom_nay),
              "chungtu": lambda: cmd_chungtu(args.tep, args.tsv),
              "thue": lambda: cmd_thue(args.code, args.nuoc, args.nsx, args.nxk, args.mac, args.tc,
                                         args.day, args.rong, args.carbon, args.loi, args.dang, args.dac_tinh)}
    if args.cmd in chuyen:
        return chuyen[args.cmd]()

    if args.cmd == "code":
        cmd_code(args.code, args.dac_tinh)
    elif args.cmd == "search":
        cmd_search(args.keyword, args.chuong, args.n)
    elif args.cmd == "phanloai":
        import phan_loai
        phan_loai.cmd_phanloai(args.ten, args.chuong, args.n, args.json)
    elif args.cmd == "chapter":
        cmd_chapter(args.num)
    elif args.cmd == "heading":
        cmd_heading(args.num)
    elif args.cmd == "gri":
        cmd_gri(args.so)
    elif args.cmd == "refs":
        cmd_refs(args.keyword, args.category, args.nam, args.co_quan)
    elif args.cmd == "tienle":
        cmd_tienle(args.ten, args.ma)
    elif args.cmd == "case":
        cmd_case(args.keyword)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
