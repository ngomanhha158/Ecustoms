---
name: "Ecustoms"
description: "Tra cứu & hỗ trợ phân loại mã HS (Biểu thuế 2026, Chú giải Chương, GRI, văn bản pháp luật) và tra cứu/tính thuế PHÒNG VỆ THƯƠNG MẠI — chống bán phá giá (CBPG), chống lẩn tránh — theo mã HS, tên hàng, nhà sản xuất, công ty thương mại, mác thép, tiêu chuẩn, số QĐ. Đọc kho chung ILMSv2 khi có ILMS_URL. Dùng khi hỏi mã HS, thuế suất, FTA, chính sách mặt hàng, CBPG/PVTM."
---

# Công cụ tra cứu & hỗ trợ phân loại HS (bản độc lập)

Dữ liệu nền: Biểu thuế XNK, Chú giải Danh mục HS, 6 Quy tắc GRI — đều
là văn bản pháp luật công khai do Bộ Tài chính/Tổng cục Hải quan ban
hành, được người dùng tự nhập/tự cập nhật qua các script trong
`scripts/`.

## Công cụ tra cứu

Chạy từ thư mục của skill này (đường dẫn tuyệt đối tới `scripts/query_hs.py`):

```bash
python scripts/query_hs.py code <mã 8 số>       # tra 1 mã HS
python scripts/query_hs.py search "<từ khóa>"   # tìm mã theo từ khóa (chỉ tham khảo)
python scripts/query_hs.py chapter <số chương>  # Chú giải pháp lý theo Chương
python scripts/query_hs.py heading <4 số>       # Chú giải chi tiết nhóm 4 số
python scripts/query_hs.py gri [số quy tắc]     # toàn văn 6 quy tắc GRI
python scripts/query_hs.py refs "<từ khóa>"     # tra văn bản pháp luật đã thêm (mọi danh mục)
python scripts/query_hs.py refs "<từ khóa>" --category chinh_sach_phap_luat  # chỉ tra NĐ/TT
python scripts/query_hs.py refs "<từ khóa>" --category cbpg_pvtm             # chỉ tra QĐ CBPG/PVTM
python scripts/query_hs.py case "<từ khóa>"     # tra tiền lệ/case đã tự ghi lại
```

Nếu dữ liệu Biểu thuế/Chú giải chưa được nhập, script sẽ báo rõ và
hướng dẫn chạy `scripts/import_tariff.py` — không tự bịa số liệu khi
thiếu dữ liệu.

## Quy trình phân tích gợi ý (người dùng tự điều chỉnh theo kinh nghiệm riêng)

1. Đọc kỹ tên hàng khai báo, tách bản chất/thành phần/công dụng thật
   khỏi các yếu tố không liên quan phân loại (model, NSX, đóng gói...).
2. Nếu đã có mã khai báo: `code <mã>` để đối chiếu mô tả chính thức.
3. Nếu cần tìm/thẩm định mã: đọc `chapter` và `heading` của các nhóm
   nghi vấn, đối chiếu Chú giải loại trừ ở CẢ hai đầu (nhóm nghiêng về
   và nhóm cạnh tranh) trước khi kết luận.
4. Nếu vẫn chưa rõ: áp `gri` theo đúng thứ tự 1 → 2 → 3(a) → 3(b) → 3(c).
5. Tra thêm `refs` cho các văn bản chuyên biệt đã nhập (thuế CBPG, giấy
   phép chuyên ngành...) và `case` cho tiền lệ tự ghi nhận.
6. Khi thiếu thông tin quyết định (thành phần, tỷ lệ, công nghệ sản
   xuất, cấu trúc) — hỏi lại người dùng, không suy đoán.
7. Luôn nêu rõ nguồn: Biểu thuế phiên bản nào, Chú giải theo Thông tư
   nào, để người dùng tự kiểm tra hiệu lực hiện hành (dữ liệu tĩnh có
   thể lỗi thời, cần xác nhận trước khi trích dẫn làm căn cứ chính
   thức).

Xem `README.md` ở thư mục gốc để biết cách nhập/cập nhật dữ liệu.

## Nối với kho chung ILMSv2 (khuyên dùng)

Đặt biến môi trường thì các lệnh `code`, `search`, `chapter`, `gri`,
`refs` đọc thẳng kho Tra cứu HS của ILMSv2 (cùng dữ liệu nhân viên thấy
trên tab "Tra cứu HS"), và `add_reference.py` gửi văn bản mới vào kho ấy
thay vì lưu tệp trên máy:

```powershell
$env:ILMS_URL  = "https://truelogistics.up.railway.app"
$env:ILMS_USER = "tai_khoan_ilms"      # hoặc $env:ILMS_TOKEN = "<token>"
$env:ILMS_PASS = "mat_khau"
python scripts/query_hs.py code 72287010
python scripts/query_hs.py refs "thep can nong" --category cbpg_pvtm
python scripts/query_hs.py vanban 3765/QĐ-BCT        # đọc toàn văn (id hoặc số hiệu)
python scripts/add_reference.py --title "..." --so-hieu "123/QĐ-BCT" --category cbpg_pvtm --ngay 2026-09-30 --file vb.txt
```

Thêm văn bản cần tài khoản có quyền `tracuu.manage` (MANAGER, ACCOUNTANT,
DOCS). `heading` và `case` vẫn đọc tệp trên máy vì ILMS chưa có hai loại
dữ liệu này. Không đặt `ILMS_URL` thì mọi lệnh chạy trên tệp máy như cũ.

## Tra cứu thuế phòng vệ thương mại (CBPG, chống lẩn tránh)

Cần `ILMS_URL`. Dữ liệu và luật tính nằm ở kho ILMSv2 — skill chỉ đọc, không tự tính:

```bash
python scripts/query_hs.py cbpg "LX International"        # tìm theo tên hàng, mã HS, nhà SX, công ty TM, mác thép, tiêu chuẩn, số QĐ
python scripts/query_hs.py cbpg "DX57D+Z" --kieu mac_thep
python scripts/query_hs.py vu AD19                          # hồ sơ đủ: mô tả, quy cách, mã HS, mức thuế từng nhà SX, loại trừ
python scripts/query_hs.py thue 7210.49.11 --nuoc KR --nsx "Hyundai Steel" --nxk "LX International"
python scripts/query_hs.py thue 7210.49.11 --nuoc CN --mac DX57D+Z --tc "EN 10346:2024"
```

- Lệnh `code <mã>` tự báo **"ĐANG BỊ ÁP THUẾ PHÒNG VỆ THƯƠNG MẠI"** khi mã thuộc vụ đang áp.
- Khi phân loại một mã có dấu hiệu CBPG, luôn chạy `thue` với đủ nước C/O, nhà SX, nhà XK (và mác thép + tiêu chuẩn với hàng thép) rồi trích **từng bước và căn cứ** máy trả về.
- Vụ ghi "CHƯA ĐỐI CHIẾU BẢN GIẤY": nói rõ với người dùng rằng số liệu cần đối chiếu QĐ gốc trước khi khai.
- Không nộp C/O, không có giấy chứng nhận nhà SX, hay nhà XK không cùng hàng ngang với nhà SX đều rơi về mức cao hơn — nêu rõ điều này khi tư vấn.

## Đồng bộ với ILMSv2 (ILMS là nguồn chính)

- **Dữ liệu:** có `ILMS_URL` thì mọi lệnh tra (`code`, `search`, `refs`, `vanban`, `cbpg`, `vu`, `thue`) đọc thẳng
  kho ILMSv2 — cùng số liệu nhân viên thấy trên app. Thêm văn bản bằng `add_reference.py` hay nút "+ Văn bản"
  trên app đều vào CÙNG một kho.
- **Bản sao trên máy** (để tra khi mất mạng): `python scripts/query_hs.py dongbo` — kéo mọi văn bản ILMS về
  `references/`, đẩy văn bản chỉ có trên máy (có dòng `[Số hiệu]`) lên ILMS. `--chi-keo` để chỉ kéo về.
- Tra cứu phòng vệ thương mại (`cbpg`, `vu`, `thue`) luôn đọc trực tiếp ILMS, không có bản sao — mức thuế phải là số hiện hành.
- **Ưu tiên:** Ecustoms là skill tra cứu HS / CBPG CHÍNH. Chỉ dùng skill khác khi người dùng gọi đích danh.
