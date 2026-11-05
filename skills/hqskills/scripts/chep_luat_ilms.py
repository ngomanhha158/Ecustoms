# -*- coding: utf-8 -*-
"""Chép khối LUẬT của pvtm_local.py từ ILMSv2 `backend/app/services/pvtm.py`.

MỘT luật MỘT chỗ: luật tính thuế phòng vệ (kể cả soát lô theo quy cách, phase138)
viết ở ILMS. Skill không viết lại luật, chỉ chép nguyên văn bằng script này:

    python scripts/chep_luat_ilms.py <đường dẫn ILMS>/backend/app/services/pvtm.py [--commit <sha>]

Script thay đoạn giữa hai dòng mốc `# ===… LUẬT` và `# ===… HẾT LUẬT` trong
pvtm_local.py. Chỉ bỏ những gì chạm CSDL / module khác của ILMS (docstring đầu
tệp, import, `sql_dang_ap`); mọi dòng còn lại giữ NGUYÊN VĂN. Chép xong chạy
`python -m unittest discover -s tests` và (có ILMS_URL) `python scripts/kiem_khop.py`.

Cùng lượt, nếu cạnh pvtm.py có `kiem_tra_dong.py` (phiếu kiểm tra dòng hàng — lệnh `kiemtra`), chép NGUYÊN
TỆP thành `kiem_tra_dong_local.py`: chỉ đổi các dòng `from .x import …` thành `from pvtm_local import …`
(bo_dau và luật PVTM đã có trong pvtm_local).
"""
import argparse
import ast
import os
import re
import sys

DICH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pvtm_local.py")
MOC_DAU = "# ================================================================ LUẬT"
MOC_CUOI = "# ================================================================ HẾT LUẬT"
DICH_KT = os.path.join(os.path.dirname(DICH), "kiem_tra_dong_local.py")
BO_HAM = {"sql_dang_ap"}   # sinh câu SQL — skill không có CSDL


def khoi_luat(nguon: str, commit: str) -> str:
    cay = ast.parse(nguon)
    dong = nguon.splitlines()
    bo = set()
    for nut in cay.body:
        la_doc = isinstance(nut, ast.Expr) and isinstance(getattr(nut, "value", None), ast.Constant) \
            and isinstance(nut.value.value, str)
        if isinstance(nut, (ast.Import, ast.ImportFrom)) or (la_doc and nut is cay.body[0]) \
                or (isinstance(nut, ast.FunctionDef) and nut.name in BO_HAM):
            dau = min([nut.lineno] + [d.lineno for d in getattr(nut, "decorator_list", [])])
            bo.update(range(dau - 1, nut.end_lineno))
    than = "\n".join(d for i, d in enumerate(dong) if i not in bo)
    than = re.sub(r"\n{4,}", "\n\n\n", than).strip("\n")
    return (f"{MOC_DAU} — chép nguyên văn ILMS services/pvtm.py (commit {commit})\n"
            f"# KHÔNG SỬA TAY: sửa ở ILMS rồi chạy scripts/chep_luat_ilms.py.\n\n{than}\n\n\n{MOC_CUOI}")


def chep_kiem_tra(nguon: str, commit: str) -> str:
    """kiem_tra_dong.py nguyên văn; import tương đối của ILMS -> một dòng `from pvtm_local import …`."""
    dong = nguon.splitlines()
    ten, bo = [], set()
    for nut in ast.parse(nguon).body:
        if isinstance(nut, ast.ImportFrom) and nut.level:
            ten += [a.name for a in nut.names]
            bo.update(range(nut.lineno - 1, nut.end_lineno))
    if not ten:
        raise SystemExit("kiem_tra_dong.py không có import tương đối nào — mẫu tệp đã đổi, soát lại script")
    dau = min(bo)
    ra = [d for i, d in enumerate(dong) if i not in bo]
    ra.insert(dau, f"from pvtm_local import {', '.join(sorted(set(ten)))}  # noqa: F401")
    return (f"# Chép nguyên văn ILMS services/kiem_tra_dong.py (commit {commit}) — KHÔNG SỬA TAY:\n"
            "# sửa ở ILMS rồi chạy scripts/chep_luat_ilms.py.\n" + "\n".join(ra) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("nguon", help="đường dẫn tới ILMS backend/app/services/pvtm.py")
    ap.add_argument("--commit", default="?", help="commit ILMS đang chép (ghi vào mốc để truy lại)")
    a = ap.parse_args()
    with open(a.nguon, encoding="utf-8") as f:
        moi = khoi_luat(f.read(), a.commit)
    with open(DICH, encoding="utf-8") as f:
        cu = f.read()
    i, j = cu.find(MOC_DAU), cu.find(MOC_CUOI)
    if i < 0 or j < i:
        sys.exit(f"Không thấy hai mốc LUẬT / HẾT LUẬT trong {DICH}")
    with open(DICH, "w", encoding="utf-8") as f:
        f.write(cu[:i] + moi + cu[j + len(MOC_CUOI):])
    print(f"Đã chép luật ILMS (commit {a.commit}) vào {os.path.relpath(DICH)}.")
    kt = os.path.join(os.path.dirname(os.path.abspath(a.nguon)), "kiem_tra_dong.py")
    if os.path.exists(kt):
        with open(kt, encoding="utf-8") as f:
            moi = chep_kiem_tra(f.read(), a.commit)
        with open(DICH_KT, "w", encoding="utf-8") as f:
            f.write(moi)
        print(f"Đã chép phiếu kiểm tra dòng hàng vào {os.path.relpath(DICH_KT)}.")


if __name__ == "__main__":
    main()
