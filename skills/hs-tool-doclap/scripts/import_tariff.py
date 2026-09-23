#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nhập dữ liệu Biểu thuế XNK từ file Excel (.xlsx) hoặc CSV vào data/hs_tree.json.

File nguồn cần có các cột (tên cột có thể tùy chỉnh bằng tham số --map,
mặc định nhận diện các tên cột tiếng Việt thông dụng):
    Mã HS | Mô tả VN | Mô tả EN | Phần | Chương | Đơn vị |
    Thuế NK thông thường | Thuế MFN | Thuế VAT | Chính sách mặt hàng |
    (các cột FTA: ATIGA, ACFTA, AKFTA, CPTPP, EVFTA, RCEP, ... nếu có)

Cách dùng:
    pip install openpyxl   # nếu dùng file .xlsx
    python import_tariff.py --file "BieuThue2026.xlsx" --sheet "Sheet1"
    python import_tariff.py --file "BieuThue2026.csv"

Script sẽ MERGE vào dữ liệu hiện có trong data/hs_tree.json (không xóa
các mã đã nhập trước đó), trừ khi dùng --replace.
"""
import sys
import io
import os
import json
import re
import argparse
import csv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
TREE_PATH = os.path.join(DATA, "hs_tree.json")

COLUMN_ALIASES = {
    "code": ["ma hs", "ma so hs", "hs code", "ma"],
    "desc_vn": ["mo ta", "mo ta tieng viet", "ten hang", "description"],
    "desc_en": ["mo ta en", "english description", "desc en"],
    "section": ["phan"],
    "chapter": ["chuong"],
    "unit": ["don vi", "dvt"],
    "thue_nk_thong_thuong": ["thue nk thong thuong", "thue suat thong thuong"],
    "mfn": ["thue mfn", "thue nk uu dai", "mfn"],
    "vat": ["thue vat", "vat", "gtgt"],
    "chinh_sach": ["chinh sach mat hang", "chinh sach quan ly"],
}


def strip_accents_lower(s):
    import unicodedata
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.strip().lower()


def detect_columns(header_row):
    mapping = {}
    normed = {strip_accents_lower(h): i for i, h in enumerate(header_row)}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normed:
                mapping[field] = normed[alias]
                break
    return mapping


def read_rows(path, sheet):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        try:
            import openpyxl
        except ImportError:
            print("Cần cài đặt openpyxl: pip install openpyxl")
            sys.exit(1)
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb[sheet] if sheet else wb.active
        rows = [[c if c is not None else "" for c in row] for row in ws.iter_rows(values_only=True)]
        return rows
    elif ext == ".csv":
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return list(csv.reader(f))
    else:
        print(f"Định dạng chưa hỗ trợ: {ext}. Dùng .xlsx hoặc .csv.")
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--replace", action="store_true", help="Xóa dữ liệu cũ trước khi nhập (mặc định là merge)")
    args = ap.parse_args()

    rows = read_rows(args.file, args.sheet)
    if not rows:
        print("File rỗng.")
        return

    header = rows[0]
    mapping = detect_columns(header)
    if "code" not in mapping or "desc_vn" not in mapping:
        print("Không nhận diện được cột 'Mã HS' và/hoặc 'Mô tả'.")
        print("Các cột đọc được:", header)
        print("Hãy đổi tên cột trong file nguồn cho khớp, hoặc chỉnh COLUMN_ALIASES trong script.")
        return

    tree = {"_meta": {}, "codes": {}}
    if os.path.exists(TREE_PATH) and not args.replace:
        with open(TREE_PATH, "r", encoding="utf-8") as f:
            tree = json.load(f)
        tree.setdefault("codes", {})

    count = 0
    for row in rows[1:]:
        if mapping["code"] >= len(row):
            continue
        raw_code = str(row[mapping["code"]] or "").strip()
        code = re.sub(r"\D", "", raw_code)
        if len(code) < 6:
            continue
        entry = {}
        for field, idx in mapping.items():
            if field == "code":
                continue
            if idx < len(row) and row[idx] not in (None, ""):
                entry[field] = str(row[idx]).strip()
        tree["codes"][code] = entry
        count += 1

    with open(TREE_PATH, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    print(f"Đã nhập {count} mã HS vào {TREE_PATH}")


if __name__ == "__main__":
    main()
