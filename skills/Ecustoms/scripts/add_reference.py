#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thêm một văn bản pháp luật/tham khảo mới vào thư mục references/,
để lệnh `query_hs.py refs "<từ khóa>"` tra được ngay.

Cách dùng:
    python add_reference.py --title "QD 1978-2025 CBPG thep hinh H" --category cbpg_pvtm --file "C:\\duong_dan\\file.txt"

    Hoặc dán trực tiếp nội dung (không cần file có sẵn):
    python add_reference.py --title "TT 26-2025 TT-BCT" --category chinh_sach_phap_luat --paste
    (sau đó dán nội dung, kết thúc bằng dòng chỉ có EOF rồi Enter)

Danh mục gợi ý (tự do đặt tên khác nếu cần, script tự tạo thư mục mới):
    chinh_sach_phap_luat  - Nghị định, Thông tư (chính sách nền, áp dụng chung)
    cbpg_pvtm              - Quyết định CBPG/PVTM cho từng vụ việc cụ thể
    cong_van_huong_dan      - Công văn hướng dẫn nghiệp vụ của Hải quan/Bộ
    (không truyền --category thì lưu thẳng vào gốc references/)

Ghi chú: nếu file gốc là PDF/DOCX, hãy copy phần văn bản (text) ra rồi
dùng --paste hoặc lưu thành .txt trước, script này chỉ nhận văn bản
thuần (txt/md).
"""
import sys
import io
import os
import re
import argparse
import unicodedata
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(BASE, "references")


def slugify(text, max_len=50):
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    text = text or "van_ban"
    # Giới hạn độ dài tên file để tránh vượt MAX_PATH (260 ký tự) trên
    # Windows, nhất là khi thư mục gốc dự án đã dài (vd scratch workspace).
    if len(text) > max_len:
        text = text[:max_len].rstrip("_")
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True, help="Tên/tiêu đề văn bản, dùng để đặt tên file")
    ap.add_argument("--file", help="Đường dẫn file .txt/.md nguồn để copy vào references/")
    ap.add_argument("--paste", action="store_true", help="Dán nội dung trực tiếp qua stdin, kết thúc bằng dòng 'EOF'")
    ap.add_argument("--category", default=None, help="Thư mục con để phân loại (vd chinh_sach_phap_luat, cbpg_pvtm, cong_van_huong_dan). Bỏ trống để lưu ở gốc references/")
    ap.add_argument("--so-hieu", help="Số hiệu văn bản (vd 3765/QĐ-BCT) — bắt buộc khi gửi lên ILMS")
    ap.add_argument("--ngay", help="Ngày ban hành YYYY-MM-DD (tùy chọn)")
    ap.add_argument("--co-quan", default="", help="Cơ quan ban hành (tùy chọn)")
    args = ap.parse_args()

    target_dir = os.path.join(REFS, args.category) if args.category else REFS
    os.makedirs(target_dir, exist_ok=True)
    fname = slugify(args.title) + ".txt"
    dest = os.path.join(target_dir, fname)

    header = f"[Tiêu đề] {args.title}\n[Ngày thêm vào tool] {date.today().isoformat()}\n" + "-" * 60 + "\n\n"

    if args.file:
        if not os.path.exists(args.file):
            print(f"Không tìm thấy file: {args.file}")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    elif args.paste:
        print("Dán nội dung văn bản, kết thúc bằng một dòng chỉ có: EOF")
        lines = []
        for line in sys.stdin:
            if line.strip() == "EOF":
                break
            lines.append(line)
        content = "".join(lines)
    else:
        print("Cần --file <đường dẫn> hoặc --paste.")
        sys.exit(1)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ilms_api
    if ilms_api.bat():
        # Có ILMS_URL: gửi thẳng vào kho chung của ILMSv2, không lưu tệp máy
        # (một nguồn duy nhất — nhân viên thấy ngay trên tab Tra cứu HS).
        if not (args.so_hieu and args.category):
            sys.exit("Gửi lên ILMS cần --so-hieu và --category.")
        row = ilms_api.them_van_ban({"so_hieu": args.so_hieu, "ten": args.title, "loai": args.category,
                                     "ngay_ban_hanh": args.ngay, "co_quan": args.co_quan}, content)
        print(f"Đã thêm vào kho ILMS: [{row['id']}] {row['so_hieu']} (mã HS trong bài được trích tự động)")
        return

    with open(dest, "w", encoding="utf-8") as f:
        f.write(header + content)

    print(f"Đã lưu văn bản vào: {dest}")
    print(f"Tra ngay bằng: python scripts/query_hs.py refs \"<từ khóa>\"")


if __name__ == "__main__":
    main()
