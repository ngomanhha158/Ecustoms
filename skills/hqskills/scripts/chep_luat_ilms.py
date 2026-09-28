# -*- coding: utf-8 -*-
"""Chép khối LUẬT của pvtm_local.py từ ILMSv2 `backend/app/services/pvtm.py`.

MỘT luật MỘT chỗ: luật tính thuế phòng vệ (kể cả soát lô theo quy cách, phase138)
viết ở ILMS. Skill không viết lại luật, chỉ chép nguyên văn bằng script này:

    python scripts/chep_luat_ilms.py <đường dẫn ILMS>/backend/app/services/pvtm.py [--commit <sha>]

Script thay đoạn giữa hai dòng mốc `# ===… LUẬT` và `# ===… HẾT LUẬT` trong
pvtm_local.py. Chỉ bỏ những gì chạm CSDL / module khác của ILMS (docstring đầu
tệp, import, `sql_dang_ap`); mọi dòng còn lại giữ NGUYÊN VĂN. Chép xong chạy
`python -m unittest discover -s tests` và (có ILMS_URL) `python scripts/kiem_khop.py`.
"""
import argparse
import ast
import os
import re
import sys

DICH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pvtm_local.py")
MOC_DAU = "# ================================================================ LUẬT"
MOC_CUOI = "# ================================================================ HẾT LUẬT"
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


if __name__ == "__main__":
    main()
