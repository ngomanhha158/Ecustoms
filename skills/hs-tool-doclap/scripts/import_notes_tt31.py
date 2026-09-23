#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nhập Chú giải pháp lý Phần/Chương từ Phụ lục I Thông tư 31/2022/TT-BTC
(văn bản công khai, Danh mục hàng hóa XNK Việt Nam).

File nguồn .doc cần trích xuất văn bản trước bằng antiword:
    antiword -m UTF-8.txt "TT_31_2022_phu_luc.doc" > tt31_extract.txt

Sau đó:
    python scripts/import_notes_tt31.py --file tt31_extract.txt

Ghi vào data/chapter_notes.json.

Cách nhận diện: antiword xuất văn bản dạng bảng "|VN...|   |EN...|".
Script quét từng dòng, tách 2 cột VN/EN, nhận diện các mốc:
  - "PHẦN <số La Mã>" / "SECTION <số>"  -> bắt đầu 1 Phần mới
  - "Chương <số>" / "Chapter <số>" (số khớp nhau)  -> bắt đầu 1 Chương mới
  - dòng có mã nhóm 4 số dạng "NN.NN" (vd "01.01")  -> hết phần Chú giải,
    bắt đầu bảng nhóm hàng (không cần thu thập tiếp cho chapter_notes)
Toàn bộ văn bản giữa mốc "Chương N" và mốc heading đầu tiên (hoặc
Chương kế tiếp) được lưu làm Chú giải của Chương N.
"""
import sys
import io
import os
import re
import json
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT_PATH = os.path.join(DATA, "chapter_notes.json")

CHUONG_RE = re.compile(r"^Chương\s+(\d{1,2})\.?$")
CHAPTER_EN_RE = re.compile(r"^Chapter\s+(\d{1,2})\.?$")
HEADING_RE = re.compile(r"^\d{2}\.\d{2}$")


def split_cells(line):
    parts = [p.strip() for p in line.split("|")]
    return [p for p in parts if p]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="File .txt đã trích xuất bằng antiword")
    ap.add_argument("--replace", action="store_true")
    args = ap.parse_args()

    with open(args.file, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    chapters = {}
    if os.path.exists(OUT_PATH) and not args.replace:
        with open(OUT_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
        chapters = existing.get("chapters", {})

    current_chapter = None
    buf = []
    in_heading_table = False

    def flush():
        nonlocal buf, current_chapter
        if current_chapter and buf:
            text = "\n".join(buf).strip()
            if text:
                chapters[str(current_chapter)] = text
        buf = []

    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        cells = split_cells(line)
        if not cells:
            continue
        vn = cells[0]

        m = CHUONG_RE.match(vn)
        if m:
            # xác nhận cột thứ 2 (EN) cũng khớp "Chapter N" cùng số, để
            # loại các câu văn có nhắc "Chương N" giữa nội dung Chú giải
            num = m.group(1)
            en_match = False
            for c in cells[1:]:
                em = CHAPTER_EN_RE.match(c)
                if em and em.group(1) == num:
                    en_match = True
                    break
            if en_match:
                flush()
                current_chapter = num
                in_heading_table = False
                continue

        if HEADING_RE.match(vn):
            # đã sang bảng liệt kê nhóm hàng -> dừng thu thập Chú giải Chương này
            in_heading_table = True
            continue

        if current_chapter and not in_heading_table:
            # bỏ dòng lặp lại tiêu đề Chương/tên Chương đã có trong desc ở hs_tree
            buf.append(vn)

    flush()

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "_meta": {
                "source": "Phụ lục I Thông tư 31/2022/TT-BTC (văn bản công khai)",
            },
            "chapters": chapters,
        }, f, ensure_ascii=False, indent=2)

    print(f"Đã nhập Chú giải cho {len(chapters)} Chương.")
    print(f"Ghi vào: {OUT_PATH}")


if __name__ == "__main__":
    main()
