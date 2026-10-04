# -*- coding: utf-8 -*-
"""Đo tỷ lệ gợi ý đúng của `phanloai` trên bộ thử có nhãn (tên hàng ↔ mã HS đã chốt).

    python scripts/danh_gia.py [data/danh_gia/mau_thu.tsv] [--chi-tiet]

Tệp TSV: cột `ten_hang`, `ma_hs` (8 số), tùy chọn `ghi_chu`. Kết quả: top-1 / top-3 đúng theo mã 8 số,
nhóm 4 số, và chương — đây là CON SỐ THẬT duy nhất được phép nói về "độ chính xác" của skill.
Bộ mẫu kèm theo chỉ 20 dòng do người viết tự chọn — số đo trên nó là để so trước/sau một thay đổi,
KHÔNG phải độ chính xác thực tế; muốn có % đáng tin phải nạp tờ khai đã thông quan (tầng 1).
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phan_loai as pl  # noqa: E402
import query_hs as q  # noqa: E402


def doc(tep):
    with open(tep, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f, delimiter="\t") if r.get("ten_hang") and r.get("ma_hs")]


def do(dong, codes, chapters, top=3):
    """[(ten, ma_dung, [ma gợi ý theo thứ tự])]."""
    ra = []
    for r in dong:
        kq = pl.phan_loai(r["ten_hang"], codes, chapters, {}, toi_da_nhom=top, toi_da_ma=top)
        goi_y = [m["ma"] for n in kq["nhom"] for m in n["ma"] if len(m["ma"]) == 8]
        ra.append((r["ten_hang"], r["ma_hs"].strip(), goi_y[:top * 3]))
    return ra


def tong_ket(kq):
    n = len(kq)
    def ti_le(cat, k):
        return sum(1 for _t, d, g in kq if d[:cat] in [x[:cat] for x in g[:k]]) / n * 100 if n else 0
    return {"n": n, "ma8_top1": ti_le(8, 1), "ma8_top3": ti_le(8, 3), "nhom4_top1": ti_le(4, 1),
            "nhom4_top3": ti_le(4, 3), "chuong_top1": ti_le(2, 1)}


def main():
    tep = next((a for a in sys.argv[1:] if not a.startswith("--")), os.path.join(pl.DATA, "danh_gia", "mau_thu.tsv"))
    codes = q.load_json("hs_tree.json").get("codes", {})
    chapters = q.load_json("chapter_notes.json").get("chapters", {})
    kq = do(doc(tep), codes, chapters)
    tk = tong_ket(kq)
    print(f"Bộ thử: {tep} — {tk['n']} dòng")
    print(f"Mã 8 số   : top-1 {tk['ma8_top1']:.0f}%  top-3 {tk['ma8_top3']:.0f}%")
    print(f"Nhóm 4 số : top-1 {tk['nhom4_top1']:.0f}%  top-3 {tk['nhom4_top3']:.0f}%")
    print(f"Chương    : top-1 {tk['chuong_top1']:.0f}%")
    if "--chi-tiet" in sys.argv:
        for t, d, g in kq:
            dau = "✓" if g[:1] == [d] else ("~" if d in g[:3] else ("·" if g and g[0][:4] == d[:4] else "✗"))
            print(f"{dau} {d}  ← {', '.join(g[:3]) or '(không)'}  | {t[:70]}")


if __name__ == "__main__":
    main()
