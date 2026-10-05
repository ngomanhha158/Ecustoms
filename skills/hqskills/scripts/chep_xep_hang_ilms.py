# -*- coding: utf-8 -*-
"""Chép luật xếp hạng mã HS theo tên hàng từ ILMSv2 sang skill — KHÔNG sửa tay scripts/hs_xep_hang.py.

    python scripts/chep_xep_hang_ilms.py <ILMS>/backend/app/services/hs_xep_hang.py [--commit <sha>]

Nguồn sự thật là ILMS `backend/app/services/hs_xep_hang.py` (một luật một chỗ). Bản chép chỉ khác hai dòng:
`bo_dau` lấy từ đây thay vì `.chong_trung`, và tệp từ đồng nghĩa trỏ `data/tu_dong_nghia.json` của skill.
Chạy xong: `python -m unittest discover -s tests` (test_dong_bo_xep_hang so lại với ILMS nếu có bản ILMS cạnh).
"""
import argparse
import os
import re
import sys

DICH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hs_xep_hang.py")

_BO_DAU = '''import unicodedata

_THAY_TRUOC = str.maketrans({"đ": "d", "Đ": "D"})


def bo_dau(t: str) -> str:
    """Như ILMS chong_trung.bo_dau: bỏ dấu + hạ chữ thường (không bỏ dấu câu, không gộp khoảng trắng)."""
    nfd = unicodedata.normalize("NFD", t.translate(_THAY_TRUOC))
    return "".join(c for c in nfd if not unicodedata.combining(c)).lower()'''

_TEP = 'TEP_DONG_NGHIA = pathlib.Path(__file__).resolve().parents[1] / "data" / "tu_dong_nghia.json"'


def chuyen(nguon: str, commit: str = "") -> str:
    """Nội dung ILMS → nội dung bản chép skill. Báo lỗi nếu ILMS đổi hai dòng neo (phải sửa script này)."""
    if "from .chong_trung import bo_dau" not in nguon:
        raise SystemExit("Không thấy 'from .chong_trung import bo_dau' trong bản ILMS — sửa chep_xep_hang_ilms.py.")
    if not re.search(r"^TEP_DONG_NGHIA = .*$", nguon, re.M):
        raise SystemExit("Không thấy dòng TEP_DONG_NGHIA trong bản ILMS — sửa chep_xep_hang_ilms.py.")
    dau = (f"# BẢN CHÉP TỰ ĐỘNG từ ILMSv2 backend/app/services/hs_xep_hang.py{' @ ' + commit if commit else ''}.\n"
           "# Đừng sửa tay — sửa ở ILMS rồi chạy scripts/chep_xep_hang_ilms.py.\n")
    ra = nguon.replace("from .chong_trung import bo_dau", _BO_DAU, 1)
    ra = re.sub(r"^TEP_DONG_NGHIA = .*$", _TEP, ra, count=1, flags=re.M)
    return dau + ra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("nguon")
    ap.add_argument("--commit", default="")
    a = ap.parse_args()
    with open(a.nguon, encoding="utf-8") as f:
        moi = chuyen(f.read(), a.commit)
    with open(DICH, "w", encoding="utf-8") as f:
        f.write(moi)
    print(f"Đã chép → {DICH}")


if __name__ == "__main__":
    sys.exit(main())
