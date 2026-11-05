# Chép nguyên văn ILMS services/kiem_tra_dong.py (commit 30daf4c7) — KHÔNG SỬA TAY:
# sửa ở ILMS rồi chạy scripts/chep_luat_ilms.py.
"""Kiểm tra nhanh MỘT dòng hàng tờ khai — luật thuần, không chạm CSDL (CEO duyệt mẫu 05-11-2026).

Bản vẽ: skill hqskills docs/superpowers/specs/2026-11-05-kiemtra-phieu-design.md (phương án A, bản sửa 2).

Một luật một chỗ: tệp này là nguồn duy nhất; skill hqskills chép NGUYÊN VĂN bằng chep_luat_ilms.py.
Dữ liệu biểu thuế đi vào qua hai hàm do nơi gọi cấp (ILMS: bảng hs_codes; skill: hs_tree.json):
    tra_ma(code) -> {code, desc_vn, desc_en, mfn, thue_tt, fta: dict} | None
    ma_con(tien_to) -> [mã 8 số có thật]
Kết quả phòng vệ thương mại truyền vào sẵn (dict của pvtm_kho.tinh_cho_lo / pvtm_local.tinh_cho_lo).

Phạm vi bản 1: thép Chương 72 — soát hợp kim theo Chú giải 1(f), mã nghi ngờ hợp kim <-> không hợp kim.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from pvtm_local import DON_VI, NHAN_DANG, NHAN_KHOA, _dat, bo_dau, chuan_dang, chuan_nuoc, doc_so, khoang  # noqa: F401

# ---------------------------------------------------------------- Chú giải 1(f) Chương 72
# "Thép hợp kim khác": chứa ít nhất MỘT nguyên tố đạt ngưỡng (% khối lượng). Chép từ Chú giải
# Chương 72 (TT 31/2022/TT-BTC) — kho hs_chapter_notes; đổi Chú giải thì sửa ở đây.
NGUONG_HOP_KIM: dict[str, float] = {
    "Al": 0.3, "B": 0.0008, "Cr": 0.3, "Co": 0.3, "Cu": 0.4, "Pb": 0.4, "Mn": 1.65, "Mo": 0.08,
    "Ni": 0.3, "Nb": 0.06, "Si": 0.6, "Ti": 0.05, "W": 0.3, "V": 0.1, "Zr": 0.05,
    # "Các nguyên tố khác tính cho mỗi nguyên tố từ 0,1% trở lên (trừ lưu huỳnh, phốt pho, carbon và nitơ)"
    "Bi": 0.1, "Se": 0.1, "Te": 0.1, "Sn": 0.1, "Sb": 0.1, "As": 0.1, "Ca": 0.1, "Mg": 0.1, "La": 0.1, "Ce": 0.1,
}
# Chú giải 1(e): thép không gỉ — carbon ≤ 1,2% và crôm ≥ 10,5% (nhóm 72.18–72.23), tách khỏi "hợp kim khác".
NGUONG_KHONG_GI = {"Cr": 10.5, "C_toi_da": 1.2}
TEN_NGUYEN_TO = {"Al": "Nhôm", "B": "Bo", "Cr": "Crôm", "Co": "Coban", "Cu": "Đồng", "Pb": "Chì", "Mn": "Mangan",
                 "Mo": "Molybđen", "Ni": "Nikel", "Nb": "Niobi", "Si": "Silic", "Ti": "Titan", "W": "Vonfram",
                 "V": "Vanadi", "Zr": "Zircon", "C": "Carbon", "P": "Phốt pho", "S": "Lưu huỳnh", "N": "Nitơ",
                 "Bi": "Bitmut", "Se": "Selen", "Te": "Telu", "Sn": "Thiếc", "Sb": "Antimon", "As": "Asen",
                 "Ca": "Canxi", "Mg": "Magie", "La": "Lantan", "Ce": "Xeri"}
NHOM_KHONG_HOP_KIM = ("7208", "7209", "7210", "7211", "7212", "7213", "7214", "7215", "7216", "7217")
NHOM_HOP_KIM = ("7224", "7225", "7226", "7227", "7228", "7229")
NHOM_KHONG_GI = ("7218", "7219", "7220", "7221", "7222", "7223")
# Nước xuất xứ -> các cột FTA của Biểu thuế (một chỗ cho cả ô hiển thị lẫn phép so thuế suất khai).
FTA_THEO_NUOC: dict[str, tuple[str, ...]] = {"CN": ("acfta",), "KR": ("akfta", "vkfta"), "JP": ("ajcep", "vjepa"),
                                             "IN": ("aifta",)}
# Ghép cặp không hợp kim <-> hợp kim cùng hình dạng / mức gia công (bản vẽ §3).
_CAP_XUOI: dict[str, tuple[str, ...]] = {
    "7208": ("722530", "722540"), "7209": ("722550",), "7210": ("722591", "722592", "722599"),
    "7211": ("722691", "722692", "722699"), "7212": ("722699",), "7213": ("7227",), "7214": ("722830",),
    "7216": ("722870",),
}
_CAP_NGUOC: dict[str, tuple[str, ...]] = {}
for _kh, _ds in _CAP_XUOI.items():
    for _hk in _ds:
        _CAP_NGUOC[_hk] = _CAP_NGUOC.get(_hk, ()) + (_kh,)
CAP_NHOM: dict[str, tuple[str, ...]] = {**_CAP_XUOI, **_CAP_NGUOC}
_KHOA_CAP = sorted(CAP_NHOM, key=len, reverse=True)   # tiền tố dài trước: '722540' thắng '7225'


def _nhom_cap(code: str) -> str | None:
    return next((k for k in _KHOA_CAP if code.startswith(k)), None)


# ---------------------------------------------------------------- đọc mô tả ECUS
_SO = r"\d+(?:[.,]\d+)?"
_NT = "|".join(sorted(list(NGUONG_HOP_KIM) + ["C", "P", "S", "N"], key=len, reverse=True))
# Thành phần phải là PHẦN TRĂM: có '%' hoặc dấu ':'/'=' — 'W2440 mm', 'T40' là kích thước, không phải nguyên tố.
_MAU_NT = re.compile(r"(?<![A-Za-z])(?P<nt>" + _NT + r")\s*(?P<dau>[:=])?\s*(?P<toi_da>max|tối đa|toi da|≤|<=|<)?\s*"
                     r"(?P<a>" + _SO + r")\s*(?P<pt>%)?\s*(?:(?:->|-|–|~|÷|đến|to)\s*(?P<b>" + _SO + r")\s*(?P<pt2>%)?)?"
                     r"(?!\s*mm)(?!\d)(?![.,]\d)", re.I)
_PHU = r"(?:dat phu|phu|ma|trang|son)"
_PHU_DINH = re.compile(r"\b(?:khong|chua)(?: duoc)? " + _PHU + r"(?:\s*(?:,|/|va|hoac)?\s*" + _PHU + r")*\b")
_MAU_KT = re.compile(r"(" + _SO + r")\s*(?:mm)?\s*[x×*]\s*(" + _SO + r")\s*(?:mm)?(?:\s*[x×*]\s*(" + _SO + r"|C)\s*(?:mm)?)?",
                     re.I)


def _kich_thuoc(t: str, khoa: str) -> float | None:
    """Kích thước mm. Độ dày: CÙNG luật pvtm_kho.doc_so_lo — '2.500' MƠ HỒ (2,5 hay 2500?) -> None (ghi mo_ho),
    dấu phẩy là thập phân ('1,250' = 1,25). Rộng/dài: '2.440' / '1,250' là ngăn nghìn — CỐ Ý khác doc_so_lo
    (ô rộng của lô gõ số thuần; còn mô tả ECUS viết '1,250' kiểu Anh, khổ 1,25 mm không có thật)."""
    if khoa == "day":
        return None if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", t) else doc_so(t)
    if re.fullmatch(r"\d{1,3}[.,]\d{3}", t):
        return float(t.replace(".", "").replace(",", ""))
    return doc_so(t)


def doc_dong_hang(mo_ta: str) -> dict[str, Any]:
    """Ô "Mô tả hàng hóa" ECUS -> thông số. Chỉ ghi cái ĐỌC ĐƯỢC; không đoán (khong_doc_duoc liệt kê phần thiếu)."""
    t = " ".join((mo_ta or "").split())
    kd = bo_dau(t)
    ra: dict[str, Any] = {"nguyen_to": {}, "mo_ho": []}
    for m in _MAU_NT.finditer(t.replace("%->", "% ->")):
        if not (m["dau"] or m["pt"] or m["pt2"] or m["toi_da"]):
            continue
        nt = next(k for k in NGUONG_HOP_KIM.keys() | {"C", "P", "S", "N"} if k.lower() == m["nt"].lower())
        a = doc_so(m["a"])
        b = doc_so(m["b"]) if m["b"] else a
        if m["toi_da"]:
            a = 0.0   # 'C max 0,25%' / 'C ≤ 0,25%': chỉ biết cận trên
        if max(a, b) < 100:
            ra["nguyen_to"].setdefault(nt, (min(a, b), max(a, b)))
    if "C" in ra["nguyen_to"]:
        ra["carbon"] = ra["nguyen_to"]["C"]
    # Nhãn rõ (dày / rộng / T / W) ưu tiên; cặp 'a x b' chỉ điền phần còn thiếu.
    for khoa, mau in (("day", r"\b(?:chieu day|do day|day|t)\s*[:=]?\s*(" + _SO + r")\s*(?:mm)?(?=\s*(?:x|×|\*|mm|,|;|$))"),
                      ("rong", r"\b(?:chieu rong|kho|rong|w)\s*[:=]?\s*(" + _SO + r")\s*(?:mm)?(?=\s*(?:x|×|\*|mm|,|;|$))")):
        if x := re.search(mau, kd):
            v = _kich_thuoc(x.group(1), khoa)
            if v is None:
                ra["mo_ho"].append(f"{khoa} '{x.group(1)}'")
            else:
                ra[khoa] = v
    m = _MAU_KT.search(re.sub(r"\b[TtWwLl](?=\d)", "", t))
    if m:
        nhom = [m.group(1), m.group(2)]
        cuon = bool(m.group(3)) and m.group(3).upper() == "C"
        if m.group(3) and not cuon:
            nhom.append(m.group(3))
        so = [_kich_thuoc(x, "day" if i == 0 and "day" not in ra else "rong") for i, x in enumerate(nhom)]
        if so[0] is None:
            ra["mo_ho"].append(f"day '{nhom[0]}'")
        if "day" in ra and ra["day"] not in so:   # 'dày 40mm' + '2.440 x 12.000' -> cặp là rộng x dài
            so = [ra["day"]] + so
        for khoa, v in zip(("day", "rong", "dai"), so):
            if v is not None and not (khoa == "day" and any(x.startswith("day") for x in ra["mo_ho"])):
                ra.setdefault(khoa, v)
        if cuon:
            ra["dang"] = "cuon"   # '3 x 1250 x C' là cách viết cuộn
    if "dang" not in ra:
        if re.search(r"\b(dang cuon|cuon|coil)\b", kd) and not re.search(r"khong (o )?dang cuon", kd):
            ra["dang"] = "cuon"
        elif re.search(r"\b(tam|plate|sheet)\b", kd):
            ra["dang"] = "tam"
    if "can nguoi" in kd or "ep nguoi" in kd:
        ra["gia_cong"] = "nguoi"
    elif "can nong" in kd:
        ra["gia_cong"] = "nong"
    con = _PHU_DINH.sub(" ", kd).replace("phu dau", " ")
    if re.search(r"\b(son|ma kem|ma nhom|ma crom|ma hop kim|ton ma|da ma|duoc ma|ma dien|trang kem|da trang|"
                 r"duoc trang|dat phu|da phu|duoc phu|phu (?:kem|son|mau|nhua|plastic))\b", con):
        ra["phu"] = True
    elif _PHU_DINH.search(kd):
        ra["phu"] = False
    if re.search(r"\b(thep gio|high[- ]speed)\b", kd):
        ra["thep_gio"] = True
    if x := re.search(r"\bTC\s*[:：]\s*([^,;]+)", t):
        ra["tieu_chuan"] = x.group(1).strip().rstrip(".")
    if x := re.search(r"M[áa]c(?: thép)?\s*[:：]\s*([^,;]+?)(?:\.\s|[,;]|\s+M[ớo]i\b|$)", t):
        ra["mac_thep"] = x.group(1).strip().rstrip(".")
    return ra


# ---------------------------------------------------------------- hợp kim
def la_hop_kim(nguyen_to: dict[str, tuple[float, float]]) -> dict[str, Any]:
    """Chú giải 1(f): ket_luan 'hop_kim' | 'khong_hop_kim' | 'chua_du' (khoảng khai vắt qua ngưỡng / không có
    thành phần). Kèm nguyên tố quyết định, ngưỡng và khoảng cách tới ngưỡng (điểm %)."""
    if not nguyen_to:
        return {"ket_luan": "chua_du", "ly_do": "Mô tả không ghi thành phần hóa học"}
    cr, c = nguyen_to.get("Cr"), nguyen_to.get("C")
    if cr and cr[0] >= NGUONG_KHONG_GI["Cr"] and (c is None or c[1] <= NGUONG_KHONG_GI["C_toi_da"]):
        return {"ket_luan": "khong_gi", "nguyen_to": "Cr", "nguong": NGUONG_KHONG_GI["Cr"], "gia_tri": cr,
                "cach": round(cr[0] - NGUONG_KHONG_GI["Cr"], 4)}
    vat = []
    for nt, (a, b) in nguyen_to.items():
        ng = NGUONG_HOP_KIM.get(nt)
        if ng is None:
            continue
        if a >= ng:
            return {"ket_luan": "hop_kim", "nguyen_to": nt, "nguong": ng, "gia_tri": (a, b), "cach": round(a - ng, 4)}
        if b >= ng:
            vat.append(nt)
    if vat:
        nt = vat[0]
        return {"ket_luan": "chua_du", "nguyen_to": nt, "nguong": NGUONG_HOP_KIM[nt], "gia_tri": nguyen_to[nt],
                "ly_do": f"Khoảng khai {TEN_NGUYEN_TO[nt]} vắt qua ngưỡng {NGUONG_HOP_KIM[nt]:g}% — Mill Test quyết định"}
    gan = min(((nt, NGUONG_HOP_KIM[nt] - b) for nt, (a, b) in nguyen_to.items() if nt in NGUONG_HOP_KIM),
              key=lambda x: x[1], default=None)
    kq = {"ket_luan": "khong_hop_kim"}
    if gan:
        kq.update(nguyen_to=gan[0], nguong=NGUONG_HOP_KIM[gan[0]], gia_tri=nguyen_to[gan[0]], cach=round(gan[1], 4))
    return kq


# ---------------------------------------------------------------- soát mã với thông số
def _la_ma_thep(code: str) -> bool:
    return code[:4] in NHOM_KHONG_HOP_KIM + NHOM_HOP_KIM + NHOM_KHONG_GI


def _loai_thep_ma(code: str) -> str:
    return "khong_gi" if code[:4] in NHOM_KHONG_GI else "hop_kim" if code[:4] in NHOM_HOP_KIM else "khong_hop_kim"


_TEN_LOAI = {"hop_kim": "thép hợp kim", "khong_hop_kim": "thép không hợp kim", "khong_gi": "thép không gỉ"}


def _khoang_day(mo_ta_ma: str) -> list[tuple[str, float]]:
    """Dải chiều dày trong mô tả mã ('Chiều dày trên 10 mm', 'từ 4,75 mm trở lên nhưng không quá 10 mm')."""
    kd = bo_dau(mo_ta_ma)
    i = max(kd.rfind("chieu day"), kd.rfind("do day"))
    if i < 0:
        return []
    doan = re.split(r" - |:", mo_ta_ma[i:])[0]
    return khoang(doan)


def soat_ma(ma: dict[str, Any], tt: dict[str, Any], hop_kim: str) -> list[dict[str, Any]]:
    """Mỗi tiêu chí máy soát được: {tieu_chi, ma_ghi, lo, dat: True|False|None}. None = thiếu dữ liệu lô."""
    code, mo = ma["code"], ma["desc_vn"]
    kd = bo_dau(mo)
    ra: list[dict[str, Any]] = []
    if _la_ma_thep(code):
        loai = _loai_thep_ma(code)
        dat = None if hop_kim == "chua_du" else hop_kim == loai
        ra.append({"tieu_chi": "Hợp kim (Chú giải 1(e), 1(f) Chương 72)", "ma_ghi": _TEN_LOAI[loai],
                   "lo": _TEN_LOAI.get(hop_kim, "chưa đủ dữ liệu"), "dat": dat})
    for mau, ten, tren in (("tu 600 ?mm tro len", "Chiều rộng", True), ("duoi 600 ?mm", "Chiều rộng", False)):
        if re.search(mau, kd):
            r = tt.get("rong")
            ra.append({"tieu_chi": ten, "ma_ghi": "từ 600 mm trở lên" if tren else "dưới 600 mm",
                       "lo": None if r is None else f"{_vn(r)} mm", "dat": None if r is None else (r >= 600) == tren})
            break
    for mau, cuon in (("khong o dang cuon", False), ("o dang cuon", True), ("dang cuon", True)):
        if mau in kd:
            d = tt.get("dang")
            ra.append({"tieu_chi": "Dạng", "ma_ghi": "dạng cuộn" if cuon else "không ở dạng cuộn",
                       "lo": {"cuon": "cuộn", "tam": "tấm"}.get(d), "dat": None if d is None else (d == "cuon") == cuon})
            break
    dk = _khoang_day(mo)
    if dk:
        d = tt.get("day")
        ra.append({"tieu_chi": "Độ dày", "ma_ghi": re.split(r" - |:", mo[max(kd.rfind("chieu day"), kd.rfind("do day")):])[0].strip(),
                   "lo": None if d is None else f"{_vn(d)} mm", "dat": None if d is None else all(_dat(d, x) for x in dk)})
    if "thep gio" in kd:
        ra.append({"tieu_chi": "Thép gió", "ma_ghi": "thép gió",
                   "lo": "thép gió" if tt.get("thep_gio") else "không ghi thép gió", "dat": bool(tt.get("thep_gio"))})
    if "chua dat phu" in kd or "chua duoc dat phu" in kd or "da dat phu" in kd or "duoc son" in kd:
        da = not ("chua dat phu" in kd or "chua duoc dat phu" in kd)
        p = tt.get("phu")
        ra.append({"tieu_chi": "Phủ, mạ, tráng, sơn", "ma_ghi": "đã phủ/mạ/tráng/sơn" if da else "chưa phủ/mạ/tráng",
                   "lo": None if p is None else ("đã phủ" if p else "chưa phủ"), "dat": None if p is None else p == da})
    for mau, ten in (("can nguoi", "cán nguội"), ("can nong", "cán nóng")):
        if mau in kd:
            g = tt.get("gia_cong")
            ra.append({"tieu_chi": "Gia công", "ma_ghi": ten,
                       "lo": {"nong": "cán nóng", "nguoi": "cán nguội"}.get(g), "dat": None if g is None else ten.endswith(
                           "nóng" if g == "nong" else "nguội")})
            break
    return ra


def ket_luan_ma(tieu_chi: list[dict[str, Any]]) -> str:
    """'dung' | 'xem_lai' | 'chua_du' — 'dung' chỉ khi MỌI tiêu chí máy soát được đều đạt."""
    if any(x["dat"] is False for x in tieu_chi):
        return "xem_lai"
    if any(x["dat"] is None for x in tieu_chi) or not tieu_chi:
        return "chua_du"
    return "dung"


# ---------------------------------------------------------------- mã nghi ngờ
def cap_nghi_ngo(code: str, tt: dict[str, Any], hop_kim: str, tra_ma: Callable[[str], dict | None],
                 ma_con: Callable[[str], list[str]]) -> list[dict[str, Any]]:
    """Mã đối ứng hợp kim <-> không hợp kim cùng quy cách. Mỗi mã đều có thật (tra_ma); không khớp mã 8 số
    nào thì trả mã 6 số kèm 'can_xac_dinh' — KHÔNG ghép đuôi."""
    nhom = _nhom_cap(code)
    if not nhom:
        return []
    doi = "khong_hop_kim" if code[:4] in NHOM_HOP_KIM else "hop_kim"   # NHOM_KHONG_GI không có trong CAP_NHOM
    ra = []
    for tien_to in CAP_NHOM[nhom]:
        for c in ma_con(tien_to):
            m = tra_ma(c)
            if not m:
                continue
            tc = [x for x in soat_ma(m, tt, doi) if not x["tieu_chi"].startswith("Hợp kim")]
            if all(x["dat"] is not False for x in tc):
                ra.append({**m, "_khop": sum(x["dat"] is True for x in tc)})
    if ra:   # mã 'Loại khác' / 'có hình dập nổi' khớp ít tiêu chí hơn mã đúng quy cách -> bỏ
        cao = max(x["_khop"] for x in ra)
        ra = [{k: v for k, v in x.items() if k != "_khop"} for x in ra if x["_khop"] == cao]
        for x in ra:
            x["can_xac_dinh"] = len(ra) > 1
    if not ra:
        for tien_to in CAP_NHOM[nhom]:
            if (m := tra_ma(tien_to[:6])) or ma_con(tien_to[:6]):
                ra.append({**(m or {"code": tien_to[:6], "desc_vn": "", "mfn": "", "fta": {}}), "can_xac_dinh": True})
    return ra


# ---------------------------------------------------------------- phiếu
def _ma_cham(code: str) -> str:
    """'72254090' -> '7225.40.90' (cùng cách viết tra_cuu.dinh_dang_ma; tệp luật thuần không nhập tra_cuu)."""
    return f"{code[:4]}.{code[4:6]}.{code[6:]}" if len(code) == 8 else code


def _cap(m: dict[str, Any]) -> list[str]:
    """Các cấp mô tả của mã. Nơi gọi đưa sẵn `cap` (ILMS: tra_cuu.cap_cua — đọc cột cap_mo_ta); không có thì tách
    đúng luật tra_cuu.tach_cap (bản dự phòng cho skill đọc hs_tree.json): chỉ cắt ở " - " ĐỨNG TRƯỚC một gạch nữa,
    nên "kẽm - nhôm - magiê" không bị xé. Đổi luật cắt ở tra_cuu thì đổi cả đây (test_cap_khop_tra_cuu canh)."""
    if m.get("cap"):
        return list(m["cap"])
    cap = [re.sub(r"^[-\s]*", "", p).rstrip(" :") for p in re.split(r" - (?=-)", m.get("desc_vn") or "")]
    return [c for c in cap if c]


def _vn(x: float) -> str:
    """0.3 -> '0,3'; 2300 -> '2.300' (ngăn nghìn) — mọi số in trên phiếu đi qua đây."""
    if float(x).is_integer() and abs(x) >= 1000:
        return f"{int(x):,}".replace(",", ".")
    return f"{x:g}".replace(".", ",")


def _pt(v: Any) -> str:
    if v in (None, ""):
        return "—"
    try:
        return _vn(float(v)) + "%"
    except ValueError:
        return str(v)


def _thue(m: dict[str, Any], nuoc: str | None) -> str:
    fta = m.get("fta") or {}
    s = f"MFN {_pt(m.get('mfn'))}"
    for hd in FTA_THEO_NUOC.get(nuoc or "", ()):
        if fta.get(hd) not in (None, ""):
            s += f" · {hd.upper()} {_pt(fta[hd])}"
    return s


def _so_hay_none(v: Any) -> float | None:
    """Ô thuế suất Biểu thuế / người khai: '0', '5%', '7,5' -> số; '*', 'KCT', '0 (-MY, TH)' (ô FTA có ghi chú
    loại trừ — người khai tự đối chiếu C/O) -> chỉ lấy khi đứng đầu là số; còn lại None."""
    m = re.match(r"\s*(\d+(?:[.,]\d+)?)\s*%?", str(v or ""))
    return doc_so(m.group(1)) if m else None


def _ket_cbpg(kq: dict[str, Any] | None) -> tuple[str, str, str]:
    """(giá trị ô, dòng chi tiết, mức màu) từ kết quả tinh_cho_lo."""
    if not kq or not kq.get("vu_viec"):
        return "KHÔNG ÁP", "mã không thuộc vụ nào đang áp", "tot"
    ds = kq["vu_viec"]
    ap = [v for v in ds if v["ket_luan"] == "ap"]
    if ap:
        if any(v["muc_thue"] is None for v in ap):   # kho chưa nhập mức: KHÔNG in 0% như số thật
            return "BỊ ÁP", "chưa có mức trong kho — tra QĐ gốc · " + ", ".join(v["ma_vu_viec"] for v in ap), "xau"
        cao = max(v["muc_thue"] for v in ap)
        return f"BỊ ÁP {_pt(cao)}", ", ".join(v["ma_vu_viec"] for v in ap), "xau"
    if any(v["ket_luan"] == "chua_du" for v in ds):
        return "CHƯA ĐỦ", "thiếu " + ", ".join(sorted({t for v in ds for t in v.get("thieu", [])})), "canh"
    ngoai = [v for v in ds if v["ket_luan"] == "khong_thuoc_pham_vi"]
    return "KHÔNG ÁP", (f"ngoài phạm vi {len(ngoai)} vụ" if ngoai else "không thuộc diện áp"), "tot"


def _buoc_pham_vi(kq: dict[str, Any] | None):
    """(vụ, bước, pham_vi) cho mọi bước "Phạm vi" của kết quả tinh_cho_lo — dữ liệu có cấu trúc của pvtm."""
    for v in (kq or {}).get("vu_viec", []):
        for b in v["cac_buoc"]:
            if b.get("pham_vi"):
                yield v, b, b["pham_vi"]


def _lo_chu(p: dict[str, Any]) -> str:
    if p["khoa"] == "dang":
        return NHAN_DANG.get(p["lo"], str(p["lo"]))
    return f"{_vn(p['lo'])} {DON_VI.get(p['khoa'], '')}".strip()


def _bang_pvtm(kq: dict[str, Any] | None) -> list[dict[str, Any]]:
    tieu_chi: dict[str, list[dict[str, Any]]] = {}
    for v, b, p in _buoc_pham_vi(kq):
        tieu_chi.setdefault(v["ma_vu_viec"], []).append(
            {"ten": NHAN_KHOA[p["khoa"]], "qd": p["goc"].split(": ", 1)[-1], "lo": _lo_chu(p), "dat": b["dat"]})
    return [{"vu": v["ma_vu_viec"], "so_hieu": v.get("so_hieu", ""), "tieu_chi": tieu_chi.get(v["ma_vu_viec"], []),
             "ket_luan": {"khong_thuoc_pham_vi": "Ngoài phạm vi",
                          "ap": f"Bị áp {_pt(v['muc_thue'])}" if v["muc_thue"] is not None else "Bị áp — chưa có mức",
                          "khong_ap": "Không áp", "chua_du": "Chưa đủ dữ liệu"}[v["ket_luan"]],
             "muc": {"ap": "xau", "chua_du": "canh"}.get(v["ket_luan"], "tot")}
            for v in (kq or {}).get("vu_viec", [])]


def _khoang_dong(dk: list[tuple[str, float]]) -> tuple[float, float]:
    lo, hi = 0.0, float("inf")
    for op, x in dk:
        if op in (">", ">="):
            lo = max(lo, x)
        else:
            hi = min(hi, x)
    return lo, hi


def _nguong_thoat(khoang_vu: list[tuple[float, float]], lo_khai: float | None = None) -> str:
    """Hợp các khoảng phạm vi của mọi vụ -> 'trên X' / 'dưới Y' / 'ngoài X–Y'. Biết giá trị lô thì nói
    theo PHÍA của lô (lô 40 mm, khoảng 1,2–25,4 -> 'trên 25,4'), đúng điều kiện cần đo để giữ kết luận."""
    ds = sorted(khoang_vu)
    hop = [list(ds[0])]
    for lo, hi in ds[1:]:
        if lo <= hop[-1][1] + 1e-9:
            hop[-1][1] = max(hop[-1][1], hi)
        else:
            hop.append([lo, hi])
    if lo_khai is not None:
        tren = [hi for lo, hi in hop if hi < lo_khai]
        duoi = [lo for lo, hi in hop if lo > lo_khai]
        if tren and not duoi:
            return f"trên {_vn(max(tren))}"
        if duoi and not tren:
            return f"dưới {_vn(min(duoi))}"
    cau = []
    for lo, hi in hop:
        if lo <= 0:
            cau.append(f"trên {_vn(hi)}")
        elif hi == float("inf"):
            cau.append(f"dưới {_vn(lo)}")
        else:
            cau.append(f"ngoài {_vn(lo)}–{_vn(hi)}")
    return " và ".join(cau)


def _tan_mat(tt: dict[str, Any], hk: dict[str, Any], kq: dict[str, Any] | None, code: str) -> list[dict[str, str]]:
    """Việc kiểm hóa phải xem tận mắt — mỗi việc gắn với NGƯỠNG làm đổi kết luận.
    Tiêu chí quy cách: gộp khoảng (pham_vi.dk của pvtm) của MỌI vụ cùng mã -> ngưỡng để lô nằm ngoài tất cả."""
    gom: dict[str, dict[str, Any]] = {}
    tay: list[dict[str, str]] = []
    for _v, b, p in _buoc_pham_vi(kq):
        if b["dat"] is not False:
            continue
        if p.get("dk"):
            g = gom.setdefault(p["khoa"], {"khoang": [], "lo": p["lo"]})
            g["khoang"].append(_khoang_dong(p["dk"]))
        else:   # dạng hàng / quy cách chữ: không có ngưỡng số -> đối chiếu tay, không lặng lẽ mất dòng
            viec = {"viec": f"Đối chiếu tay {NHAN_KHOA[p['khoa']].lower()}: QĐ ghi “{p['goc'].split(': ', 1)[-1]}”",
                    "khai": _lo_chu(p)}
            if viec not in tay:
                tay.append(viec)
    ra = [{"viec": f"Đo {NHAN_KHOA[k].lower()}: phải {_nguong_thoat(g['khoang'], g['lo'])} {DON_VI.get(k, '')} "
                   "thì nằm ngoài phạm vi chống bán phá giá", "khai": _lo_chu({"khoa": k, "lo": g["lo"]})}
          for k, g in gom.items()] + tay
    if hk.get("nguyen_to"):
        nt = hk["nguyen_to"]
        a, b = hk["gia_tri"]
        tren = hk["ket_luan"] in ("hop_kim", "khong_gi")
        ra.append({"viec": f"Mill Test ghi {TEN_NGUYEN_TO[nt]} {'≥' if tren else '<'} {_vn(hk['nguong'])}%: căn cứ xếp "
                           f"{_TEN_LOAI.get(hk['ket_luan'], 'thép')}",
                   "khai": f"{_vn(a)}–{_vn(b)}%" if a != b else f"{_vn(a)}%"})
    if tt.get("dang"):
        ra.append({"viec": f"Hàng dạng {'tấm, không cuộn' if tt['dang'] == 'tam' else 'cuộn'}"
                           + ("" if tt.get("phu") else "; bề mặt không sơn, mạ, tráng"),
                   "khai": code[:4] + "." + code[4:6]})
    return ra


# Ô nhập riêng ghi đè giá trị đọc từ mô tả — mỗi ô một bộ chuyển (dạng: pvtm.chuan_dang, 'tấm' -> 'tam').
_GHI_DE: dict[str, Callable[[Any], Any]] = {
    "day": float, "rong": float, "mac_thep": str, "tieu_chuan": str,
    "dang": lambda v: chuan_dang(str(v)), "carbon": lambda v: (doc_so(str(v)),) * 2,
}


def thong_so(dau_vao: dict[str, Any]) -> dict[str, Any]:
    """Thông số lô = đọc từ mô tả, rồi ô người dùng nhập riêng (day/rong/carbon/dang/mac_thep/tieu_chuan) ghi đè."""
    tt = doc_dong_hang(dau_vao.get("mo_ta", ""))
    for k, doi in _GHI_DE.items():
        if dau_vao.get(k) not in (None, ""):
            tt[k] = doi(dau_vao[k])
    tt["khong_doc_duoc"] = [k for k in ("day", "rong", "dang", "carbon") if k not in tt]
    return tt


def lo_pvtm(tt: dict[str, Any], dau_vao: dict[str, Any]) -> dict[str, Any]:
    """Thông số đưa vào tinh_cho_lo (carbon khai là khoảng -> lấy đầu CAO, phía bất lợi khi soát ngưỡng '≤')."""
    c = tt.get("carbon")
    return {"nuoc_co": dau_vao.get("nuoc") or None, "nha_sx": dau_vao.get("nsx") or None,
            "nha_xk": dau_vao.get("nxk") or None, "mac_thep": tt.get("mac_thep"), "tieu_chuan": tt.get("tieu_chuan"),
            "day": tt.get("day"), "rong": tt.get("rong"), "carbon": c[1] if c else None, "dang": tt.get("dang")}


def tien_to_can_doc(code: str) -> list[str]:
    """Tiền tố mã nơi gọi phải nạp sẵn cho tra_ma / ma_con: chính mã + các nhóm đối ứng (và mã 6 số của chúng)."""
    nhom = _nhom_cap(code)
    return [code] + (list(CAP_NHOM[nhom]) if nhom else [])


def nghi_ngo(code: str, tt: dict[str, Any], tra_ma: Callable[[str], dict | None],
             ma_con: Callable[[str], list[str]]) -> list[dict[str, Any]]:
    """Mã nghi ngờ của dòng hàng (nơi gọi tính PVTM cho từng mã rồi đưa NGUYÊN danh sách vào lap_phieu)."""
    if not _la_ma_thep(code):
        return []
    return cap_nghi_ngo(code, tt, la_hop_kim(tt["nguyen_to"])["ket_luan"], tra_ma, ma_con)


def ma_nghi_ngo(code: str, tt: dict[str, Any], tra_ma: Callable[[str], dict | None],
                ma_con: Callable[[str], list[str]]) -> list[str]:
    return [m["code"] for m in nghi_ngo(code, tt, tra_ma, ma_con)]


def lap_phieu(dau_vao: dict[str, Any], tra_ma: Callable[[str], dict | None], ma_con: Callable[[str], list[str]],
              pvtm_ma: dict[str, Any] | None, pvtm_nghi_ngo: dict[str, dict[str, Any]] | None = None,
              tt: dict[str, Any] | None = None, ds_nghi_ngo: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """dau_vao: {ma, mo_ta, nuoc?, thue_suat?, tk?, dong?, luong?, nsx?, nxk?, + ghi đè day/rong/carbon/dang/mac_thep/
    tieu_chuan}. pvtm_ma: tinh_cho_lo của chính mã khai; pvtm_nghi_ngo: {mã nghi ngờ: tinh_cho_lo} (nơi gọi tính trước).
    tt / ds_nghi_ngo: nơi gọi đã tính (thong_so / nghi_ngo) thì đưa vào, khỏi đọc mô tả và soát mã đối ứng lần hai."""
    code = re.sub(r"\D", "", dau_vao.get("ma") or "")
    ma = tra_ma(code)
    if not ma:
        raise ValueError(f"Không có mã {code} trong Biểu thuế")
    tt = tt if tt is not None else thong_so(dau_vao)
    hk = la_hop_kim(tt["nguyen_to"]) if _la_ma_thep(code) else {"ket_luan": "khong_ap_dung"}
    tieu_chi = soat_ma(ma, tt, hk["ket_luan"])
    kl = ket_luan_ma(tieu_chi)
    try:
        nuoc = chuan_nuoc(dau_vao.get("nuoc"))   # 'Trung Quốc' -> 'CN' — cùng luật với phần CBPG
    except ValueError:
        nuoc = None
    can_lam_ro = [f"{x['tieu_chi']}: mã ghi {x['ma_ghi']}, lô {x['lo']}" for x in tieu_chi if x["dat"] is False]
    can_lam_ro += [f"Không đọc được {k} từ mô tả" for k in tt["khong_doc_duoc"] if _la_ma_thep(code)]
    can_lam_ro += [f"Số mơ hồ, nhập lại bằng ô riêng: {x}" for x in tt.get("mo_ho", [])]
    if hk.get("ket_luan") == "chua_du" and hk.get("ly_do"):
        can_lam_ro.append(hk["ly_do"])
    ts = dau_vao.get("thue_suat")
    thue_khop = None
    if ts not in (None, ""):
        khai = _so_hay_none(ts)
        muc_ap = [x for x in [_so_hay_none(ma.get("mfn"))] + [_so_hay_none((ma.get("fta") or {}).get(hd))
                                                               for hd in FTA_THEO_NUOC.get(nuoc or "", ())] if x is not None]
        if khai is None:
            can_lam_ro.append(f"Không đọc được thuế suất khai '{ts}'")
        elif not muc_ap:
            can_lam_ro.append("Biểu thuế không ghi MFN/FTA dạng số để so thuế suất khai")
        else:
            thue_khop = any(abs(khai - x) < 1e-9 for x in muc_ap)
            if not thue_khop and nuoc and nuoc not in FTA_THEO_NUOC:
                thue_khop = None   # chưa có bảng FTA cho nước này: không kết luận lệch, để người đối chiếu C/O
                can_lam_ro.append(f"Thuế suất khai {_vn(khai)}% khác MFN; chưa có bảng FTA cho nước {nuoc} — đối chiếu C/O")
            elif not thue_khop:
                can_lam_ro.append(f"Thuế suất khai {_vn(khai)}% khác MFN/FTA của mã")
    cb_gt, cb_ct, cb_muc = _ket_cbpg(pvtm_ma)
    if any(v["ket_luan"] == "ap" and v.get("thieu") for v in (pvtm_ma or {}).get("vu_viec", [])):
        can_lam_ro.append("Kết luận CBPG đang giả định lô nằm trong phạm vi (thiếu quy cách)")
    for v in (pvtm_ma or {}).get("vu_viec", []):
        if v["ket_luan"] == "ap" and v["muc_thue"] is None:
            can_lam_ro.append(f"Vụ {v['ma_vu_viec']}: kho chưa có mức thuế — tra bảng mức thuế trong QĐ gốc")
    dong_nghi = []
    if _la_ma_thep(code):
        dong_nghi.append({"code": code, "mo_ta": ma["desc_vn"], "cap": _cap(ma)[-2:], "dang_khai": True,
                         "khi": _khi(hk, code), "thue": _thue(ma, nuoc), "cbpg": _ket_cbpg(pvtm_ma)})
        for m in (ds_nghi_ngo if ds_nghi_ngo is not None else cap_nghi_ngo(code, tt, hk["ket_luan"], tra_ma, ma_con)):
            dong_nghi.append({"code": m["code"], "mo_ta": m["desc_vn"], "cap": _cap(m)[-2:], "dang_khai": False,
                             "can_xac_dinh": m["can_xac_dinh"],
                             "khi": _khi(hk, m["code"]), "thue": _thue(m, nuoc),
                             "cbpg": _ket_cbpg((pvtm_nghi_ngo or {}).get(m["code"]))})
    ly_do_nghi_ngo = ("" if len(dong_nghi) > 1 else "ngoai_chuong_72" if not _la_ma_thep(code)
                      else "khong_gi" if code[:4] in NHOM_KHONG_GI else "khong_co_cap")
    ghi = ""
    if hk.get("nguyen_to") and hk["ket_luan"] in ("hop_kim", "khong_hop_kim"):
        nt, ng = hk["nguyen_to"], hk["nguong"]
        a, b = hk["gia_tri"]
        tren = hk["ket_luan"] == "hop_kim"
        ghi = (f"{TEN_NGUYEN_TO[nt]} khai {_vn(a)}–{_vn(b)}%, {'cao hơn' if tren else 'thấp hơn'} ngưỡng {_vn(ng)}% là "
               f"{_vn(abs(hk['cach']))} điểm %. Mill Test là chứng từ quyết định.")
    return {
        "dau": {"ten": _ten_rut_gon(dau_vao.get("mo_ta", "")), "tk": dau_vao.get("tk"), "dong": dau_vao.get("dong"),
                "nuoc": nuoc, "luong": dau_vao.get("luong"), "ma": code},
        "o": [
            {"khoa": "ma_hs", "nhan": "Mã HS", "gt": {"dung": "ĐÚNG", "xem_lai": "CẦN XEM LẠI", "chua_du": "CHƯA ĐỦ"}[kl],
             "ct": f"{_ma_cham(code)} · theo tiêu chí máy soát được",
             "muc": {"dung": "tot", "xem_lai": "xau", "chua_du": "canh"}[kl]},
            {"khoa": "thue", "nhan": "Thuế NK", "gt": _pt(ma.get("mfn")),
             "ct": _thue(ma, nuoc) + ({True: " · khớp TK", False: " · LỆCH TK", None: ""}[thue_khop]),
             "muc": "xau" if thue_khop is False else "tot"},
            {"khoa": "cbpg", "nhan": "CBPG / PVTM", "gt": cb_gt, "ct": cb_ct, "muc": cb_muc},
            {"khoa": "lam_ro", "nhan": "Cần làm rõ", "gt": str(len(can_lam_ro)),
             "ct": can_lam_ro[0] if can_lam_ro else "không có", "muc": "canh" if can_lam_ro else "tot"},
        ],
        "can_lam_ro": can_lam_ro,
        "thong_so": tt, "hop_kim": hk, "tieu_chi_ma": tieu_chi,
        "tan_mat": _tan_mat(tt, hk, pvtm_ma, code),
        "lap_luan": _lap_luan(code, ma, hk, tt),
        "nghi_ngo": dong_nghi, "ghi_nghi_ngo": ghi, "ly_do_nghi_ngo": ly_do_nghi_ngo,
        "pvtm": _bang_pvtm(pvtm_ma),
    }


def _khi(hk: dict[str, Any], code: str) -> str:
    """Điều kiện để hàng rơi vào mã này (theo nhóm hợp kim / không hợp kim / không gỉ)."""
    if code[:4] in NHOM_KHONG_GI:
        return "Crôm ≥ 10,5% và carbon ≤ 1,2% (Chú giải 1(e) Chương 72)"
    nt = hk.get("nguyen_to") if hk.get("nguyen_to") in NGUONG_HOP_KIM else "Cr"
    ng = NGUONG_HOP_KIM.get(nt, 0.3)
    if code[:4] in NHOM_HOP_KIM:
        return f"{TEN_NGUYEN_TO[nt]} ≥ {_vn(ng)}% (hoặc một nguyên tố khác đạt ngưỡng Chú giải 1(f))"
    return f"{TEN_NGUYEN_TO[nt]} < {_vn(ng)}% và không nguyên tố nào đạt ngưỡng Chú giải 1(f)"


def _lap_luan(code: str, ma: dict[str, Any], hk: dict[str, Any], tt: dict[str, Any]) -> list[str]:
    ra = []
    if hk.get("ket_luan") == "khong_gi":
        a, b = hk["gia_tri"]
        ra.append(f"Crôm {_vn(a)}–{_vn(b)}% ≥ 10,5% → thép không gỉ (Chú giải 1(e) Chương 72) → nhóm 72.18–72.23")
    elif hk.get("ket_luan") in ("hop_kim", "khong_hop_kim") and hk.get("nguyen_to"):
        a, b = hk["gia_tri"]
        if hk["ket_luan"] == "hop_kim":
            ra.append(f"{TEN_NGUYEN_TO[hk['nguyen_to']]} {_vn(a)}–{_vn(b)}% ≥ {_vn(hk['nguong'])}% → thép hợp kim "
                      "(Chú giải 1(f) Chương 72) → không thuộc nhóm thép không hợp kim")
        else:
            ra.append("Không nguyên tố nào đạt ngưỡng Chú giải 1(f) Chương 72 → thép không hợp kim")
    if tt.get("rong") is not None:
        ra.append(f"Rộng {_vn(tt['rong'])} mm {'≥' if tt['rong'] >= 600 else '<'} 600 mm → nhóm {code[:2]}.{code[2:4]}")
    cap = _cap(ma)
    if len(cap) > 1:
        ra.append(f"{cap[-2]} → {_ma_cham(code)[:7]}; {cap[-1]} → .{code[6:]}")
    return ra


def _ten_rut_gon(mo_ta: str) -> str:
    t = " ".join((mo_ta or "").split())
    return re.split(r",\s*(?:chứa|chua|KT|TC|Mác|Mac)\b", t)[0][:120]
