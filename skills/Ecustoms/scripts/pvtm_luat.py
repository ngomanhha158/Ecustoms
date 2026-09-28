# -*- coding: utf-8 -*-
# TỰ SINH bởi scripts/chep_luat.py từ ILMSv2 backend/app/services/pvtm.py @ 3e382d2. KHÔNG SỬA TAY —
# ILMS đổi luật thì chạy lại chep_luat.py rồi kiem_khop.py.
"""Phòng vệ thương mại (CBPG, chống lẩn tránh…) — luật thuần, không chạm CSDL.

Bản vẽ: docs/PHASE_PVTM_CBPG_KIEN_TRUC.md (CEO duyệt 23-09-2026).

Các luật viết MỘT chỗ ở đây, router và tool TruePilot chỉ gọi:
- `sql_dang_ap()`      : vụ nào đang áp (không lưu cột, tính khi đọc).
- `chuan_ten_cong_ty()`: so tên công ty sau khi bỏ hậu tố pháp nhân.
- `tieu_de()`          : tiêu đề hồ sơ vụ theo Mô tả hàng hóa của QĐ.
- `tinh_muc_thue()`    : thủ tục 3 bước ghi trong mọi QĐ (C/O → nhà SX → nhà XK),
                         đi trước là bước loại trừ theo mác thép + tiêu chuẩn.
- `soat_quy_cach()`    : (phase138, docs/PHASE134_PVTM_SOAT_LO_KIEN_TRUC.md) lô nằm trong
                         phạm vi quy cách của vụ không, và điều kiện đi kèm loại trừ
                         (1959/QĐ-BCT chỉ loại trừ mác thép với hàng DẠNG TẤM…).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

from luat_nen import bo_dau  # ILMS: services/chong_trung.bo_dau
from luat_nen import la_ma_hs  # ILMS: services/tra_cuu.la_ma_hs

LOAI = ("cbpg", "chong_lan_tranh", "chong_tro_cap", "tu_ve")
GIAI_DOAN = ("tam_thoi", "chinh_thuc", "ra_soat", "het_hieu_luc", "cham_dut")
VAI_VAN_BAN = ("goc", "sua_doi", "gia_han", "ra_soat", "cham_dut")
KIEU_LOAI_TRU = ("mo_ta", "mac_thep", "ma_hs", "vu_khac")
GIAI_DOAN_CON_AP = ("tam_thoi", "chinh_thuc", "ra_soat")
# phase138: thông số quy cách máy so được, loại điều kiện đi kèm loại trừ, và 4 kết luận.
KHOA_QUY_CACH = ("day", "rong", "carbon", "loi", "dang")
LOAI_DIEU_KIEN = ("mac_thep_chi_khi", "loai_tru_quy_cach", "ke_thua_mac_thep", "ho_so_loai_tru")
NHAN_KHOA = {"day": "Độ dày", "rong": "Chiều rộng", "carbon": "Hàm lượng carbon", "loi": "Đường kính lõi",
             "dang": "Dạng (tấm/cuộn)"}
DON_VI = {"day": "mm", "rong": "mm", "carbon": "%", "loi": "mm"}
NHAN_DANG = {"tam": "tấm", "cuon": "cuộn"}
DANG = tuple(NHAN_DANG)
NGAY_CANH_BAO, NGAY_CANH_BAO_TOI_DA = 90, 730   # GET /canh-bao và tool canh_bao_pvtm dùng chung
CHUA_DOI_CHIEU = "Dữ liệu vụ này chưa được đối chiếu với bản giấy — kiểm lại QĐ trước khi khai."
NHAN_KET_LUAN = {"ap": "Bị áp", "khong_ap": "Không áp", "khong_thuoc_pham_vi": "Ngoài phạm vi vụ",
                 "chua_du": "Chưa đủ dữ liệu"}

NHAN_VAI_VAN_BAN = {"goc": "Quyết định gốc", "sua_doi": "Sửa đổi", "gia_han": "Gia hạn",
                    "ra_soat": "Rà soát", "cham_dut": "Chấm dứt"}
# CEO 24-09: màn Tra cứu gọi vụ chống lẩn tránh là "Chống bán phá giá" (mã loai giữ
# nguyên để còn tách được khi cần).
NHAN_LOAI = {"cbpg": "Chống bán phá giá", "chong_lan_tranh": "Chống bán phá giá",
             "chong_tro_cap": "Chống trợ cấp", "tu_ve": "Tự vệ"}
NHAN_GIAI_DOAN = {"tam_thoi": "Tạm thời", "chinh_thuc": "Chính thức", "ra_soat": "Đang rà soát",
                  "het_hieu_luc": "Hết hiệu lực", "cham_dut": "Chấm dứt"}
# Tám loại khóa của ô tìm thống nhất — thứ tự là thứ tự chip trên màn hình.
NHAN_KIEU_TIM = {"mat_hang": "Mặt hàng", "ma_hs": "Mã HS", "nha_sx": "Nhà sản xuất",
                 "cong_ty_tm": "Công ty thương mại", "quy_cach": "Quy cách",
                 "mac_thep": "Mác thép", "tieu_chuan": "Tiêu chuẩn",
                 "so_qd": "Số quyết định", "loai_tru": "Loại trừ"}
TEN_NUOC = {"CN": "Trung Quốc", "KR": "Hàn Quốc", "IN": "Ấn Độ", "MY": "Malaysia", "TW": "Đài Loan",
            "ID": "Indonesia", "TH": "Thái Lan", "JP": "Nhật Bản", "US": "Hoa Kỳ", "VN": "Việt Nam"}


# Tên nước người dùng / TruePilot hay gõ -> ISO-2. Khóa đã bỏ dấu, hạ chữ.
_TEN_KHAC = {"china": "CN", "tq": "CN", "korea": "KR", "south korea": "KR", "han quoc": "KR", "hq": "KR",
             "india": "IN", "an do": "IN", "taiwan": "TW", "dai loan": "TW", "thailand": "TH", "thai lan": "TH",
             "japan": "JP", "nhat": "JP", "nhat ban": "JP", "usa": "US", "my": "US", "hoa ky": "US"}


def chuan_nuoc(v: str | None) -> str | None:
    """'kr' / ' KR ' / 'Hàn Quốc' / 'Korea' -> 'KR'; rỗng -> None (không có C/O).
    Gõ tên lạ thì BÁO LỖI (ValueError), không đoán — đoán sai là ra 'không áp 0%'."""
    t = (v or "").strip()
    if not t:
        return None
    if len(t) == 2 and t.isascii() and t.isalpha():
        return t.upper()
    k = " ".join(bo_dau(t).replace(".", " ").split())
    ma = {bo_dau(ten): m for m, ten in TEN_NUOC.items()}.get(k) or _TEN_KHAC.get(k)
    if not ma:
        raise ValueError(f"Không nhận ra nước '{t}' — nhập mã ISO 2 chữ (CN, KR…) hoặc tên nước")
    return ma


def ma_hs_8(v: str | None) -> str | None:
    """'7210.49.11' -> '72104911'; không đủ 8 số hoặc lẫn chữ -> None."""
    d = la_ma_hs(v or "")
    return d if d and len(d) == 8 else None


def sql_dang_ap(bang: str = "v") -> str:
    """Vị từ SQL "vụ đang áp hôm nay" — MỘT định nghĩa cho mọi câu truy vấn."""
    gd = ", ".join(f"'{g}'" for g in GIAI_DOAN_CON_AP)
    return (f"({bang}.giai_doan IN ({gd}) AND {bang}.hieu_luc_tu <= CURRENT_DATE"
            f" AND ({bang}.hieu_luc_den IS NULL OR {bang}.hieu_luc_den >= CURRENT_DATE))")


# ---------------------------------------------------------------- chuẩn hóa
_HAU_TO = re.compile(
    r"\b(co\.?,?\s*ltd\.?|company\s+limited|co\.?|ltd\.?|limited|corporation|corp\.?|inc\.?|"
    r"pte\.?|plc|llc|jsc|gmbh|s\.?a\.?|company)\b")


def chuan_ten_cong_ty(ten: str | None) -> str:
    """'LX International Corp.' == 'lx international' == 'LX INTERNATIONAL CORPORATION'."""
    t = bo_dau(ten or "")
    t = _HAU_TO.sub(" ", t)
    t = re.sub(r"[^0-9a-z&]+", " ", t)
    return " ".join(t.split())


def chuan_mac_thep(mac: str | None) -> str:
    """Bỏ khoảng trắng, hạ chữ: 'DX57D + Z' == 'dx57d+z'."""
    return re.sub(r"\s+", "", (mac or "")).lower()


# Bản OCR hay trộn chữ Nga với chữ La-tinh trông y hệt: 'ГOCT' (Г Nga + OCT La-tinh)
# phải khớp 'GOST' người khai gõ. Chỉ đổi đúng chữ viết tắt này, không phiên âm cả câu.
_GOST = re.compile(r"[ГгGg][OoОо][CcСсSs][TtТт]")


def _chuan_tc(tc: str | None) -> str:
    return _GOST.sub("gost", re.sub(r"\s+", " ", (tc or "")).strip()).lower()


def khop_tieu_chuan(trong_qd: str, cua_lo: str | None) -> bool:
    """QĐ ghi năm ('EN 10346:2024') thì phải khớp cả năm; không ghi năm ('GB/T',
    'ASTM A131') thì lô khớp khi bắt đầu bằng đúng chuỗi ấy (QĐ 2310 mục 5)."""
    qd, lo = _chuan_tc(trong_qd), _chuan_tc(cua_lo)
    if not qd or not lo:
        return False
    if ":" in qd:   # có năm -> khớp tuyệt đối, nhưng không vấp khoảng trắng ('EN 10346: 2024')
        return qd.replace(" ", "") == lo.replace(" ", "")
    return lo == qd or lo.startswith(qd + " ") or lo.startswith(qd + ":") or lo.startswith(qd + "-")


# "Hàng hóa … là một số sản phẩm " / "Một số sản phẩm " / "Sản phẩm " — dò trên bản bo_dau.
_CAU_DAN = re.compile(r"^(hang hoa[^.;:]*? la )?(mot so |cac )?san pham ")


def tieu_de(mo_ta: str | None, ten_hang: str) -> str:
    """Tiêu đề hồ sơ vụ theo "Mô tả hàng hóa" của QĐ (CEO 27-09), không theo tên hàng rút gọn.
    Chỉ bỏ câu dẫn, còn lại nguyên văn QĐ; chưa có mô tả -> tên hàng. Dò trên bo_dau để
    "hóa"/"hoá" và NFC/NFD cùng khớp; NFC trước để hai bản dài bằng nhau mà cắt."""
    mt = " ".join(unicodedata.normalize("NFC", mo_ta or "").split())
    dan = _CAU_DAN.match(bo_dau(mt))
    than = mt[dan.end():] if dan else mt
    return than[:1].upper() + than[1:] if than else ten_hang


def so(v: Any) -> float | None:
    return None if v is None else float(v) if isinstance(v, (Decimal, int, float)) else float(str(v).replace(",", "."))


# ---------------------------------------------------------------- tính thuế
@dataclass
class Buoc:
    buoc: str
    ket_qua: str
    dat: bool | None      # True = qua bước, False = dừng ở bước này, None = chỉ thông tin
    can_cu: str = ""


@dataclass
class KetQua:
    ma_vu_viec: str
    ket_luan: str          # 'ap' | 'khong_ap' | 'khong_thuoc_pham_vi' | 'chua_du' (NHAN_KET_LUAN)
    muc_thue: float | None
    cac_buoc: list[Buoc] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)
    nha_sx_khop: str | None = None   # tên nhà SX trong QĐ đã khớp — màn hình tô dòng theo tên này
    thieu: list[str] = field(default_factory=list)          # thông số còn thiếu (nhãn) — 'chua_du' hỏi đúng các ô này
    thieu_khoa: list[str] = field(default_factory=list)     # cùng danh sách, dạng khóa (day/rong/…) — màn hình đưa con trỏ tới ô
    tu_doi_chieu: list[str] = field(default_factory=list)   # quy cách chữ máy không so được: người tự đối chiếu

    def dict(self) -> dict[str, Any]:
        return asdict(self)


def _hang_ngang(nha_sx: list[dict], chon: dict) -> list[dict]:
    """Các nhà SX cùng một hàng ngang trong bảng mức thuế (cùng 'nhom')."""
    if not chon.get("nhom"):
        return [chon]
    return [n for n in nha_sx if n.get("nhom") == chon["nhom"] and n["nuoc"] == chon["nuoc"]]


def tinh_muc_thue(vu: dict[str, Any], lo: dict[str, Any]) -> KetQua:
    """Soát quy cách (phase138) rồi `_tinh`. Bị áp mà kho chưa có con số (QĐ gốc chưa
    nhập bảng mức thuế) thì nói thẳng, không trả số — số sai là rủi ro thật cho khách."""
    kq = _soat_roi_tinh(vu, lo)
    if kq.ket_luan == "ap" and kq.muc_thue is None:
        kq.canh_bao.append("Kho chưa có mức thuế của trường hợp này — tra bảng mức thuế trong QĐ gốc.")
    return kq


# ---------------------------------------------------------------- soát quy cách (phase138)
_SO = r"\d+(?:[.,]\d+)*"
_TOAN_TU = [  # dài trước ngắn: "nho hon hoac bang" không được bắt thành "nho hon"
    (r"lon hon hoac bang|khong nho hon|>=|≥", ">="),
    (r"nho hon hoac bang|khong qua|toi da|<=|≤", "<="),
    (r"lon hon|tren|>", ">"),
    (r"nho hon|duoi|<", "<"),
]
# Tên quy cách (đã bỏ dấu) -> khóa. "Thành phần lõi" (dây hàn) đọc riêng phần C.
_TEN_QUY_CACH = {"do day": "day", "chieu rong": "rong", "be rong": "rong", "ham luong carbon": "carbon",
                 "duong kinh loi": "loi", "dang": "dang"}


def doc_so(t: str) -> float:
    """MỘT bộ đọc số cho cả chữ QĐ lẫn ô người nhập: '1.880' -> 1880 (chấm ngăn nghìn);
    '0,108' -> 0.108; '0.30' / '0.300' -> 0.3."""
    if "," in t:
        return float(t.replace(".", "").replace(",", "."))
    if re.fullmatch(r"[1-9]\d{0,2}(?:\.\d{3})+", t):   # '0.300' là số thập phân, không phải ngăn nghìn
        return float(t.replace(".", ""))
    return float(t)


def khoang(text: str) -> list[tuple[str, float]]:
    """Chuỗi quy cách trong QĐ -> [(toán tử, giá trị)]; không có số ('Bất kể') -> [].
    Có dung sai '+/- 0,2' thì nới hai đầu (1624/QĐ-BCT: que hàn 2,0–4,0 mm ± 0,2)."""
    t = bo_dau(text).replace("±", "+/-")
    tol = 0.0
    m = re.search(r"dung sai\s*\+\s*/\s*-\s*(" + _SO + ")", t)
    if m:
        tol, t = doc_so(m.group(1)), t[:m.start()]
    m = re.search(r"(?:tu\s*)?(" + _SO + r")\s*(?:mm|%)?\s*(?:den|–|-)\s*(" + _SO + ")", t)
    if m:   # "trên 3 mm đến 10 mm" / "lớn hơn 3 đến 10": đầu dưới là biên MỞ
        mo = re.search(r"(?:tren|lon hon)\s*$", t[:m.start()]) and not re.search(r"hoac bang\s*$", t[:m.start()])
        return [(">" if mo else ">=", doc_so(m.group(1)) - tol), ("<=", doc_so(m.group(2)) + tol)]
    m = re.search(r"tu\s*(" + _SO + r")\s*(?:mm|%)?\s*tro len", t)
    if m:
        return [(">=", doc_so(m.group(1)))]
    ds: list[tuple[str, float]] = []
    for mau, op in _TOAN_TU:
        ds += [(op, doc_so(x.group(1))) for x in re.finditer(r"(?:" + mau + r")\s*(" + _SO + ")", t)]
        t = re.sub(r"(?:" + mau + r")\s*" + _SO, " ", t)   # đọc rồi thì xóa, tránh toán tử ngắn bắt lại
    return ds


def _dat(v: float, dk: tuple[str, float]) -> bool:
    op, x = dk
    return {">=": v >= x - 1e-9, "<=": v <= x + 1e-9, ">": v > x + 1e-9, "<": v < x - 1e-9}[op]


def chuan_dang(v: str | None) -> str | None:
    """'tấm' / 'tam' / 'plate' -> 'tam'; 'cuộn' / 'coil' -> 'cuon'; rỗng -> None; lạ -> ValueError."""
    t = bo_dau((v or "").strip())
    if not t:
        return None
    d = {"tam": "tam", "plate": "tam", "sheet": "tam", "cuon": "cuon", "coil": "cuon"}.get(t)
    if not d:
        raise ValueError(f"Dạng hàng phải là tấm hoặc cuộn, nhận '{v}'")
    return d


def _quy_cach_so(vu: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """quy_cach của vụ -> ({khóa: {dk: [(op, v)], dang: set, goc: 'Tên: giá trị'}}, [quy cách chữ]).
    Cột số (phase138: khoa/tu/den/…) người nhập đã soát thì DÙNG TRƯỚC; chưa có thì đọc chữ."""
    so_: dict[str, dict[str, Any]] = {}
    chu: list[str] = []
    for q in vu.get("quy_cach", []):
        goc = f"{q['ten']}: {q['gia_tri']}"
        khoa = q.get("khoa")
        if khoa == "dang" and q.get("dang_cho_phep"):
            so_["dang"] = {"dang": set(q["dang_cho_phep"]), "goc": goc}
            continue
        if khoa in DON_VI and (q.get("tu") is not None or q.get("den") is not None):
            dk = ([(">=" if q.get("tu_bao_gom", True) else ">", so(q["tu"]))] if q.get("tu") is not None else []) \
                + ([("<=" if q.get("den_bao_gom", True) else "<", so(q["den"]))] if q.get("den") is not None else [])
            so_[khoa] = {"dk": dk, "goc": goc}
            continue
        ten = bo_dau(q["ten"]).strip()
        if ten == "thanh phan loi":
            for doan in q["gia_tri"].split(";"):
                if bo_dau(doan).strip().startswith("c "):
                    so_["carbon"] = {"dk": khoang(doan.strip()[1:]), "goc": f"{q['ten']}: {doan.strip()}"}
            chu.append(goc)
            continue
        k = _TEN_QUY_CACH.get(ten)
        if k == "dang":
            dang = {d for d, nhan in NHAN_DANG.items() if nhan in q["gia_tri"].lower()}
            if dang:
                so_["dang"] = {"dang": dang, "goc": goc}
                continue
        elif k and (dk := khoang(q["gia_tri"])):
            so_[k] = {"dk": dk, "goc": goc}
            continue
        chu.append(goc)
    return so_, chu


def khoa_can_nhap(vu: dict[str, Any]) -> list[str]:
    """Thông số lô mà vụ này dùng tới (phạm vi + điều kiện đi kèm) — màn hình chỉ hiện đúng các ô ấy."""
    k = set(_quy_cach_so(vu)[0])
    for d in vu.get("dieu_kien") or []:
        k |= {x for x in d.get("dieu_kien", {}) if x in KHOA_QUY_CACH}
    return [x for x in KHOA_QUY_CACH if x in k]


def soat_quy_cach(vu: dict[str, Any], lo: dict[str, Any]) -> tuple[list[Buoc], bool, list[str], list[str]]:
    """-> (các bước phạm vi, lô NGOÀI phạm vi?, KHÓA thông số chưa nhập, quy cách chữ tự đối chiếu)."""
    can_cu = f"{vu.get('so_hieu') or vu['ma_vu_viec']} — mô tả hàng hóa"
    so_, chu = _quy_cach_so(vu)
    buoc, ngoai, thieu = [], False, []
    for khoa, x in so_.items():
        gt = lo.get(khoa)
        if gt in (None, ""):
            thieu.append(khoa)
            continue
        if khoa == "dang":
            ok, noi = gt in x["dang"], f"lô dạng {NHAN_DANG[gt]}"
        else:
            ok, noi = all(_dat(so(gt), d) for d in x["dk"]), f"lô {so(gt):g} {DON_VI[khoa]}"
        ngoai |= not ok
        buoc.append(Buoc(f"Phạm vi — {NHAN_KHOA[khoa]}", f"{noi}; QĐ: {x['goc']}", ok, can_cu))
    return buoc, ngoai, thieu, chu


def _khop_dieu_kien(dk: dict[str, Any], lo: dict[str, Any]) -> tuple[str, int, list[str]]:
    """Điều kiện loại trừ theo quy cách -> ('khop' | 'truot' | 'thieu', số điều kiện đã biết, khóa thiếu)."""
    biet, thieu = 0, []
    for khoa, yeu_cau in dk.items():
        v = lo.get(khoa)
        if v in (None, ""):
            thieu.append(khoa)
            continue
        biet += 1
        if not (v == yeu_cau if khoa == "dang" else _dat(so(v), (yeu_cau[0], float(yeu_cau[1])))):
            return "truot", biet, thieu
    return ("thieu" if thieu else "khop"), biet, thieu


def _soat_roi_tinh(vu: dict[str, Any], lo: dict[str, Any]) -> KetQua:
    """Bước 0 (phase138) bọc quanh `_tinh`. Thứ tự: phạm vi quy cách -> loại trừ theo quy cách
    -> `_tinh` -> điều kiện đi kèm loại trừ mác thép (dạng tấm, kế thừa vụ khác, hồ sơ).
    Mọi nhánh đi qua MỘT lối ra `_xong` (bước phạm vi, thông số thiếu, cảnh báo giả định)."""
    ma = vu["ma_vu_viec"]
    buoc_pv, ngoai, thieu, chu = soat_quy_cach(vu, lo)
    tu_dc = chu + [x["noi_dung"] for x in vu.get("loai_tru", []) if x["kieu"] in ("mo_ta", "vu_khac") and x.get("noi_dung")]
    if ngoai:
        kq = KetQua(ma, "khong_thuoc_pham_vi", 0.0)
        if not vu.get("doi_chieu_luc"):
            kq.canh_bao.append(CHUA_DOI_CHIEU)
        return _xong(kq, buoc_pv, thieu, [])
    dk_ds = vu.get("dieu_kien") or []
    quyet_dinh = None
    for d in (x for x in dk_ds if x["loai"] == "loai_tru_quy_cach"):
        khop, biet, con_thieu = _khop_dieu_kien(d["dieu_kien"], lo)
        if khop == "khop":
            return _xong(KetQua(ma, "khong_ap", 0.0, [Buoc("Loại trừ theo quy cách", d["trich"], True, d["can_cu"])]),
                         buoc_pv, thieu, tu_dc)
        if khop == "thieu" and biet and not quyet_dinh:   # phần biết đã khớp -> thông số thiếu QUYẾT ĐỊNH kết luận
            quyet_dinh = (d, con_thieu)

    kq = _tinh(vu, lo)
    loai = {x["loai"]: x for x in dk_ds}   # kho.kiem chặn trùng: một dòng mỗi loại này
    chi_khi, ke_thua, ho_so = loai.get("mac_thep_chi_khi"), loai.get("ke_thua_mac_thep"), loai.get("ho_so_loai_tru")
    loai_mac = any(b.buoc == "Loại trừ mác thép" and b.dat for b in kq.cac_buoc)
    mac_ke_thua = None
    if not loai_mac and ke_thua and chuan_mac_thep(lo.get("mac_thep")):
        mac_ke_thua = next((x for x in ke_thua.get("loai_tru_mac", [])
                            if chuan_mac_thep(x["mac_thep"]) == chuan_mac_thep(lo.get("mac_thep"))
                            and khop_tieu_chuan(x["tieu_chuan"], lo.get("tieu_chuan"))), None)
    if loai_mac or mac_ke_thua:
        buoc_mac = [Buoc("Loại trừ mác thép", f"{mac_ke_thua['mac_thep']} theo {mac_ke_thua['tieu_chuan']} "
                         f"(danh mục loại trừ của {ke_thua['dieu_kien'].get('vu')})", True, ke_thua["can_cu"])] \
            if mac_ke_thua else kq.cac_buoc
        can = (chi_khi or {}).get("dieu_kien", {}).get("dang")
        if can and lo.get("dang") != can:
            # Chưa biết dạng / sai dạng: tính lại như không có mác. Tính lại đã ra KHÔNG ÁP (nước không bị áp,
            # loại trừ mã HS…) thì mác không còn quyết định gì — trả luôn, không hỏi thêm.
            lai = _tinh(vu, {**lo, "mac_thep": None})
            if lo.get("dang") or lai.ket_luan != "ap":
                if lo.get("dang"):
                    lai.cac_buoc.insert(0, Buoc("Loại trừ mác thép", f"chỉ loại trừ hàng dạng {NHAN_DANG[can]}; "
                                                f"lô dạng {NHAN_DANG[lo['dang']]}", False, chi_khi["can_cu"]))
                kq = lai
            else:
                kq = KetQua(ma, "chua_du", None, buoc_mac + [Buoc(
                    "Điều kiện loại trừ mác thép", f"chỉ áp dụng cho hàng dạng {NHAN_DANG[can]} — chưa nhập dạng hàng",
                    None, chi_khi["can_cu"])], lai.canh_bao)
                thieu = ["dang"] + thieu   # thông số QUYẾT ĐỊNH đứng đầu: màn hình đưa con trỏ tới đó
        else:
            kq = KetQua(ma, "khong_ap", 0.0, buoc_mac + ([Buoc("Điều kiện loại trừ mác thép", f"hàng dạng {NHAN_DANG[can]}",
                                                               True, chi_khi["can_cu"])] if can else []), kq.canh_bao)
            if ho_so:
                kq.canh_bao.append(f"Hồ sơ để được loại trừ ({ho_so['can_cu']}): {ho_so['trich']}")

    if quyet_dinh and kq.ket_luan == "ap":
        d, con_thieu = quyet_dinh
        kq.cac_buoc.append(Buoc("Loại trừ theo quy cách", f"{d['trich']} — thiếu "
                                + ", ".join(NHAN_KHOA[k] for k in con_thieu), None, d["can_cu"]))
        kq.ket_luan, kq.muc_thue = "chua_du", None
        thieu = con_thieu + thieu
    return _xong(kq, buoc_pv, thieu, tu_dc)


def _xong(kq: KetQua, buoc_pv: list[Buoc], thieu: list[str], tu_dc: list[str]) -> KetQua:
    """Lối ra chung: gắn bước phạm vi lên đầu, thông số thiếu (khử trùng), cảnh báo ÁP đang giả định."""
    kq.cac_buoc = buoc_pv + kq.cac_buoc
    kq.thieu_khoa = list(dict.fromkeys(thieu))
    kq.thieu = [NHAN_KHOA[k] for k in kq.thieu_khoa]
    kq.tu_doi_chieu = tu_dc
    if kq.thieu and kq.ket_luan == "ap":
        kq.canh_bao.append("Chưa nhập " + ", ".join(kq.thieu) + " — kết luận ÁP đang GIẢ ĐỊNH lô nằm trong "
                           "phạm vi quy cách của vụ.")
    return kq


def _tinh(vu: dict[str, Any], lo: dict[str, Any]) -> KetQua:
    """Một vụ + một lô -> mức thuế và từng bước lý do.

    vu : {ma_vu_viec, so_hieu, muc_khong_chung_tu, doi_chieu_luc,
          nuoc: [{nuoc, muc_toan_quoc}], nha_sx: [{nuoc, ten, nhom, muc_thue, khong_ap, cong_ty_tm: [..]}],
          loai_tru: [{kieu, noi_dung, mac_thep, tieu_chuan, vu_khac}]}
    lo : {nuoc_co (ISO-2 | None), nha_sx?, nha_xk?, mac_thep?, tieu_chuan?}
    """
    can_cu = vu.get("so_hieu") or vu["ma_vu_viec"]
    kq = KetQua(vu["ma_vu_viec"], "ap", None)
    if not vu.get("doi_chieu_luc"):
        kq.canh_bao.append(CHUA_DOI_CHIEU)

    # Bước 0a: loại trừ đích danh theo mã HS.
    code = ma_hs_8(lo.get("code"))
    if code and any(x["kieu"] == "ma_hs" and ma_hs_8(x.get("ma_hs")) == code for x in vu.get("loai_tru", [])):
        kq.cac_buoc.append(Buoc("Loại trừ mã HS", f"Mã {code} được loại trừ", True, f"{can_cu} — mục loại trừ"))
        kq.ket_luan, kq.muc_thue = "khong_ap", 0.0
        return kq
    # Bước 0b: loại trừ theo mác thép + tiêu chuẩn (máy phán được); loại trừ theo mô tả thì chỉ nhắc.
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

    # Bước 1: chứng từ xuất xứ.
    nuoc_ap = {n["nuoc"]: so(n.get("muc_toan_quoc")) for n in vu.get("nuoc", [])}
    moi_nuoc = not nuoc_ap   # vụ không ghi nước (thường là tự vệ) = áp cho MỌI xuất xứ
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

    # Bước 2: nhà sản xuất trên giấy chứng nhận chất lượng.
    sx = chuan_ten_cong_ty(lo.get("nha_sx"))
    chon = next((n for n in trong_nuoc if sx and chuan_ten_cong_ty(n["ten"]) == sx), None)
    if not chon:
        kq.cac_buoc.append(Buoc("Nhà sản xuất", (lo.get("nha_sx") or "Không có giấy chứng nhận") + " — không có tên trong bảng",
                                False, f"{can_cu} — bước 2"))
        kq.muc_thue = toan_quoc
        return kq
    kq.cac_buoc.append(Buoc("Nhà sản xuất", chon["ten"], True, f"{can_cu} — bước 2"))
    kq.nha_sx_khop = chon["ten"]

    # Bước 3: nhà xuất khẩu trên hợp đồng/hóa đơn — trùng nhà SX hoặc công ty TM cùng hàng ngang.
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
