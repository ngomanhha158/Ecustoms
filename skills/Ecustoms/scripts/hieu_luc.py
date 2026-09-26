#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dò quan hệ hiệu lực giữa các văn bản trong kho `references/`.

Đọc toàn văn từng văn bản, tìm câu có động từ hiệu lực ("thay thế", "bãi bỏ",
"hết hiệu lực", "sửa đổi, bổ sung") đứng TRƯỚC một số hiệu văn bản khác trong
cùng câu. Kết quả là GỢI Ý tự động: chỉ biết những gì kho trên máy có, nên
"không thấy văn bản sửa đổi" KHÔNG có nghĩa là văn bản còn hiệu lực.

Không lưu chỉ mục ra đĩa: kho vài chục văn bản, dò lại mỗi lần để không bao
giờ lệch với tệp vừa `dongbo`.
"""
import re
import unicodedata

# Số hiệu: 06/2026/TT-BTC, 3765/QĐ-BCT, 90/2025/QH15, 1624/QĐ-BCT ...
SO_HIEU = re.compile(r"\b\d{1,5}/(?:\d{4}/)?[A-ZĐ][A-ZĐ0-9]*(?:-[A-ZĐ0-9]+)*")

# Thứ tự = mức nặng: gặp nhiều động từ trong một câu thì lấy loại nặng nhất.
DONG_TU = (
    ("bai_bo", re.compile(r"bãi bỏ|hết hiệu lực|chấm dứt hiệu lực|hủy bỏ", re.I)),
    ("thay_the", re.compile(r"thay thế", re.I)),
    ("sua_doi", re.compile(r"sửa đổi|bổ sung|đính chính", re.I)),
)
MOT_PHAN = re.compile(r"một phần|một số|cụm từ|(?<![a-zà-ỹ])(?:điều|khoản|điểm|phụ lục|mẫu|biểu mẫu)\s", re.I)
MUC_LIET_KE = re.compile(r"\s*(?:[a-zđ]\)|-|\+)\s")
NHAN = {"bai_bo": "bãi bỏ / làm hết hiệu lực", "thay_the": "thay thế", "sua_doi": "sửa đổi, bổ sung"}

# "… được sửa đổi, bổ sung bởi Luật số 90/2025/QH15" nói về văn bản KHÁC, không phải văn bản đang đọc.
_BOI = re.compile(r"(?:bởi|tại)\s+(?:[^\s]+\s+){0,4}số\s*$|(?:bởi|tại)\s+(?:[^\s]+\s+){0,3}$", re.I)
NGAY_HL = re.compile(
    # "… NÀY có hiệu lực": chỉ câu nói về CHÍNH văn bản. Không có "này" thì dễ vớ ngày
    # hiệu lực của văn bản khác được kể lại (Thông báo rà soát: "QĐ 1624 có hiệu lực kể từ…").
    r"này\s+(?:có hiệu lực|hiệu lực thi hành)[^.;]{0,40}?(?:kể\s+)?từ ngày\s+"
    r"(\d{1,2})\s*(?:tháng\s*|/)\s*(\d{1,2})\s*(?:năm\s*|/)\s*(\d{4})", re.I)


def chuan(so_hieu):
    """Khóa so sánh số hiệu: bỏ dấu, viết hoa, bỏ khoảng trắng (Đ -> D)."""
    s = so_hieu.replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", "", s).upper()


def trung_so(a, b):
    """'3765/QĐ-BCT' khớp '3765/2023/QĐ-BCT' — QĐ Bộ thường không ghi năm trong số hiệu."""
    a, b = chuan(a), chuan(b)
    if a == b:
        return True
    co_nam = re.compile(r"/\d{4}/")
    if bool(co_nam.search(a)) == bool(co_nam.search(b)):
        return False          # cùng ghi năm mà khác nhau: 26/2023/NĐ-CP ≠ 26/2026/NĐ-CP
    return co_nam.sub("/", a) == co_nam.sub("/", b)


def bac(so_hieu):
    """Thứ bậc hiệu lực pháp lý (số nhỏ = cao hơn) theo ký hiệu; 9 = không xác định."""
    k = chuan(so_hieu)
    for rx, b in ((r"/QH\d*$|-QH\d*$", 1), (r"UBTVQH", 2), (r"-CP$", 3), (r"QD-TTG$", 4),
                  (r"/TT-|/TTLT-", 5), (r"/QD-", 6)):
        if re.search(rx, k):
            return b
    return 9 if re.search(r"/[A-Z]+-[A-Z]+$", k) and "QD" not in k and "TT" not in k else 7


def co_the_tac_dong(nguon, dich):
    """Văn bản cấp dưới không sửa đổi/bãi bỏ được văn bản cấp trên; công văn (bậc 9) không tác động văn bản nào."""
    bn, bd = bac(nguon), bac(dich)
    return bn != 9 and bn <= bd


def _cau(noi_dung):
    phang = re.sub(r"[ \t]*\n[ \t]*", " ", noi_dung)
    phang = re.sub(r"[|]", " ", phang)
    return re.split(r"(?<=[.;:])\s+(?=[-–A-ZĐ0-9\"“(]|[a-zđ]\)\s)", re.sub(r"\s{2,}", " ", phang))


def ngay_hieu_luc(noi_dung):
    """Ngày có hiệu lực ghi rõ trong văn bản (yyyy-mm-dd), '' nếu văn bản ghi kiểu 'sau 15 ngày…'."""
    m = NGAY_HL.search(re.sub(r"\s+", " ", noi_dung))
    if not m:
        return ""
    d, t, n = m.groups()
    return f"{n}-{int(t):02d}-{int(d):02d}"


def quan_he(so_hieu_minh, noi_dung):
    """[(loai, so_hieu_dich, trich_doan)] văn bản này tác động lên văn bản khác."""
    ra, da_co = [], set()
    dan = None   # động từ của câu dẫn "…bãi bỏ các văn bản sau:" — mục "a) …" bên dưới kế thừa
    for cau in _cau(noi_dung):
        if cau.lstrip().lower().startswith(("căn cứ", "theo đề nghị", "xét đề nghị")):
            dan = None
            continue
        loai = next((k for k, rx in DONG_TU if rx.search(cau)), None)
        la_muc = MUC_LIET_KE.match(cau) is not None
        if not loai:
            if not (dan and la_muc):
                dan = None
                continue
            loai, vt, ke_thua = dan, 0, True
        else:
            ke_thua = False
            vt = min(rx.search(cau).start() for _k, rx in DONG_TU if rx.search(cau))
            if cau.rstrip().endswith(":") and not la_muc:
                dan = loai
        # Số hiệu văn bản KHÁC đứng trước động từ -> động từ là của văn bản ấy
        # ("QĐ số 2959/QĐ-BCT về việc sửa đổi QĐ 1624" kể lại trong văn bản thứ ba).
        if any(not trung_so(m.group(0), so_hieu_minh) for m in SO_HIEU.finditer(cau, 0, vt)):
            continue
        if loai != "sua_doi" and MOT_PHAN.search(cau[vt:vt + 60]):
            loai = "sua_doi"   # "bãi bỏ Điều 3…", "thay thế cụm từ…" chỉ là sửa một phần
        # số hiệu phải ở sát động từ; mục kế thừa chỉ lấy số hiệu ĐẦU (các số sau chỉ được nhắc tới)
        for m in list(SO_HIEU.finditer(cau, vt, vt + 150))[:1 if ke_thua else None]:
            dich = m.group(0)
            if trung_so(dich, so_hieu_minh) or not co_the_tac_dong(so_hieu_minh, dich) or _BOI.search(cau[max(0, m.start() - 40):m.start()]):
                continue
            khoa = (loai, chuan(dich))
            # số hiệu bị ngắt dòng ("13/2015/TT-B TC") -> bản cụt trùng với bản đủ đã gặp
            if any(l == loai and (d.startswith(khoa[1]) or khoa[1].startswith(d)) for l, d in da_co):
                continue
            da_co.add(khoa)
            dau = max(0, m.start() - 160)
            ra.append((loai, dich, ("…" if dau else "") + cau[dau:m.end() + 60].strip() + "…"))
    return ra


def lap_chi_muc(van_ban):
    """van_ban: [{so_hieu, ngay, co_quan, tieu_de, rel, noi_dung}] -> gắn 'tac_dong', 'bi_tac_dong', 'ngay_hl'."""
    for v in van_ban:
        v["tac_dong"] = quan_he(v["so_hieu"], v["noi_dung"]) if v["so_hieu"] else []
        v["bi_tac_dong"] = []
        v["ngay_hl"] = ngay_hieu_luc(v["noi_dung"])
    for nguon in van_ban:
        for loai, dich, trich in nguon["tac_dong"]:
            for v in van_ban:
                if v is not nguon and v["so_hieu"] and trung_so(v["so_hieu"], dich):
                    v["bi_tac_dong"].append((loai, nguon, trich))
    return van_ban


def tinh_trang(v):
    """Nhãn ngắn cho kết quả `refs`: '' nếu kho không có văn bản nào tác động lên v."""
    loai = {l for l, _n, _t in v.get("bi_tac_dong", [])}
    for k in ("bai_bo", "thay_the", "sua_doi"):
        if k in loai:
            nguon = [n["so_hieu"] for l, n, _t in v["bi_tac_dong"] if l == k]
            return f"⚠ Có văn bản {NHAN[k]}: {', '.join(dict.fromkeys(nguon))}"
    return ""
