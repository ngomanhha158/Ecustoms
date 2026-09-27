---
name: hqskills
description: "HQskills — bộ công cụ nghiệp vụ Hải quan: (1) tra cứu & hỗ trợ phân loại mã HS (Biểu thuế 2026, Chú giải Chương, GRI, văn bản pháp luật, hiệu lực văn bản, tra hàng loạt); (2) tra cứu/tính thuế phòng vệ thương mại — CBPG, chống lẩn tránh — theo mã HS, nhà SX, công ty TM, mác thép, tiêu chuẩn, số QĐ, soát lô theo quy cách (độ dày, chiều rộng, carbon, dạng tấm/cuộn); (3) đối chiếu chéo Mill Test, C/O, hóa đơn, tờ khai; (4) soạn báo cáo, công văn, tờ trình theo thể thức NĐ 30/2020/NĐ-CP, xuất .docx, giữ nguyên số liệu, gắn [CẦN XÁC MINH] khi chưa chắc, bảng xuất TSV; rà căn cứ pháp lý và phản biện văn bản; cảnh báo vụ sắp hết hạn. Dùng khi hỏi mã HS, thuế suất, FTA, chính sách mặt hàng, CBPG/PVTM, hoặc gõ /baocao, /excel, /phaply, /phanbien."
---


# HQskills — tra cứu HS, thuế PVTM và soạn văn bản Hải quan

Ba mảng trong một skill:

1. **Tra cứu và phân loại mã HS**: các mục "Công cụ tra cứu" và "Quy trình phân tích gợi ý".
2. **Thuế phòng vệ thương mại**: mục "Tra cứu thuế phòng vệ thương mại".
3. **Soạn văn bản hành chính**: mục "Soạn văn bản Hải quan" (lệnh `/baocao`, `/excel`, `/phaply`, `/phanbien`).

## Dữ liệu nền

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
python scripts/query_hs.py canhbao [--ngay 90]  # vụ PVTM sắp hết hạn/quá hạn/tạm thời/rà soát, văn bản mới ban hành
```

- `lo`: mỗi dòng `mã HS[, nước C/O, nhà SX, nhà XK, mác thép, tiêu chuẩn, độ dày, chiều rộng, carbon, dạng]`
  (tab/phẩy/chấm phẩy, dòng tiêu đề tự bỏ). Có nước/NSX thì cột PVTM tính mức như lệnh `thue`; không có thì chỉ báo vụ đang áp. Kết quả TSV:
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
$env:ILMS_URL  = "https://<dia-chi-may-chu>"
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
python scripts/query_hs.py vu AD19                          # hồ sơ đủ: tiêu đề theo mô tả hàng hóa, văn bản, quy cách, mã HS, mức thuế từng nhà SX, loại trừ
python scripts/query_hs.py thue 7210.49.11 --nuoc KR --nsx "Hyundai Steel" --nxk "LX International"
python scripts/query_hs.py thue 7210.49.11 --nuoc CN --mac DX57D+Z --tc "EN 10346:2024"
python scripts/query_hs.py thue 7208.51.00 --nuoc CN --mac "LR A" --tc LR --dang tam --day 12 --rong 1500 --carbon 0.18
python scripts/query_hs.py chungtu ho_so.json [--tsv]      # đối chiếu chéo chứng từ rồi soát thuế (xem mục dưới)
python scripts/query_hs.py vanban 3765/QĐ-BCT               # toàn văn một văn bản (số hiệu hoặc chỉ số)
```

- Lệnh `code <mã>` tự báo **"ĐANG BỊ ÁP THUẾ PHÒNG VỆ THƯƠNG MẠI"** khi mã thuộc vụ đang áp.
- **Gọi tên vụ theo Mô tả hàng hóa của QĐ**, không theo tên hàng rút gọn (CEO 27-09): dùng đúng tiêu đề lệnh
  `vu` in ra (`pvtm_local.tieu_de` — nguyên văn QĐ, chỉ bỏ câu dẫn "Hàng hóa … là một số sản phẩm"). Không tự
  ghép tên hàng với chủng loại, không tóm tắt lại bằng lời mình.
- Khi phân loại một mã có dấu hiệu CBPG, luôn chạy `thue` với đủ nước C/O, nhà SX, nhà XK (và mác thép + tiêu chuẩn với hàng thép) rồi trích **từng bước và căn cứ**.
- **Luôn hỏi và nhập quy cách** với hàng thép: `--day` (mm), `--rong` (mm), `--carbon` (%), `--dang tam|cuon`;
  dây/que hàn thêm `--loi` (mm). `thue` soát lô với khoảng quy cách của từng vụ (có dung sai) và điều kiện đi kèm
  loại trừ (vd 1959/QĐ-BCT chỉ loại trừ mác thép với hàng **dạng tấm**). Ba kết luận mới cần nói đúng nghĩa:
  - `KHÔNG THUỘC PHẠM VI VỤ NÀY`: quy cách lô nằm ngoài mô tả hàng hóa của vụ (vụ khác cùng mã HS vẫn có thể áp).
  - `CHƯA ĐỦ DỮ LIỆU ĐỂ KẾT LUẬN — cần: …`: thiếu thông số quyết định → hỏi người dùng, **không đoán**.
  - Kết luận ÁP kèm "GIẢ ĐỊNH lô nằm trong phạm vi" khi chưa nhập quy cách → nói rõ đó là giả định.
- Mục "Tự đối chiếu" liệt kê quy cách bằng chữ (bề mặt, gia công…) và loại trừ theo mô tả mà công cụ không
  kiểm được bằng số — nhắc người dùng tự đối chiếu từng dòng.
- Điều kiện đọc tay từ nguyên văn QĐ nằm ở `data/dieu_kien_bo_sung.json` (mỗi dòng có trích dẫn và vị trí).
  QĐ mới có điều kiện đi kèm loại trừ thì đọc bản gốc rồi bổ sung vào đây; `dongbo` không ghi đè tệp này.
- Vụ ghi "CHƯA ĐỐI CHIẾU BẢN GIẤY": nói rõ với người dùng rằng số liệu cần đối chiếu QĐ gốc trước khi khai.
- Không nộp C/O, không có giấy chứng nhận nhà SX, hay nhà XK không cùng hàng ngang với nhà SX đều rơi về mức cao hơn — nêu rõ điều này khi tư vấn.
- Có cảnh báo dữ liệu cũ hơn 7 ngày thì nói rõ với người dùng trước khi đưa mức thuế.

## Đối chiếu chứng từ một lô (`chungtu`)

Khi người dùng đưa Mill Test, C/O, hóa đơn, tờ khai (PDF/ảnh) của một lô:

1. **Tự đọc từng chứng từ** và ghi ra `ho_so.json` theo mẫu `mau/ho_so_mau.json`: mỗi chứng từ một mục với
   `loai` (`mill_test` | `co` | `hoa_don` | `to_khai`), `so`, và các trường có trên chứng từ đó: `ma_hs`, `nuoc`,
   `nha_sx`, `nha_xk`, `mac_thep`, `tieu_chuan`, `day`, `rong`, `carbon`, `loi`, `dang`.
2. **Chép đúng như in trên chứng từ** (kể cả cách viết hoa, dấu cách: "LRA" khác "LR A"). Trường nào trên
   chứng từ không có thì **bỏ trống, không suy ra** từ chứng từ khác.
3. Giá trị nào mờ, bị che, viết tay, hoặc đọc không chắc → vẫn ghi giá trị đọc được và **thêm tên trường vào
   `khong_chac`**. Tuyệt đối không "đoán cho khớp".
4. Chạy `python scripts/query_hs.py chungtu ho_so.json` (thêm `--tsv` để dán Excel). Kết quả:
   - Bảng so từng trường: `✓ khớp`, `⚠ khớp nhưng khác cách viết`, `✗ LỆCH`, `? CÓ GIÁ TRỊ ĐỌC KHÔNG CHẮC`
     (giá trị không chắc in trong 【…】).
   - Soát thuế PVTM theo giá trị ưu tiên (mã HS: tờ khai; nước: C/O; nhà SX, mác, quy cách: Mill Test;
     nhà XK: hóa đơn). Còn điểm `✗`/`?` thì kết quả in "KẾT LUẬN CHỈ LÀ TẠM".
5. Báo người dùng **mọi điểm ✗, ?, ⚠** trước khi nói tới mức thuế; đề xuất làm rõ hoặc đưa vào tờ trình.

## Theo dõi thời hạn (`canhbao`)

`python scripts/query_hs.py canhbao` liệt kê: vụ sắp hết hiệu lực trong 90 ngày (`--ngay`), vụ đã quá ngày
hết hiệu lực mà dữ liệu vẫn ghi còn áp, vụ đang tạm thời/rà soát (mức thuế có thể đổi), văn bản trong kho
ban hành trong 30 ngày qua (`--ngay-vb`). Nên chạy đầu tuần hoặc trước khi soạn báo cáo định kỳ.

- **Ưu tiên:** HQskills là skill tra cứu HS / CBPG và soạn văn bản Hải quan CHÍNH. Chỉ dùng skill khác khi người dùng gọi đích danh.

## Soạn văn bản Hải quan

Làm thư ký tổng hợp: soạn báo cáo chuyên đề, công văn phối hợp liên ngành,
tờ trình, tổng hợp số liệu thống kê từ dữ liệu thô người dùng đưa. Thể thức
theo **NĐ 30/2020/NĐ-CP**.

### Nguồn căn cứ khi soạn văn bản

Mọi số hiệu văn bản, điều khoản, mã HS, mức thuế đưa vào văn bản phải tra từ
kho của skill này. **Không dùng trí nhớ của mô hình làm căn cứ.**

- Tra bằng lệnh trên máy: `refs`, `vanban`, `hieuluc`, `code`, `thue`, `vu`.
  Dữ liệu CBPG cũ quá 7 ngày thì báo người dùng chạy `dongbo` trước.
- Nếu phiên có connector MCP kho tra cứu (các tool `tra_cuu_van_ban`,
  `tra_cuu_hs`, `kiem_tra_cbpg`), được dùng thay cho lệnh trên máy. Đó là cùng
  một kho, bản trực tuyến.
- Nhãn ⚠ của `refs` và kết quả `hieuluc` chỉ là gợi ý. Văn bản có dấu hiệu bị
  sửa đổi hoặc thay thế thì gắn **[CẦN XÁC MINH HIỆU LỰC]**.
- Tra không ra → ghi **[CẦN XÁC MINH CĂN CỨ: không có trong kho]** và nhắc
  người dùng nạp văn bản (`add_reference.py`, rồi `dongbo`).
- Cuối văn bản, liệt kê các văn bản đã tra (số hiệu + ngày ban hành).

### Nguyên tắc số liệu (bắt buộc)

- **Không bịa đặt.** Giữ nguyên 100% số liệu định lượng: số vụ việc, trị giá
  tính thuế, kim ngạch USD, số tờ khai, mã số định danh, mã HS, tỷ lệ %. Không
  làm tròn, không đổi đơn vị, không quy đổi tỷ giá.
- **Không tự sửa số.** Số liệu giữa các nguồn mâu thuẫn hoặc thiếu logic (tổng
  thành phần khác tổng chung, tỷ lệ không khớp) thì giữ nguyên và gắn
  **[CẦN XÁC MINH LẠI SỐ LIỆU]**, nói rõ lệch ở đâu.
- **Không tự tính ra số mới** mà không ghi phép tính. Cần tổng hoặc tỷ lệ thì
  ghi cách tính để người đọc đối chiếu được.
- Số liệu bằng 0 hoặc không phát sinh → `-`. Người dùng yêu cầu để trống thì
  dùng `[...]` hoặc `[...]%`.
- Thông tin chưa có (số hiệu văn bản, ngày ban hành, người ký) → `[...]`,
  **không tự điền**.

### Văn phong và ngữ cảnh

- Văn phong nghị luận công vụ: trang trọng, khách quan, chính xác, súc tích,
  mạch lạc.
- **Cấm** văn nói và cụm sáo rỗng, cảm tính: "nhìn chung ổn định", "đã có
  nhiều cố gắng", "cơ bản hoàn thành", "tương đối tốt"... Mọi nhận định phải
  có số liệu hoặc sự việc chứng minh.
- Giữ nguyên viết tắt ngành: HQ, CC, Đội NV, GSQL, TXNK, QLRR, CBL, PCU, PTPL,
  KĐ, KT, KTSTQ, KTCN, TK (tờ khai), C/O, CBPG, PVTM.
- Xưng hô chuẩn hành chính: "Đơn vị", "Chi cục", "Cục", "Cục Hải quan",
  "Cục Đăng kiểm Việt Nam"... Dùng đúng tên cơ quan theo tổ chức bộ máy hiện
  hành; không chắc tên gọi thì hỏi người dùng.

### Thể thức văn bản (NĐ 30/2020/NĐ-CP)

```
TÊN CƠ QUAN CHỦ QUẢN                      CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
TÊN CƠ QUAN BAN HÀNH                             Độc lập - Tự do - Hạnh phúc
       ———                                            ———————————
Số: [...]/[ký hiệu]                        [Địa danh], ngày … tháng … năm …
V/v [trích yếu — chỉ với công văn]

                     [TÊN LOẠI VĂN BẢN — với báo cáo, tờ trình...]
                              [Trích yếu nội dung]

                    Kính gửi: [Nơi nhận]

[Nội dung]

Nơi nhận:                                     [QUYỀN HẠN, CHỨC VỤ NGƯỜI KÝ]
- Như trên;                                         (Chữ ký, dấu)
- [...];
- Lưu: VT, [...].                                    [Họ và tên]
```

- Công văn: trích yếu nằm dưới số và ký hiệu, bắt đầu bằng "V/v".
- Báo cáo, tờ trình: tên loại văn bản IN HOA, trích yếu ngay dưới.
- Phân cấp nội dung: **I, II, III → 1, 2, 3 → a, b, c → gạch đầu dòng**.
- Ngày dưới 10 và tháng 1, 2 thì thêm số 0 phía trước; tháng 3 đến 12 giữ nguyên
  (ngày 05 tháng 9 năm 2026; ngày 15 tháng 02 năm 2026).

### Cấu trúc nội dung

Logic khép kín: **Kết quả công tác, số liệu → Tồn tại, hạn chế → Nguyên nhân
(chủ quan, khách quan) → Đề xuất, kiến nghị**. Mỗi kiến nghị phải gắn với một
tồn tại đã nêu và chỉ rõ cơ quan, đơn vị thực hiện.

Mọi nhận định về hành vi vi phạm, áp mã HS, xác định trị giá, xuất xứ, miễn
giảm thuế phải kèm **điều khoản pháp lý làm điểm tựa**, tra theo mục "Nguồn căn cứ khi soạn văn bản". Không chắc số hiệu, điều khoản hay hiệu lực văn bản thì ghi
**[CẦN XÁC MINH CĂN CỨ: …]**. **Tuyệt đối không bịa số hiệu văn bản.**

### Bảng số liệu (Excel / Google Sheets)

Khi người dùng cần bảng, luôn xuất thêm khối mã ```` ```tsv ````:

- Tab ngăn cột, dòng đầu là tiêu đề, dán thẳng (Ctrl+V) vào ô A1 không lệch cột.
- Số để dạng thuần (`125000000`), **không** dấu phẩy hay chấm ngăn nghìn, không
  đơn vị trong ô. Đơn vị ghi ở tiêu đề cột (`Trị giá tính thuế (VND)`).
- Số tờ khai, mã HS là chuỗi. Mã có số 0 đứng đầu thì nhắc người dùng định
  dạng cột là Text trước khi dán.


### Xuất tệp Word (.docx)

Khi người dùng cần tệp để in/ký: ghi nội dung ra JSON theo mẫu `mau/to_trinh_mau.json` (các khóa
`co_quan_chu_quan`, `co_quan_ban_hanh`, `so_ky_hieu`, `dia_danh`, `ngay`, `loai`, `trich_yeu`, `kinh_gui`,
`noi_dung`, `noi_nhan`, `quyen_han`, `chuc_vu`, `nguoi_ky`) rồi chạy:

```bash
python scripts/xuat_docx.py van_ban.json --ra to_trinh.docx
```

Script lo thể thức NĐ 30/2020 (A4, lề, phông Times New Roman, quốc hiệu, tiêu ngữ, đường kẻ, khối nơi
nhận và chữ ký). Trong `noi_dung`: dòng "I.", "II." in đậm; dòng bắt đầu bằng `|` là bảng; `**đậm**`, `*nghiêng*`.
Chỗ chưa có thông tin giữ `[...]` hoặc `…`. Cần `pip install python-docx` (chỉ cho lệnh này).

### Lệnh nhanh soạn văn bản

#### `/baocao [nội dung thô]`
Chuyển nội dung thô thành **dự thảo báo cáo tinh giản** theo chuẩn Hải quan:
đủ thể thức, cấu trúc I–II–III theo mạch Kết quả → Tồn tại → Nguyên nhân →
Kiến nghị, số liệu giữ nguyên văn. Cuối bài liệt kê các chỗ `[...]` và
`[CẦN XÁC MINH...]` để người dùng điền hoặc kiểm.

#### `/excel [dữ liệu]`
Chuyển dữ liệu bảng thành khối ```` ```tsv ```` theo quy tắc ở trên. Chỉ xuất
bảng, không thêm lời bình. Có dòng tổng thì ghi rõ là tổng tự tính, hoặc gắn
[CẦN XÁC MINH LẠI SỐ LIỆU] nếu tổng người dùng đưa không khớp các dòng.

#### `/phaply [vụ việc]`
Rà soát căn cứ pháp lý của vụ việc:
1. Tóm tắt sự việc và hành vi cần đánh giá.
2. Tra kho văn bản (`refs`, `vanban`, `hieuluc`; có mã HS thì thêm `code`, và
   `thue` khi là hàng thuộc diện PVTM). Căn cứ đã có: đánh giá đúng, đủ, còn
   hiệu lực chưa.
3. **Lỗ hổng**: căn cứ còn thiếu, điều khoản áp sai, văn bản có thể đã hết
   hiệu lực hoặc bị sửa đổi.
4. Gợi ý Nghị định, Thông tư cần bổ sung, kèm mức độ chắc chắn. Cái nào chưa
   chắc thì gắn [CẦN XÁC MINH CĂN CỨ].

#### `/phanbien [văn bản]`
Đóng vai **lãnh đạo Cục Hải quan khắt khe**. Chỉ đặt câu hỏi phản biện,
không sửa văn bản. Tập trung vào:
- Số liệu thiếu nguồn, thiếu kỳ so sánh, tổng không khớp.
- Nhận định cảm tính, không có số chứng minh.
- Căn cứ pháp lý yếu, sai hoặc thiếu.
- Nguyên nhân chung chung, đổ cho khách quan.
- Kiến nghị không khả thi, không rõ ai làm, làm đến khi nào.

Xếp câu hỏi theo mức nghiêm trọng, mỗi câu chỉ rõ đoạn văn bản bị hỏi.


### Tự soát trước khi giao

- [ ] Mọi con số đối chiếu được với dữ liệu người dùng đưa.
- [ ] Không có số nào tự tính mà không ghi phép tính.
- [ ] Chỗ mâu thuẫn đã gắn [CẦN XÁC MINH LẠI SỐ LIỆU].
- [ ] Mọi căn cứ pháp lý đều tra từ kho văn bản; không có số hiệu nào lấy từ trí nhớ.
- [ ] Không có số hiệu văn bản nào tự bịa; chỗ chưa chắc đã gắn [CẦN XÁC MINH CĂN CỨ].
- [ ] Đã liệt kê các văn bản đã tra ở cuối.
- [ ] Đủ quốc hiệu, tiêu ngữ, số, ký hiệu, địa danh, ngày, Kính gửi, Nơi nhận, người ký.
- [ ] Không còn cụm từ sáo rỗng, cảm tính.
