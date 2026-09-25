# Công cụ tra cứu & phân loại HS (bản độc lập, tự xây)

Công cụ này do bạn tự xây, không sao chép nội dung nghiệp vụ của bất
kỳ skill bên thứ ba nào. Dữ liệu nền là văn bản pháp luật/Biểu thuế
công khai do Bộ Tài chính, Tổng cục Hải quan ban hành — bạn tự nhập
và tự cập nhật khi có văn bản mới (ví dụ Quyết định chống bán phá giá
thép hình chữ H).

## Cấu trúc thư mục

```
Ecustoms/
├── data/
│   ├── hs_tree.json        # Biểu thuế XNK — nhập qua import_tariff.py
│   ├── chapter_notes.json  # Chú giải pháp lý theo Chương
│   ├── heading_notes.json  # Chú giải chi tiết theo nhóm 4 số
│   ├── gri_rules.json      # 6 quy tắc GRI (đã có sẵn, văn bản công khai)
│   └── case_notes.md       # Tiền lệ/case bạn tự đúc kết theo thời gian
├── references/             # Văn bản pháp luật rời, chia theo danh mục:
│   ├── chinh_sach_phap_luat/  # Nghị định, Thông tư (chính sách nền)
│   ├── cbpg_pvtm/              # Quyết định CBPG/PVTM từng vụ việc
│   └── cong_van_huong_dan/     # Công văn hướng dẫn nghiệp vụ Hải quan/Bộ
│                            # thêm bằng add_reference.py (xem Bước 2)
└── scripts/
    ├── query_hs.py          # Công cụ tra cứu chính (dùng hằng ngày)
    ├── import_tariff.py     # Nhập/cập nhật Biểu thuế từ Excel/CSV
    └── add_reference.py     # Thêm 1 văn bản pháp luật mới
```

## Bước 1 — Nạp dữ liệu Biểu thuế lần đầu

Tải file Biểu thuế XNK hiện hành (Excel/CSV) từ nguồn chính thức
(Tổng cục Hải quan, Cổng TTĐT Bộ Tài chính, hoặc bản Thông tư đính kèm
Phụ lục). Sau đó:

```bash
pip install openpyxl
python scripts/import_tariff.py --file "BieuThue2026.xlsx" --sheet "Sheet1"
```

Script tự nhận diện các cột phổ biến (Mã HS, Mô tả, Thuế MFN, VAT,
Chính sách mặt hàng...). Nếu không nhận diện được, xem thông báo lỗi
để đổi tên cột nguồn hoặc chỉnh `COLUMN_ALIASES` trong script.

## Bước 2 — Thêm văn bản pháp luật mới (Nghị định, Thông tư, Quyết định CBPG...)

Dùng `--category` để xếp đúng loại (tự tạo thư mục nếu chưa có):
- `chinh_sach_phap_luat` — Nghị định, Thông tư áp dụng chung
- `cbpg_pvtm` — Quyết định chống bán phá giá/phòng vệ thương mại từng vụ việc
- `cong_van_huong_dan` — Công văn hướng dẫn nghiệp vụ của Hải quan/Bộ

Nếu bạn có file .txt/.md sẵn:
```bash
python scripts/add_reference.py --title "TT 26-2025-TT-BCT quy dinh chi tiet PVTM" --category chinh_sach_phap_luat --file "duong_dan\\van_ban.txt"
python scripts/add_reference.py --title "QD 1978-2025 CBPG thep hinh H" --category cbpg_pvtm --file "duong_dan\\van_ban.txt"
```

Nếu chỉ có nội dung để dán trực tiếp:
```bash
python scripts/add_reference.py --title "ND 86-2025-ND-CP PVTM" --category chinh_sach_phap_luat --paste
# rồi dán nội dung, gõ dòng "EOF" để kết thúc
```

Từ giờ có thể tra:
```bash
python scripts/query_hs.py refs "cbpg thep hinh H"                      # tra toàn bộ, mọi danh mục
python scripts/query_hs.py refs "PVTM" --category chinh_sach_phap_luat  # chỉ tra trong 1 danh mục
python scripts/query_hs.py refs                                          # xem danh sách tất cả văn bản đã có
```

## Bước 3 — Dùng hằng ngày

```bash
python scripts/query_hs.py code 72287010
python scripts/query_hs.py search "thep hinh"
python scripts/query_hs.py chapter 72
python scripts/query_hs.py heading 7228
python scripts/query_hs.py gri
python scripts/query_hs.py refs "chong ban pha gia"
python scripts/query_hs.py case "thep hinh H"
```

## Ghi lại tiền lệ của chính bạn

Mở `data/case_notes.md`, thêm mục mới theo mẫu có sẵn trong file mỗi
khi xử lý xong một case đáng nhớ (kết luận, căn cứ, bài học) — đây là
"vốn tri thức" riêng của bạn, tự do cập nhật không vướng bản quyền ai.

## Dùng như Skill trong Claude Code

Thư mục `claude-skill/` (nếu có) chứa bản đóng gói để copy vào
`~/.claude/skills/` — xem `claude-skill/SKILL.md`.

## Chạy độc lập — ILMSv2 chỉ là nơi đồng bộ dữ liệu

Mọi lệnh tra cứu (`code`, `search`, `chapter`, `heading`, `gri`, `refs`, `vanban`,
`case`, `cbpg`, `vu`, `thue`) chạy **hoàn toàn trên máy**, không cần mạng, không cần
ILMS. ILMSv2 chỉ dùng ở lệnh đồng bộ:

```powershell
$env:ILMS_URL  = "https://truelogistics.up.railway.app"
$env:ILMS_USER = "tai_khoan_ilms"      # hoặc $env:ILMS_TOKEN = "<token>"
$env:ILMS_PASS = "mat_khau"
python scripts/query_hs.py dongbo            # kéo văn bản + kho CBPG về máy, đẩy văn bản chỉ có trên máy lên
python scripts/query_hs.py dongbo --chi-keo  # chỉ kéo về
python scripts/kiem_khop.py                  # so luật tính thuế CBPG trên máy với ILMS (phải 0 lệch)
```

- `dongbo` kéo: mọi văn bản về `references/<loại>/`, mọi vụ phòng vệ thương mại (đủ hồ sơ,
  mức thuế từng nhà SX, công ty TM, loại trừ) về `data/pvtm.json`. Ghi xong mới thay tệp cũ.
- Dữ liệu CBPG cũ hơn **7 ngày** thì `cbpg`/`vu`/`thue` in cảnh báo đầu kết quả — mức thuế đổi
  theo QĐ mới, nhắc người dùng chạy `dongbo`.
- Luật tính thuế CBPG (`scripts/pvtm_local.py`) là **bản chép** luật của ILMSv2
  (`backend/app/services/pvtm.py`). ILMS đổi luật thì chép lại khối "LUẬT" rồi chạy
  `kiem_khop.py`; lệch dù một lô là chưa được dùng.
- `add_reference.py` có `ILMS_URL` thì gửi văn bản mới lên kho ILMS (cần quyền `tracuu.manage`:
  MANAGER, ACCOUNTANT, DOCS), sau đó chạy `dongbo --chi-keo` để có bản trên máy.
- Biểu thuế, Chú giải, GRI trong `data/` là dữ liệu gốc của skill (ILMS được nạp từ chính các tệp này).

## Tra cứu thuế phòng vệ thương mại (CBPG, chống lẩn tránh)

```bash
python scripts/query_hs.py cbpg "LX International"        # tìm theo tên hàng, mã HS, nhà SX, công ty TM, quy cách, mác thép, tiêu chuẩn, số QĐ
python scripts/query_hs.py cbpg "DX57D+Z" --kieu mac_thep
python scripts/query_hs.py vu AD19                          # hồ sơ đủ: văn bản, mô tả, quy cách, mã HS, mức thuế từng nhà SX, loại trừ
python scripts/query_hs.py thue 7210.49.11 --nuoc KR --nsx "Hyundai Steel" --nxk "LX International"
python scripts/query_hs.py thue 7210.49.11 --nuoc CN --mac DX57D+Z --tc "EN 10346:2024"
python scripts/query_hs.py vanban 3765/QĐ-BCT               # toàn văn một văn bản (số hiệu hoặc chỉ số)
```

- Lệnh `code <mã>` tự báo **"ĐANG BỊ ÁP THUẾ PHÒNG VỆ THƯƠNG MẠI"** khi mã thuộc vụ đang áp.
- Khi phân loại một mã có dấu hiệu CBPG, luôn chạy `thue` với đủ nước C/O, nhà SX, nhà XK (và mác thép + tiêu chuẩn với hàng thép) rồi trích **từng bước và căn cứ**.
- Vụ ghi "CHƯA ĐỐI CHIẾU BẢN GIẤY": nói rõ với người dùng rằng số liệu cần đối chiếu QĐ gốc trước khi khai.
- Không nộp C/O, không có giấy chứng nhận nhà SX, hay nhà XK không cùng hàng ngang với nhà SX đều rơi về mức cao hơn — nêu rõ điều này khi tư vấn.
- Có cảnh báo dữ liệu cũ hơn 7 ngày thì nói rõ với người dùng trước khi đưa mức thuế.

- **Ưu tiên:** Ecustoms là skill tra cứu HS / CBPG CHÍNH. Chỉ dùng skill khác khi người dùng gọi đích danh.
