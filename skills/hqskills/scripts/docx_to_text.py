#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trích xuất văn bản thuần từ file .docx (không cần thư viện python-docx),
giữ cấu trúc bảng đơn giản (mỗi ô cách nhau bằng " | ", mỗi hàng 1 dòng).

Cách dùng:
    python docx_to_text.py "file.docx" > output.txt
    python docx_to_text.py "file.docx" --out output.txt
"""
import sys
import io
import zipfile
import argparse
import xml.etree.ElementTree as ET

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_text(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)
    root = tree.getroot()
    body = root.find(f"{W_NS}body")
    lines = []

    def handle_table(tbl):
        for tr in tbl.findall(f"{W_NS}tr"):
            cells = []
            for tc in tr.findall(f"{W_NS}tc"):
                texts = []
                for t in tc.iter(f"{W_NS}t"):
                    texts.append(t.text or "")
                cells.append("".join(texts).strip())
            lines.append(" | ".join(cells))

    def handle_para(p):
        texts = []
        for t in p.iter(f"{W_NS}t"):
            texts.append(t.text or "")
        line = "".join(texts)
        lines.append(line)

    for elem in body:
        tag = elem.tag
        if tag == f"{W_NS}p":
            handle_para(elem)
        elif tag == f"{W_NS}tbl":
            handle_table(elem)
            lines.append("")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    text = extract_text(args.docx)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Đã ghi: {args.out}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
