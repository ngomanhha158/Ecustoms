# -*- coding: utf-8 -*-
"""Phòng vệ thương mại (CBPG…) chạy HOÀN TOÀN trên máy — đọc data/pvtm.json.

Skill Ecustoms tách khỏi ILMSv2: ILMS chỉ là nơi ĐỒNG BỘ dữ liệu (`query_hs.py
dongbo` kéo về data/pvtm.json). Tra cứu, xem hồ sơ vụ, tính thuế đều chạy ở đây,
không cần mạng.

LUẬT TÍNH THUẾ nằm ở `pvtm_luat.py` — bản chép NGUYÊN TỆP `services/pvtm.py` của
ILMS, sinh tự động bằng `chep_luat.py` (không sửa tay). Tệp này chỉ còn tầng KHO
(đọc data/pvtm.json, chọn vụ theo mã, tìm) và tầng gọi (kiểm đầu vào như LoIn của
ILMS). `kiem_khop.py` so cả chuỗi với máy chủ ILMS.
"""
import json
import os
import re
from datetime import date, datetime, timezone

from luat_nen import bo_dau, la_ma_hs  # noqa: F401  (query_hs / kiem_khop dùng qua pl.*)
from pvtm_luat import (GIAI_DOAN_CON_AP, NHAN_GIAI_DOAN, NHAN_KET_LUAN, NHAN_KHOA, NHAN_KIEU_TIM,  # noqa: F401
                       NHAN_LOAI, TEN_NUOC, chuan_dang, chuan_nuoc, doc_so, khoa_can_nhap, ma_hs_8,
                       tinh_muc_thue)

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TEP = os.path.join(DATA, "pvtm.json")
CU_SAU_NGAY = 7   # dữ liệu cũ hơn số ngày này thì in cảnh báo

try:   # ILMS phase131 (cách miễn của dòng loại trừ) — có trong luật khi ILMS đã merge nhánh ấy
    from pvtm_luat import NHAN_THU_TUC_MIEN_TRU
except ImportError:
    NHAN_THU_TUC_MIEN_TRU = {"kiem_dinh": "Tự động — căn cứ kết quả kiểm định Hải quan hoặc giám định",
                             "xin_mien_tru": "Chỉ khi có quyết định miễn trừ của Bộ Công Thương"}


# ================================================================ kho trên máy
class ChuaDongBo(SystemExit):
    pass


def doc_kho():
    if not os.path.exists(TEP):
        raise ChuaDongBo("Chưa có dữ liệu CBPG trên máy — chạy: python scripts/query_hs.py dongbo")
    with open(TEP, encoding="utf-8") as f:
        return json.load(f)


def canh_bao_cu(kho):
    """Chuỗi cảnh báo nếu dữ liệu đồng bộ đã cũ, '' nếu còn mới."""
    luc = datetime.fromisoformat(kho["dong_bo_luc"])
    ngay = (datetime.now(timezone.utc) - luc).days
    if ngay > CU_SAU_NGAY:
        return (f"! Dữ liệu CBPG đồng bộ cách đây {ngay} ngày ({luc:%d/%m/%Y}) — mức thuế có thể đã đổi "
                f"theo QĐ mới. Chạy: python scripts/query_hs.py dongbo")
    return ""


def dang_ap(v, hom_nay=None):
    """Cùng định nghĩa với ILMS pvtm.sql_dang_ap(), tính theo ngày hôm nay (không tin cờ lúc đồng bộ)."""
    d = (hom_nay or date.today()).isoformat()
    return (v["giai_doan"] in GIAI_DOAN_CON_AP and v["hieu_luc_tu"] <= d
            and (not v.get("hieu_luc_den") or v["hieu_luc_den"] >= d))


def vu_theo_ma(kho, code, chi_dang_ap=False):
    """Các vụ có mã 8 số này, đang áp trước rồi hiệu lực mới trước (như ILMS vu_theo_ma_hs)."""
    ds = [v for v in kho["vu_viec"] if code in v["ma_hs"] and (dang_ap(v) or not chi_dang_ap)]
    ds.sort(key=lambda v: v.get("id", 0))                    # trùng ngày: id nhỏ trước, như ILMS trả thực tế
    ds.sort(key=lambda v: v["hieu_luc_tu"], reverse=True)
    return sorted(ds, key=lambda v: not dang_ap(v))   # sort ổn định: giữ thứ tự ngày trong mỗi nhóm


def _so_lo(ten, v):
    """Như ILMS LoIn._so: '0,18' -> 0.18, rộng '2.000' -> 2000; độ dày/carbon/lõi dạng '2.500'
    MƠ HỒ (2,5 hay 2500?) -> báo lỗi hỏi lại, không đoán."""
    if isinstance(v, str):
        v = v.strip()
        if ten != "rong" and re.fullmatch(r"\d{1,3}(?:\.\d{3})+", v):
            raise SystemExit(f"'{v}' mơ hồ — viết '{v.replace('.', ',')}' (thập phân) hoặc bỏ dấu chấm (hàng nghìn)")
        try:
            return doc_so(v) if v else None
        except ValueError:
            raise SystemExit(f"{NHAN_KHOA[ten]}: '{v}' không phải số")
    return v


def tinh_cho_lo(kho, lo):
    """Như ILMS pvtm_kho.tinh_cho_lo: mọi vụ ĐANG ÁP của mã HS × luật tính thuế (pvtm_luat)."""
    code = ma_hs_8(lo.get("code"))
    if not code:
        raise SystemExit("Mã HS phải đủ 8 số")
    try:
        lo = {**lo, "code": code, "nuoc_co": chuan_nuoc(lo.get("nuoc_co")), "dang": chuan_dang(lo.get("dang"))}
    except ValueError as e:   # nước / dạng lạ -> báo, không đoán (ILMS trả 422)
        raise SystemExit(str(e))
    for k in ("day", "rong", "carbon", "loi"):
        lo[k] = _so_lo(k, lo.get(k))
    ket_qua = [{**tinh_muc_thue(vu, lo).dict(), "ten_hang": vu["ten_hang"], "tieu_de": vu.get("tieu_de"),
                "so_hieu": vu["so_hieu"], "da_doi_chieu": vu["da_doi_chieu"]}
               for vu in vu_theo_ma(kho, code, chi_dang_ap=True)]
    return {"code": code, "bi_ap": any(k["ket_luan"] == "ap" for k in ket_qua),
            "chua_du": any(k["ket_luan"] == "chua_du" for k in ket_qua), "vu_viec": ket_qua}


def tim(kho, q, kieu=""):
    """Tìm theo 9 loại khóa như ILMS pvtm_kho.tim (khớp chuỗi con, không dấu, không phân biệt hoa thường)."""
    if kieu and kieu not in NHAN_KIEU_TIM:
        raise SystemExit(f"--kieu phải thuộc {tuple(NHAN_KIEU_TIM)}")
    k = bo_dau(q.strip())
    ma = la_ma_hs(q)
    co = lambda s: bool(s) and k in bo_dau(s)   # noqa: E731
    nhom = {x: [] for x in NHAN_KIEU_TIM}
    for v in kho["vu_viec"]:
        vu = {"ma_vu_viec": v["ma_vu_viec"], "ten_hang": v["ten_hang"], "dang_ap": dang_ap(v)}
        if co(v["ten_hang"]) or co(v["mo_ta"]) or co(v["ma_vu_viec"]):
            nhom["mat_hang"].append(vu)
        if ma:
            nhom["ma_hs"] += [{**vu, "code": c} for c in v["ma_hs"] if c.startswith(ma)]
        for s in v["nha_sx"]:
            if co(s["ten"]):
                nhom["nha_sx"].append({**vu, **_dong_sx(s)})
            nhom["cong_ty_tm"] += [{**vu, **_dong_sx(s), "ten": c, "nha_sx": s["ten"]} for c in s["cong_ty_tm"] if co(c)]
        nhom["quy_cach"] += [{**vu, "noi_dung": f"{x['ten']}: {x['gia_tri']}"} for x in v["quy_cach"]
                             if co(x["gia_tri"]) or co(x["ten"])]
        for x in v["loai_tru"]:
            if x["kieu"] == "mac_thep":
                if co(x["mac_thep"]):
                    nhom["mac_thep"].append({**vu, **x})
                if co(x["tieu_chuan"]):
                    nhom["tieu_chuan"].append({**vu, **x})
            elif co(x.get("noi_dung")):
                nhom["loai_tru"].append({**vu, "noi_dung": x["noi_dung"], "thu_tuc": x.get("thu_tuc")})
        so_qd = {v.get("so_hieu")} | {b["so_hieu"] for b in v.get("van_ban", [])}
        nhom["so_qd"] += [{**vu, "so_hieu": s} for s in sorted(x for x in so_qd if co(x))]
    return [{"kieu": x, "tong": len(ds), "ket_qua": ds} for x, ds in nhom.items()
            if ds and (not kieu or kieu == x)]


def trung_ma(kho):
    """{mã 8 số: [mã vụ…]} cho mọi mã thuộc TỪ HAI vụ đang áp trở lên.

    Không phải lỗi dữ liệu (vd AD20 và vụ chống lẩn tránh AC03.AD20 cùng mã; que
    hàn và dây hàn của QĐ 1624 chung 3 mã 8311) — nhưng người khai phải chọn đúng
    vụ theo MÔ TẢ hàng, nên phải được nhắc mỗi khi tính thuế những mã này."""
    gom = {}
    for v in kho["vu_viec"]:
        if dang_ap(v):
            for c in v["ma_hs"]:
                gom.setdefault(c, []).append(v["ma_vu_viec"])
    return {c: ds for c, ds in sorted(gom.items()) if len(ds) > 1}


_PHU = r"(son|ma|trang|dat phu|phu(?! dau)|vecni|plastic)"
_KHONG_PHU = re.compile(r"\b(khong|chua)( duoc)? " + _PHU + r"\b")
_CO_PHU = re.compile(r"\b(da |duoc )?" + _PHU + r"\b")


def lech_phu(dac_tinh, mo_ta_ma):
    """So đặc tính người dùng khai ('đã sơn lót', 'chưa mạ'…) với mô tả của mã HS về
    phủ/mạ/tráng/sơn. Trả câu cảnh báo, hoặc '' khi không lệch / không đủ dữ kiện.

    CHỈ là gợi ý soát lại mã — không kết luận phân loại (việc đó theo Chú giải + GRI).
    Bài học 25-09: hàng 'đã sơn lót' mà tra mã 7208 (chưa phủ) thì bỏ sót vụ CBPG
    của mã đúng 7210.70 (ER01.AD04)."""
    t = " ".join(bo_dau(dac_tinh).replace(",", " ").split())
    if not t:
        return ""
    khong = bool(_KHONG_PHU.search(t))
    co = bool(_CO_PHU.search(_KHONG_PHU.sub(" ", t).replace("phu dau", " ")))
    m = bo_dau(mo_ta_ma)
    ma_chua = "chua dat phu" in m or "chua duoc dat phu" in m or "not clad" in m
    ma_da = not ma_chua and ("da dat phu" in m or "duoc son" in m or "clad, plated or coated" in m
                             or "da phu" in m or "duoc ma" in m or "da ma" in m)
    if co and not khong and ma_chua:
        return ("! Hàng khai là ĐÃ sơn/mạ/tráng/phủ nhưng mã này thuộc nhóm CHƯA dát phủ, phủ, mạ, tráng "
                "— soát lại mã HS (thép cán phẳng đã sơn/mạ thường thuộc 7210/7212), vụ CBPG có thể khác hẳn.")
    if khong and not co and ma_da:
        return ("! Hàng khai là CHƯA sơn/mạ/tráng/phủ nhưng mã này thuộc nhóm ĐÃ dát phủ, phủ, mạ, tráng "
                "— soát lại mã HS.")
    return ""


def _dong_sx(s):
    return {"ten": s["ten"], "nuoc": s["nuoc"], "muc_thue": s["muc_thue"], "khong_ap": s["khong_ap"]}
