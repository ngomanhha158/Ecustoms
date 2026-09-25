# -*- coding: utf-8 -*-
"""Phòng vệ thương mại (CBPG…) chạy HOÀN TOÀN trên máy — đọc data/pvtm.json.

Skill Ecustoms tách khỏi ILMSv2: ILMS chỉ là nơi ĐỒNG BỘ dữ liệu (`query_hs.py
dongbo` kéo về data/pvtm.json). Tra cứu, xem hồ sơ vụ, tính thuế đều chạy ở đây,
không cần mạng.

LUẬT TÍNH THUẾ là BẢN CHÉP của ILMSv2 `backend/app/services/pvtm.py`
(commit b96dbc9). Hai bản phải cho cùng kết quả — `scripts/kiem_khop.py` gọi
cả hai trên mọi mã HS × nhiều kiểu lô và báo lệch. ILMS đổi luật thì chép lại
khối "LUẬT" dưới đây rồi chạy kiem_khop.py.
"""
import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TEP = os.path.join(DATA, "pvtm.json")
CU_SAU_NGAY = 7   # dữ liệu cũ hơn số ngày này thì in cảnh báo

GIAI_DOAN_CON_AP = ("tam_thoi", "chinh_thuc", "ra_soat")
NHAN_LOAI = {"cbpg": "Chống bán phá giá", "chong_lan_tranh": "Chống bán phá giá",
             "chong_tro_cap": "Chống trợ cấp", "tu_ve": "Tự vệ"}
NHAN_GIAI_DOAN = {"tam_thoi": "Tạm thời", "chinh_thuc": "Chính thức", "ra_soat": "Đang rà soát",
                  "het_hieu_luc": "Hết hiệu lực", "cham_dut": "Chấm dứt"}
NHAN_KIEU_TIM = {"mat_hang": "Mặt hàng", "ma_hs": "Mã HS", "nha_sx": "Nhà sản xuất",
                 "cong_ty_tm": "Công ty thương mại", "quy_cach": "Quy cách",
                 "mac_thep": "Mác thép", "tieu_chuan": "Tiêu chuẩn",
                 "so_qd": "Số quyết định", "loai_tru": "Loại trừ"}
TEN_NUOC = {"CN": "Trung Quốc", "KR": "Hàn Quốc", "IN": "Ấn Độ", "MY": "Malaysia", "TW": "Đài Loan",
            "ID": "Indonesia", "TH": "Thái Lan", "JP": "Nhật Bản", "US": "Hoa Kỳ", "VN": "Việt Nam"}


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
    ds.sort(key=lambda v: v["hieu_luc_tu"], reverse=True)
    return sorted(ds, key=lambda v: not dang_ap(v))   # sort ổn định: giữ thứ tự ngày trong mỗi nhóm


def tinh_cho_lo(kho, lo):
    """Như ILMS pvtm_kho.tinh_cho_lo: mọi vụ ĐANG ÁP của mã HS × luật tính thuế."""
    code = ma_hs_8(lo.get("code"))
    if not code:
        raise SystemExit("Mã HS phải đủ 8 số")
    chuan_nuoc(lo.get("nuoc_co"))   # nước lạ -> báo lỗi trước, như ILMS trả 422
    ket_qua = []
    for vu in vu_theo_ma(kho, code, chi_dang_ap=True):
        ket_qua.append({**tinh_muc_thue(vu, {**lo, "code": code}).dict(), "ten_hang": vu["ten_hang"],
                        "so_hieu": vu["so_hieu"], "da_doi_chieu": vu["da_doi_chieu"]})
    return {"code": code, "bi_ap": any(k["ket_luan"] == "ap" for k in ket_qua), "vu_viec": ket_qua}


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
                nhom["loai_tru"].append({**vu, "noi_dung": x["noi_dung"]})
        so_qd = {v.get("so_hieu")} | {b["so_hieu"] for b in v.get("van_ban", [])}
        nhom["so_qd"] += [{**vu, "so_hieu": s} for s in sorted(x for x in so_qd if co(x))]
    return [{"kieu": x, "tong": len(ds), "ket_qua": ds} for x, ds in nhom.items()
            if ds and (not kieu or kieu == x)]


def _dong_sx(s):
    return {"ten": s["ten"], "nuoc": s["nuoc"], "muc_thue": s["muc_thue"], "khong_ap": s["khong_ap"]}


# ================================================================ LUẬT — chép từ ILMS services/pvtm.py
_THAY_TRUOC = str.maketrans("ĐđØøŁł", "DdOoLl")


def bo_dau(t):
    nfd = unicodedata.normalize("NFD", (t or "").translate(_THAY_TRUOC))
    return "".join(c for c in nfd if not unicodedata.combining(c)).lower()


def la_ma_hs(q):
    so = re.sub(r"[.\s]", "", (q or "").strip())
    return so if len(so) >= 2 and so.isdigit() else None


_TEN_KHAC = {"china": "CN", "tq": "CN", "korea": "KR", "south korea": "KR", "han quoc": "KR", "hq": "KR",
             "india": "IN", "an do": "IN", "taiwan": "TW", "dai loan": "TW", "thailand": "TH", "thai lan": "TH",
             "japan": "JP", "nhat": "JP", "nhat ban": "JP", "usa": "US", "my": "US", "hoa ky": "US"}


def chuan_nuoc(v):
    t = (v or "").strip()
    if not t:
        return None
    if len(t) == 2 and t.isascii() and t.isalpha():
        return t.upper()
    k = " ".join(bo_dau(t).replace(".", " ").split())
    ma = {bo_dau(ten): m for m, ten in TEN_NUOC.items()}.get(k) or _TEN_KHAC.get(k)
    if not ma:
        raise SystemExit(f"Không nhận ra nước '{t}' — nhập mã ISO 2 chữ (CN, KR…) hoặc tên nước")
    return ma


def ma_hs_8(v):
    d = la_ma_hs(v or "")
    return d if d and len(d) == 8 else None


_HAU_TO = re.compile(
    r"\b(co\.?,?\s*ltd\.?|company\s+limited|co\.?|ltd\.?|limited|corporation|corp\.?|inc\.?|"
    r"pte\.?|plc|llc|jsc|gmbh|s\.?a\.?|company)\b")


def chuan_ten_cong_ty(ten):
    t = bo_dau(ten or "")
    t = _HAU_TO.sub(" ", t)
    t = re.sub(r"[^0-9a-z&]+", " ", t)
    return " ".join(t.split())


def chuan_mac_thep(mac):
    return re.sub(r"\s+", "", (mac or "")).lower()


_GOST = re.compile(r"[ГгGg][OoОо][CcСсSs][TtТт]")


def _chuan_tc(tc):
    return _GOST.sub("gost", re.sub(r"\s+", " ", (tc or "")).strip()).lower()


def khop_tieu_chuan(trong_qd, cua_lo):
    qd, lo = _chuan_tc(trong_qd), _chuan_tc(cua_lo)
    if not qd or not lo:
        return False
    if ":" in qd:
        return qd.replace(" ", "") == lo.replace(" ", "")
    return lo == qd or lo.startswith(qd + " ") or lo.startswith(qd + ":") or lo.startswith(qd + "-")


def so(v):
    return None if v is None else float(v) if isinstance(v, (int, float)) else float(str(v).replace(",", "."))


@dataclass
class Buoc:
    buoc: str
    ket_qua: str
    dat: object
    can_cu: str = ""


@dataclass
class KetQua:
    ma_vu_viec: str
    ket_luan: str
    muc_thue: object
    cac_buoc: list = field(default_factory=list)
    canh_bao: list = field(default_factory=list)
    nha_sx_khop: object = None

    def dict(self):
        return asdict(self)


def _hang_ngang(nha_sx, chon):
    if not chon.get("nhom"):
        return [chon]
    return [n for n in nha_sx if n.get("nhom") == chon["nhom"] and n["nuoc"] == chon["nuoc"]]


def tinh_muc_thue(vu, lo):
    kq = _tinh(vu, lo)
    if kq.ket_luan == "ap" and kq.muc_thue is None:
        kq.canh_bao.append("Kho chưa có mức thuế của trường hợp này — tra bảng mức thuế trong QĐ gốc.")
    return kq


def _tinh(vu, lo):
    can_cu = vu.get("so_hieu") or vu["ma_vu_viec"]
    kq = KetQua(vu["ma_vu_viec"], "ap", None)
    if not vu.get("doi_chieu_luc"):
        kq.canh_bao.append("Dữ liệu vụ này chưa được đối chiếu với bản giấy — kiểm lại QĐ trước khi khai.")

    code = ma_hs_8(lo.get("code"))
    if code and any(x["kieu"] == "ma_hs" and ma_hs_8(x.get("ma_hs")) == code for x in vu.get("loai_tru", [])):
        kq.cac_buoc.append(Buoc("Loại trừ mã HS", f"Mã {code} được loại trừ", True, f"{can_cu} — mục loại trừ"))
        kq.ket_luan, kq.muc_thue = "khong_ap", 0.0
        return kq
    mac = chuan_mac_thep(lo.get("mac_thep"))
    if mac:
        cung_mac = [x for x in vu.get("loai_tru", []) if x["kieu"] == "mac_thep" and chuan_mac_thep(x["mac_thep"]) == mac]
        khop = [x for x in cung_mac if khop_tieu_chuan(x["tieu_chuan"], lo.get("tieu_chuan"))]
        if khop:
            kq.cac_buoc.append(Buoc("Loại trừ mác thép", f"{khop[0]['mac_thep']} theo {khop[0]['tieu_chuan']}", True,
                                    f"{can_cu} — danh mục mác thép loại trừ"))
            kq.ket_luan, kq.muc_thue = "khong_ap", 0.0
            return kq
        if cung_mac:
            kq.cac_buoc.append(Buoc("Loại trừ mác thép",
                                    f"Mác {cung_mac[0]['mac_thep']} chỉ được loại trừ khi theo {cung_mac[0]['tieu_chuan']}",
                                    False, can_cu))
    mo_ta = [x["noi_dung"] for x in vu.get("loai_tru", []) if x["kieu"] in ("mo_ta", "vu_khac") and x.get("noi_dung")]
    if mo_ta:
        kq.canh_bao.append(f"Đối chiếu {len(mo_ta)} trường hợp loại trừ theo mô tả hàng hóa trong {can_cu}.")

    nuoc_ap = {n["nuoc"]: so(n.get("muc_toan_quoc")) for n in vu.get("nuoc", [])}
    moi_nuoc = not nuoc_ap
    nuoc_co = chuan_nuoc(lo.get("nuoc_co"))
    if not nuoc_co:
        kq.muc_thue = so(vu.get("muc_khong_chung_tu"))
        if kq.muc_thue is None:
            kq.muc_thue = max((v for v in nuoc_ap.values() if v is not None), default=None)
        kq.cac_buoc.append(Buoc("Chứng từ xuất xứ", "Không nộp C/O", False, f"{can_cu} — bước 1"))
        return kq
    if not moi_nuoc and nuoc_co not in nuoc_ap:
        kq.cac_buoc.append(Buoc("Chứng từ xuất xứ", f"C/O {TEN_NUOC.get(nuoc_co, nuoc_co)} — không thuộc nước bị áp",
                                True, f"{can_cu} — bước 1"))
        kq.ket_luan, kq.muc_thue = "khong_ap", 0.0
        return kq
    kq.cac_buoc.append(Buoc("Chứng từ xuất xứ", f"C/O {TEN_NUOC.get(nuoc_co, nuoc_co)}", True, f"{can_cu} — bước 1"))
    toan_quoc = so(vu.get("muc_khong_chung_tu")) if moi_nuoc else nuoc_ap[nuoc_co]
    trong_nuoc = [n for n in vu.get("nha_sx", []) if n["nuoc"] == nuoc_co]

    sx = chuan_ten_cong_ty(lo.get("nha_sx"))
    chon = next((n for n in trong_nuoc if sx and chuan_ten_cong_ty(n["ten"]) == sx), None)
    if not chon:
        kq.cac_buoc.append(Buoc("Nhà sản xuất", (lo.get("nha_sx") or "Không có giấy chứng nhận") + " — không có tên trong bảng",
                                False, f"{can_cu} — bước 2"))
        kq.muc_thue = toan_quoc
        return kq
    kq.cac_buoc.append(Buoc("Nhà sản xuất", chon["ten"], True, f"{can_cu} — bước 2"))
    kq.nha_sx_khop = chon["ten"]

    hang = _hang_ngang(trong_nuoc, chon)
    hop_le = {chuan_ten_cong_ty(n["ten"]) for n in hang}
    hop_le |= {chuan_ten_cong_ty(c) for n in hang for c in n.get("cong_ty_tm", [])}
    xk = chuan_ten_cong_ty(lo.get("nha_xk"))
    if xk and xk in hop_le:
        kq.cac_buoc.append(Buoc("Nhà xuất khẩu", lo["nha_xk"], True, f"{can_cu} — bước 3"))
        if chon.get("khong_ap"):
            kq.ket_luan, kq.muc_thue = "khong_ap", 0.0
        else:
            kq.muc_thue = so(chon.get("muc_thue"))
        return kq
    kq.cac_buoc.append(Buoc("Nhà xuất khẩu", (lo.get("nha_xk") or "Chưa nhập") + " — không cùng hàng ngang với nhà SX",
                            False, f"{can_cu} — bước 3"))
    kq.muc_thue = toan_quoc
    return kq
