# -*- coding: utf-8 -*-
"""Chép luật tính thuế phòng vệ thương mại từ ILMSv2 sang skill — KHÔNG sửa tay.

    python scripts/chep_luat.py                 # lấy origin/main của repo ILMS trên máy
    python scripts/chep_luat.py --ref <commit>  # hoặc một commit cụ thể

Đọc `backend/app/services/pvtm.py` của repo ILMS (biến ILMS_REPO, mặc định
D:\\ILMSV2\\ilmsv2), thay đúng HAI dòng import nội bộ của ILMS bằng bản trên máy,
ghi ra `scripts/pvtm_luat.py`. Xong chạy `python scripts/kiem_khop.py` — phải 0 lệch.

Vì sao chép nguyên tệp: 28-09 ILMS thêm cả khối "soát quy cách" (phase138) — bản chép
tay từng khối luật không theo kịp, `dongbo` báo 536/563 lệch. Chép nguyên tệp thì
luật hai bên là MỘT văn bản; kiem_khop chỉ còn canh phần dữ liệu và tầng gọi.
"""
import argparse
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DICH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pvtm_luat.py")
NGUON = "backend/app/services/pvtm.py"
THAY = {
    "from .chong_trung import bo_dau\n": "from luat_nen import bo_dau  # ILMS: services/chong_trung.bo_dau\n",
    "from .tra_cuu import la_ma_hs\n": "from luat_nen import la_ma_hs  # ILMS: services/tra_cuu.la_ma_hs\n",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--repo", default=os.environ.get("ILMS_REPO", r"D:\ILMSV2\ilmsv2"))
    a = ap.parse_args()
    if a.ref == "origin/main":
        subprocess.run(["git", "-C", a.repo, "fetch", "-q", "origin"], check=True)
    kq = subprocess.run(["git", "-C", a.repo, "show", f"{a.ref}:{NGUON}"], capture_output=True)
    if kq.returncode:
        raise SystemExit(f"Không đọc được {NGUON} ở {a.ref}: {kq.stderr.decode('utf-8', 'replace').strip()}")
    s = kq.stdout.decode("utf-8")
    for cu, moi in THAY.items():
        if cu not in s:
            raise SystemExit(f"Luật ILMS đổi dòng import '{cu.strip()}' — cập nhật THAY trong chep_luat.py rồi chạy lại.")
        s = s.replace(cu, moi)
    for dong in s.splitlines():
        if dong.startswith("from .") or dong.startswith("import app"):
            raise SystemExit(f"Luật ILMS có import nội bộ mới: '{dong}' — thêm vào luat_nen.py + THAY.")
    ma = subprocess.run(["git", "-C", a.repo, "rev-parse", "--short", a.ref], capture_output=True, text=True).stdout.strip()
    dau = (f"# -*- coding: utf-8 -*-\n# TỰ SINH bởi scripts/chep_luat.py từ ILMSv2 {NGUON} @ {ma}. KHÔNG SỬA TAY —\n"
           f"# ILMS đổi luật thì chạy lại chep_luat.py rồi kiem_khop.py.\n")
    with open(DICH, "w", encoding="utf-8", newline="\n") as f:
        f.write(dau + s)
    print(f"Đã chép luật ILMS @ {ma} -> scripts/pvtm_luat.py. Chạy: python scripts/kiem_khop.py")


if __name__ == "__main__":
    main()
