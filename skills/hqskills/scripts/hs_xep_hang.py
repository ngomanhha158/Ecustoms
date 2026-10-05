# BẢN CHÉP TỰ ĐỘNG từ ILMSv2 backend/app/services/hs_xep_hang.py @ ilmsV2@8a90654.
# Đừng sửa tay — sửa ở ILMS rồi chạy scripts/chep_xep_hang_ilms.py.
"""Xếp hạng mã HS theo tên hàng — hàm thuần, không DB (phase144, 04-10-2026).

Vì sao: ts_rank của Postgres chỉ đếm từ trúng; "máy tính xách tay" bị kéo về 8471.49
("Máy tính cá nhân TRỪ máy tính loại xách tay"), "thép hợp kim" về 72.13 ("thép KHÔNG hợp
kim"), từ phổ biến ("máy", "loại", "tự động") át từ hiếm. Module này chấm lại danh sách ứng
viên tsv đã lọc ra (tra_cuu.tim_ma) bằng bốn luật:

  1. Độ phủ từ có trọng số IDF (0–100): từ hiếm trong Biểu thuế nặng hơn từ phổ biến.
  2. Phủ định theo cụm: phạm vi "không / chưa / trừ" chạy tới hết mệnh đề (qua dấu phẩy
     khi vế sau ≤ 3 từ, dừng ở "được/đã/có/ở/kể/với"); chỉ phạt khi mô tả nói về từ ấy
     DUY NHẤT trong phạm vi phủ định — "điều hòa không khí … không điều chỉnh độ ẩm" không oan.
  3. Cụm 2 từ liền nhau (+12, cụm toàn từ chung +3, trần 36) và chuỗi ≥ 3 từ liền mạch (+8/từ).
  4. Mô tả dài trừ nhẹ; từ phủ định của người dùng không tính vào độ phủ.

Luật này là NGUỒN; bản độc lập trong Ecustoms/skills/hqskills/scripts/query_hs.py (xep_hang,
tu_bi_phu_dinh, lech_phu_dinh) phải chép theo đây — đổi ở đây thì đổi bên ấy, có bộ thử
`danh_gia.py` của skill đo trước/sau.
"""

from __future__ import annotations

import json
import math
import pathlib
import re
import unicodedata
from functools import lru_cache
from typing import Any, Iterable

import unicodedata

_THAY_TRUOC = str.maketrans({"đ": "d", "Đ": "D"})


def bo_dau(t: str) -> str:
    """Như ILMS chong_trung.bo_dau: bỏ dấu + hạ chữ thường (không bỏ dấu câu, không gộp khoảng trắng)."""
    nfd = unicodedata.normalize("NFD", t.translate(_THAY_TRUOC))
    return "".join(c for c in nfd if not unicodedata.combining(c)).lower()

PHU_DINH = frozenset({"khong", "chua", "tru"})
# Mở phạm vi PHỤ THUỘC: chữ sau đó tả hàng KHÁC mà mã này đi kèm ("ắc quy DÙNG CHO máy tính xách tay",
# "bộ phận CỦA điện thoại di động") — người dùng gõ đúng chữ ấy không có nghĩa là hàng này.
# "cua" không dấu vừa là "của" vừa là "cửa" (cửa sổ) — chỉ coi là "của" khi đứng ĐẦU mệnh đề ("- - - Của điện
# thoại di động") hoặc ngay sau "bộ phận / phụ kiện / linh kiện".
PHU_THUOC_1 = frozenset({"cua"})
TRUOC_CUA = frozenset({"", "phan", "kien"})
PHU_THUOC_2 = frozenset({("dung", "cho"), ("danh", "cho"), ("dung", "voi")})   # KHÔNG "lắp vào/dùng trong": đó là
# công dụng của chính hàng ("Loại lắp vào cửa sổ, tường", "máy dùng trong nông nghiệp") — phạt là oan.
KET_PHU_DINH = frozenset({"duoc", "da", "co", "o", "ke", "voi", "dang"})   # từ mở vị ngữ/thuộc tính mới — hết phạm vi
VE_NGAN = 5   # qua dấu phẩy vẫn còn trong phạm vi khi vế sau ≤ 5 từ ("trừ máy tính cá nhân, máy tính xách tay")
TU_CHUNG = frozenset({"tu", "dong", "xu", "ly", "loai", "khac", "dang", "co", "chua", "da", "cac", "va",
                      "hoac", "bang"})
PHAT_LECH_PHU_DINH = 35   # người dùng "không X", mô tả có X khẳng định
PHAT_THIEU_PHU_DINH = 25  # người dùng "X", mô tả chỉ nói X trong phạm vi phủ định (tối đa 2 từ)
NGUONG_NOI_LONG = 50 - 400 / 40   # khớp ≥ nửa số từ sau khi trừ tối đa cho mô tả dài

_NGOAC = re.compile(r"\([^)]*\)")
_TU = re.compile(r"[a-z]+|\d+")


def tach_tu(s: str) -> list[str]:
    """Từ không dấu, chữ thường; số bỏ dấu phân cách nghìn và tách khỏi đơn vị ("1.000 V", "1000V" → 1000, v)."""
    s = re.sub(r"(\d)[.,](\d{3})(?!\d)", r"\1\2", bo_dau(s or ""))
    return _TU.findall(s)


def tu_bi_phu_dinh(desc: str) -> frozenset[str]:
    """Tập từ của mô tả CHỈ xuất hiện trong phạm vi phủ định hoặc phụ thuộc (luật 2 ở đầu tệp).

    Tính RIÊNG phần nhóm (đoạn đầu, chung cho mọi mã con) và phần mã con (các đoạn sau " - - "). Từ khẳng
    định ở tên nhóm chuộc được từ bị PHỦ ĐỊNH ở mã con ("Máy điều hòa không khí - - … không điều chỉnh độ ẩm")
    nhưng KHÔNG chuộc được từ PHỤ THUỘC ở mã con ("Bộ điện thoại … - - - Của điện thoại di động" là BỘ PHẬN —
    người gõ "điện thoại di động" không được dẫn tới đó)."""
    pd, pt = tu_bi_phu_dinh_2(desc)
    return pd | pt


def tu_bi_phu_dinh_2(desc: str) -> tuple[frozenset[str], frozenset[str]]:
    """Như tu_bi_phu_dinh nhưng tách (từ bị PHỦ ĐỊNH, từ trong phạm vi PHỤ THUỘC) — người dùng tự nói
    "dùng cho ô tô con" thì phạm vi phụ thuộc không còn là lệch."""
    doan = _DOAN.split(_NGOAC.sub(" ", desc or ""))
    pd_a, pt_a, duong_a = _quet(doan[:1])
    pd_b, pt_b, duong_b = _quet(doan[1:])
    pd = frozenset((pd_a - duong_a) | (pd_b - duong_b - duong_a))
    pt = frozenset((pt_a - duong_a) | (pt_b - duong_b)) - pd
    return pd, pt


_DOAN = re.compile(r"\s-(?:\s-)+\s")
_RANH_TRONG_DOAN = re.compile(r"[;:]")


def _quet(cac_doan: list[str]) -> tuple[set[str], set[str], set[str]]:
    """(từ trong phạm vi phủ định, từ trong phạm vi phụ thuộc, từ khẳng định) của một nhóm đoạn."""
    phu_dinh: set[str] = set()
    phu_thuoc: set[str] = set()
    duong: set[str] = set()
    for menh_de in _RANH_TRONG_DOAN.split(bo_dau(" ; ".join(cac_doan))):
        ve = [_TU.findall(v) for v in menh_de.split(",")]
        pham_vi: set[str] | None = None
        for i, tu_ve in enumerate(ve):
            if i and (len(tu_ve) > VE_NGAN or not tu_ve):
                pham_vi = None
            truoc = ""
            for t in tu_ve:
                if t in PHU_DINH:
                    pham_vi, truoc = phu_dinh, t
                    continue
                if t in PHU_THUOC_1 and truoc in TRUOC_CUA:
                    pham_vi, truoc = phu_thuoc, t
                    continue
                if (truoc, t) in PHU_THUOC_2:
                    pham_vi = phu_thuoc
                    duong.discard(truoc)   # "dung" vừa ghi vào dương — nó chỉ là đầu cụm mở phạm vi
                    truoc = t
                    continue
                if t in KET_PHU_DINH:
                    pham_vi = None
                (pham_vi if pham_vi is not None else duong).add(t)
                truoc = t
    return phu_dinh, phu_thuoc, duong


@lru_cache(maxsize=20_000)
def phan_tich(desc_vn: str, desc_en: str) -> "MoTa":
    """Phân tích một mô tả, nhớ theo tiến trình: mỗi lượt chấm lại ~400 mô tả và cùng những mô tả ấy quay lại
    ở mọi lượt gõ, nên mọi thứ không phụ thuộc truy vấn đều tính sẵn ở đây."""
    return MoTa(desc_vn, desc_en)


class MoTa:
    __slots__ = ("vn", "chu", "dau3", "pd", "pt", "vn_k", "vn_k_pd", "vn_k_pdpt", "phat_dai")

    def __init__(self, desc_vn: str, desc_en: str):
        tu_vn = tach_tu(desc_vn)
        self.vn = " ".join(tu_vn)
        self.chu = frozenset(tu_vn) | frozenset(tach_tu(desc_en))
        self.dau3 = frozenset(c[:3] for c in self.chu)        # chặn sớm phép khớp đầu từ
        self.pd, self.pt = tu_bi_phu_dinh_2(desc_vn)
        # Chuỗi dò cụm/chuỗi với từ trong phạm vi thay bằng "|" — hai biến thể theo việc có tính phụ thuộc hay không
        self.vn_k = f" {self.vn} "
        self.vn_k_pd = self._che(self.pd)
        self.vn_k_pdpt = self._che(self.pd | self.pt)
        self.phat_dai = min(len(self.vn), 400) / 40

    def _che(self, am: frozenset[str]) -> str:
        return " " + " ".join("|" if w in am else w for w in self.vn.split()) + " " if am else self.vn_k


def nguoi_dung_noi_phu_thuoc(tu: list[str]) -> bool:
    """Tên hàng của người dùng có "dùng cho / dành cho / dùng với / của" → họ đang tả cả ngữ cảnh dùng."""
    return any(t in PHU_THUOC_1 for t in tu) or any((a, b) in PHU_THUOC_2 for a, b in zip(tu, tu[1:]))


def lech_phu_dinh(tu: list[str], vn: str, am: frozenset[str]) -> tuple[int, int]:
    """(nặng, nhẹ): nặng = người dùng phủ định X mà mô tả có X khẳng định; nhẹ = ngược lại (trần 2)."""
    vn_k = f" {vn} "
    nang = sum(1 for a, b in zip(tu, tu[1:]) if a in PHU_DINH and b not in am and f" {b} " in vn_k)
    nguoi_dung_phu_dinh = {b for a, b in zip(tu, tu[1:]) if a in PHU_DINH}
    nhe = sum(1 for t in tu if t in am and t not in PHU_DINH and t not in nguoi_dung_phu_dinh)
    return nang, min(nhe, 2)


def idf_tu_df(df: dict[str, int], n: int) -> dict[str, float]:
    """IDF chuẩn (log((N+1)/(df+1)) + 1) từ bảng từ → số mã chứa từ (lấy từ ts_stat trên hs_codes.tsv)."""
    n = max(n, 1)
    return {t: math.log((n + 1) / (d + 1)) + 1 for t, d in df.items()}


class TruyVan:
    """Phần tính MỘT LẦN cho mỗi tên hàng (không phụ thuộc mã): từ, mẫu số IDF, cặp/chuỗi cần dò, cách lấy phạm vi.
    Trước đây tính lại trong cham() cho từng mã — riêng phép dò từ lạ trong bộ từ vựng (any(k.startswith…)) chạy
    O(từ vựng) × 400 mã mỗi lượt gõ."""

    __slots__ = ("tu", "noi_dung", "tong_idf", "idf", "cap", "chuoi", "ca_cau", "bo_phu_thuoc", "co_phu_dinh", "cuoi")

    def __init__(self, q: str, idf: dict[str, float]):
        tu = list(dict.fromkeys(tach_tu(q)))
        self.tu = tu
        self.idf = idf
        # Mẫu số độ phủ: bỏ từ phủ định của người dùng, và bỏ từ KHÔNG CÓ trong Biểu thuế ("zzqqxx", mã nội bộ) —
        # không mã nào khớp được nó nên để lại chỉ kéo mọi mã xuống dưới ngưỡng; nó vẫn làm đủ_từ=False.
        noi_dung = [t for t in tu if t not in PHU_DINH and (not idf or t in idf or any(k.startswith(t) for k in idf))]
        self.noi_dung = noi_dung or [t for t in tu if t not in PHU_DINH] or tu
        self.tong_idf = sum(idf.get(t, 1.0) for t in self.noi_dung) or 1.0
        self.cap = [(f" {a} {b} ", 3 if (a in TU_CHUNG and b in TU_CHUNG) else 12) for a, b in zip(tu, tu[1:])]
        self.chuoi = [(f" {' '.join(tu[i:i + k])} ", 8 * (k - 2))
                      for k in range(len(tu), 2, -1) for i in range(len(tu) - k + 1)]   # dài trước: gặp là dừng
        self.ca_cau = f" {' '.join(tu)} "
        self.bo_phu_thuoc = nguoi_dung_noi_phu_thuoc(tu)   # người dùng tự nói "dùng cho…" thì phụ thuộc không là lệch
        self.co_phu_dinh = any(t in PHU_DINH for t in tu)
        self.cuoi = tu[-1] if tu else ""   # từ đang gõ dở: khớp đầu từ dù ngắn ('thep h' → 'hinh'), như tsquery 'h:*'


def cham(tv: TruyVan, desc_vn: str, desc_en: str) -> tuple[float, bool]:
    """Điểm một mã cho truy vấn `tv`. Trả (điểm, đủ_từ)."""
    tu = tv.tu
    m = phan_tich(desc_vn or "", desc_en or "")
    chu = m.chu
    khop = [t for t in tu if t in chu
            or ((len(t) >= 3 and t[:3] in m.dau3) or t == tv.cuoi) and any(c.startswith(t) for c in chu)]
    if not khop:
        return float("-inf"), False
    idf = tv.idf
    phu = sum(idf.get(t, 1.0) for t in khop if t in tv.noi_dung) / tv.tong_idf * 100
    # Thưởng cụm/chuỗi chỉ tính trên phần KHẲNG ĐỊNH: từ trong phạm vi phủ định/phụ thuộc đã thay bằng "|"
    # để "Của điện thoại di động" không ăn thưởng cụm liền của người gõ "điện thoại di động".
    am, vn_k = (m.pd, m.vn_k_pd) if tv.bo_phu_thuoc else (m.pd | m.pt, m.vn_k_pdpt)
    cum2 = sum(d for c, d in tv.cap if c in vn_k)
    chuoi = next((d for c, d in tv.chuoi if c in vn_k), 0)
    nang, nhe = lech_phu_dinh(tu, m.vn, am) if am or tv.co_phu_dinh else (0, 0)
    diem = (phu + (30 if tv.ca_cau in vn_k else 0) + min(cum2, 36) + chuoi + 10
            - m.phat_dai - nang * PHAT_LECH_PHU_DINH - nhe * PHAT_THIEU_PHU_DINH)
    return diem, all(t in khop for t in tu if t not in PHU_DINH)


# ---------------------------------------------------------------- từ thương mại → từ Biểu thuế
# Người khai gõ "inox", "laptop", "tôn"; Biểu thuế viết "thép không gỉ", "máy xử lý dữ liệu tự động xách tay",
# "thép cán phẳng". Bảng ở db/tra_cuu_seed/tu_dong_nghia.json — CHỈ cặp tương đương đã chắc, không suy diễn;
# HQskills giữ bản chép (Ecustoms/skills/hqskills/data/tu_dong_nghia.json), test canh hai bản khớp nhau.
TEP_DONG_NGHIA = pathlib.Path(__file__).resolve().parents[1] / "data" / "tu_dong_nghia.json"


def _chu_co_dau(s: str) -> str:
    """Chữ thường, GIỮ dấu, chuẩn NFC, cách bằng một khoảng trắng. So từ đồng nghĩa phải giữ dấu: không dấu thì
    "tôn" (tôn thép) trùng "tồn" (tồn kho) và "ô tô" trùng "ô tô"/"ổ" … — đổi nhầm tên hàng của người dùng."""
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFC", s or "").lower()))


@lru_cache(maxsize=1)
def bang_dong_nghia() -> tuple[tuple[str, str], ...]:
    """((từ thương mại có dấu, từ Biểu thuế), …) — cụm dài trước để "tôn mạ kẽm" thắng "tôn"."""
    d = json.loads(TEP_DONG_NGHIA.read_text(encoding="utf-8"))
    cap = {_chu_co_dau(k): _chu_co_dau(v) for k, v in d.items() if not k.startswith("_")}
    return tuple(sorted(cap.items(), key=lambda kv: -len(kv[0])))


def doi_dong_nghia(q: str) -> tuple[str, dict[str, str]]:
    """Thay từ thương mại bằng từ Biểu thuế (theo NGUYÊN từ, có dấu). Trả (chuỗi mới, {cũ: mới} đã thay);
    không thay gì thì trả nguyên `q`. Bảng chỉ ghi từ KHÔNG có trong Biểu thuế (xem _meta của tệp JSON)."""
    s = f" {_chu_co_dau(q)} "
    da = {}
    for cu, moi in bang_dong_nghia():
        if f" {cu} " in s:
            s = s.replace(f" {cu} ", f" {moi} ")
            da[cu] = moi
    return (s.strip(), da) if da else (q, {})


# ---------------------------------------------------------------- tiền lệ (tầng 1)
# Tiền lệ = mã người dùng ĐÃ CHỌN cho một tên hàng (hs_goi_y_log.ma_chon). Tên hàng mới giống tên hàng cũ
# (Jaccard trên tập từ ≥ NGUONG_TIEN_LE) thì mã đã chọn được cộng điểm — đây là nguồn duy nhất biết "mặc định
# đời thường" (lốp "dùng cho ô tô con" thường là lốp MỚI) mà xếp hạng theo chữ không biết.
NGUONG_TIEN_LE = 0.6
THUONG_TIEN_LE = 60      # điểm cho tiền lệ giống hệt; nhân với độ giống
TRAN_THUONG_TIEN_LE = 90


def tap_tu(q: str) -> frozenset[str]:
    return frozenset(t for t in tach_tu(q) if t not in PHU_DINH)


def thuong_tien_le(q: str, tien_le: Iterable[tuple[int, frozenset[str], str]],
                   bo_id: int | None = None) -> dict[str, tuple[float, int]]:
    """{mã: (điểm cộng, số lần đã chọn)} từ các tiền lệ (id, tập từ, mã chọn) giống tên hàng `q`.
    `bo_id`: bỏ một tiền lệ (đo kiểu leave-one-out không được tự trúng chính mình)."""
    a = tap_tu(q)
    if not a:
        return {}
    cong: dict[str, list] = {}
    for i, b, ma in tien_le:
        if i == bo_id or not b:
            continue
        giong = len(a & b) / len(a | b)
        if giong >= NGUONG_TIEN_LE:
            x = cong.setdefault(ma, [0.0, 0])
            x[0] += THUONG_TIEN_LE * giong
            x[1] += 1
    return {ma: (min(d, TRAN_THUONG_TIEN_LE), n) for ma, (d, n) in cong.items()}


def cham_mot(tv: TruyVan, r: dict[str, Any], thuong: dict[str, tuple[float, int]]) -> tuple[float, bool, dict[str, Any]]:
    """(điểm, đủ_từ, dòng) của một ứng viên, đã cộng tiền lệ: mã có tiền lệ được cộng điểm, coi như đủ từ, mang
    `tien_le` = số lần đã chọn. Điểm -inf = không khớp từ nào và không có tiền lệ (loại). HQskills gọi thẳng hàm này."""
    d, du = cham(tv, r.get("desc_vn") or "", r.get("desc_en") or "")
    t = thuong.get(r.get("code", ""))
    if t:
        return (d if d != float("-inf") else 0.0) + t[0], True, dict(r, tien_le=t[1])
    return d, du, r


def chon_du_tu(cham_xong: list[tuple[float, bool, Any]]) -> tuple[list, bool]:
    """Đã xếp → (danh sách giữ, khớp_một_phần): có mã đủ từ thì chỉ giữ chúng; không thì giữ mã ≥ NGUONG_NOI_LONG."""
    du_tu = [x for x in cham_xong if x[1]]
    return (du_tu, False) if du_tu else ([x for x in cham_xong if x[0] >= NGUONG_NOI_LONG], True)


def xep_hang(q: str, ung_vien: Iterable[dict[str, Any]], idf: dict[str, float], limit: int,
             thuong: dict[str, tuple[float, int]] | None = None) -> tuple[list[dict[str, Any]], bool]:
    """Chấm lại ứng viên (dict có desc_vn/desc_en/code) → (danh sách đã xếp, cắt `limit`, thêm `diem`; khớp_một_phần).

    Có mã đủ mọi từ thì chỉ giữ các mã ấy; không có thì giữ mã ≥ NGUONG_NOI_LONG và cờ khớp_một_phần=True.
    `thuong` (thuong_tien_le): mã có tiền lệ được cộng điểm, coi như đủ từ, và mang `tien_le` = số lần đã chọn."""
    tv = TruyVan(q, idf)
    if not tv.tu:
        return [], False
    thuong = thuong or {}
    cham_xong = [x for x in (cham_mot(tv, r, thuong) for r in ung_vien) if x[0] != float("-inf")]
    cham_xong.sort(key=lambda x: (-x[0], x[2].get("code", "")))
    chon, mot_phan = chon_du_tu(cham_xong)
    ra = [dict(r, diem=round(d, 1)) for d, _du, r in chon[:limit]]
    return ra, mot_phan and bool(ra)
