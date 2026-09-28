# -*- coding: utf-8 -*-
"""Hai hàm nền mà luật PVTM của ILMS import từ module khác (pvtm_luat.py dùng).

Chép từ ILMSv2: `services/chong_trung.bo_dau` và `services/tra_cuu.la_ma_hs`.
Đổi ở ILMS thì sửa theo — kiem_khop.py sẽ báo lệch nếu quên.
"""
import re
import unicodedata

_THAY_TRUOC = str.maketrans("ĐđØøŁł", "DdOoLl")


def bo_dau(t):
    """Bản Python của khong_dau(text) SQL — bỏ dấu + hạ chữ thường, không gộp khoảng trắng."""
    nfd = unicodedata.normalize("NFD", (t or "").translate(_THAY_TRUOC))
    return "".join(c for c in nfd if not unicodedata.combining(c)).lower()


def la_ma_hs(q):
    """'7228.70.10' / '722870' / '7228 70' -> chuỗi số; chữ hay lẫn chữ -> None."""
    so = re.sub(r"[.\s]", "", (q or "").strip())
    return so if len(so) >= 2 and so.isdigit() else None
