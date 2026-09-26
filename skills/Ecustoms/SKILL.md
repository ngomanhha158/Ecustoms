---
name: "Ecustoms"
description: "Tra cứu & hỗ trợ phân loại mã HS (Biểu thuế 2026, Chú giải Chương, GRI, văn bản pháp luật) và tra cứu/tính thuế PHÒNG VỆ THƯƠNG MẠI — chống bán phá giá (CBPG), chống lẩn tránh — theo mã HS, tên hàng, nhà sản xuất, công ty thương mại, mác thép, tiêu chuẩn, số QĐ. Chạy độc lập trên máy; ILMSv2 chỉ để đồng bộ dữ liệu (`dongbo`). Dùng khi hỏi mã HS, thuế suất, FTA, chính sách mặt hàng, CBPG/PVTM."
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
python scripts/query_hs.py search "<từ khóa>" [--chuong 72] [--n 30]  # tìm theo từ, không dấu, thứ tự tùy ý; xếp hạng, gom theo nhóm
python scripts/query_hs.py chapter <số chương>  # Chú giải pháp lý theo Chương
python scripts/query_hs.py heading <4 số>       # Chú giải chi tiết nhóm 4 số
python scripts/query_hs.py gri [số quy tắc]     # toàn văn 6 quy tắc GRI
python scripts/query_hs.py refs "<từ khóa>"     # tra văn bản pháp luật đã thêm (mọi danh mục)
python scripts/query_hs.py refs "<từ khóa>" --category chinh_sach_phap_luat  # chỉ tra NĐ/TT
python scripts/query_hs.py refs "<từ khóa>" --category cbpg_pvtm             # chỉ tra QĐ CBPG/PVTM
python scripts/query_hs.py refs --nam 2026 --co-quan BCT   # liệt kê văn bản lọc theo năm/cơ quan, kèm nhãn ⚠ hiệu lực
python scripts/query_hs.py hieuluc 13/2015/TT-BTC  # văn bản nào trong kho sửa đổi/thay thế/bãi bỏ văn bản này
python scripts/query_hs.py hieuluc                 # mọi văn bản trong kho đã bị văn bản khác tác động
python scripts/query_hs.py lo ds_ma.csv --fta acfta,evfta [--ra ket_qua.tsv]  # tra hàng loạt, xuất TSV dán Excel
python scripts/query_hs.py case "<từ khóa>"     # tra tiền lệ/case đã tự ghi lại
```

- `lo`: mỗi dòng `mã HS[, nước C/O, nhà SX, nhà XK, mác thép, tiêu chuẩn]` (tab/phẩy/chấm phẩy, dòng tiêu đề
  tự bỏ). Có nước/NSX thì cột PVTM tính mức như lệnh `thue`; không có thì chỉ báo vụ đang áp. Kết quả TSV:
  đưa người dùng trong khung ```tsv để dán vào ô A1.
- `hieuluc` và nhãn ⚠ của `refs` là dò TỰ ĐỘNG theo câu chữ ("thay thế", "bãi bỏ", "sửa đổi, bổ sung") và thứ
  bậc văn bản, chỉ trong kho trên máy. Luôn nói rõ là gợi ý; không thấy văn bản sửa đổi KHÔNG có nghĩa là còn
  hiệu lực — trích dẫn làm căn cứ phải đối chiếu nguồn chính thức.

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
