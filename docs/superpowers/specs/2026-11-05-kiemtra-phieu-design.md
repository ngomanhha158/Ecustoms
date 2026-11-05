# Lệnh `kiemtra` — phiếu kiểm tra nhanh một dòng hàng (thép Chương 72)

Ngày: 05-11-2026 · Trạng thái: CEO duyệt mẫu (phương án A, bản sửa 2) · Mẫu: artifact "Phiếu tra cứu dòng hàng".

## 1. Mục tiêu

Một lệnh nhận NGUYÊN dòng hàng trên tờ khai, in ra phiếu mà kiểm hóa viên / DOCS nhìn 5 giây là biết:
mã HS có phù hợp không, thuế NK, CBPG có áp không, cần xem tận mắt những gì, mã nghi ngờ tương tự.

Thay cho việc chạy tay 4–5 lệnh (`code`, `chapter`, liệt kê mã con, `thue`) rồi tự viết bảng kết luận.

Phạm vi bản 1: **thép Chương 72** (sắt/thép không hợp kim, thép hợp kim khác). Chương khác: lệnh vẫn chạy
phần mã HS + thuế + CBPG, bỏ các mục chỉ thép mới có (soát hợp kim, mã nghi ngờ) và nói rõ là bỏ.

## 2. Cách dùng

```bash
python scripts/query_hs.py kiemtra --ma 72254090 --nuoc CN \
  --mo-ta "Thép tấm hợp kim crom được cán phẳng, chưa được gia công quá mức cán nóng, chứa C=0.07%->0.09% Cr=0.49%->0.52%, KT: 40x2440x5729mm, TC: ASTM A709-2024, Mác: A709Gr50W. Mới 100%" \
  [--thue-suat 0] [--tk 108782254600 --dong 01] [--luong 2] [--nsx ...] [--nxk ...] [--html phieu.html]
```

- `--mo-ta` dán nguyên ô "Mô tả hàng hóa" của ECUS. Các thông số đọc được từ mô tả có thể ghi đè bằng cờ riêng
  (`--day --rong --carbon --dang --mac --tc`, cùng tên với lệnh `thue`).
- Mặc định in chữ ra màn hình. `--html <tệp>` ghi trang in 1 tờ A4 theo mẫu đã duyệt.

## 3. Thành phần (mỗi tệp một việc)

| Tệp | Việc | Phụ thuộc |
|---|---|---|
| `scripts/doc_dong_hang.py` | Đọc mô tả ECUS → `{day, rong, dai, carbon:(min,max), nguyen_to:{Cr:(min,max),…}, mac, tc, dang, gia_cong}`; ghi rõ trường nào đọc được, trường nào không | không |
| `scripts/hop_kim.py` | Ngưỡng Chú giải 1(f) Chương 72 (bảng 15 nguyên tố + "nguyên tố khác 0,1%") → `la_hop_kim(nguyen_to)` trả kết luận + nguyên tố quyết định + khoảng cách tới ngưỡng | không |
| `scripts/cap_nghi_ngo.py` | Bảng ghép cặp nhóm không hợp kim ↔ hợp kim theo hình dạng/gia công; chọn mã 8 số đối ứng theo tiêu chí dòng hàng; **mọi mã đều tra lại `hs_tree.json`, không có thì không in** | `hs_tree.json` |
| `scripts/phieu.py` | Gom kết quả → dict phiếu (4 ô tín hiệu, danh sách kiểm tận mắt, lập luận, bảng mã nghi ngờ, bảng phạm vi CBPG, nguồn dữ liệu) | 3 tệp trên + `pvtm_local.tinh_cho_lo` |
| `scripts/in_phieu.py` | Dict phiếu → chữ màn hình / HTML A4 | `phieu.py` |
| `query_hs.py` | Thêm lệnh con `kiemtra` (chỉ nối, không chứa luật) | — |

### Bảng ghép cặp (bản 1)

| Không hợp kim | Hợp kim khác | Hình dạng / gia công |
|---|---|---|
| 7208 | 7225.30 (cuộn), 7225.40 (không cuộn) | cán phẳng ≥ 600 mm, cán nóng |
| 7209 | 7225.50 | cán phẳng ≥ 600 mm, cán nguội |
| 7210 | 7225.91 / 7225.92 / 7225.99 | cán phẳng ≥ 600 mm, phủ/mạ/tráng |
| 7211 | 7226.91 / 7226.92 / 7226.99 | cán phẳng < 600 mm, chưa phủ |
| 7212 | 7226.99 | cán phẳng < 600 mm, phủ/mạ/tráng |
| 7213 | 7227 | thanh/que cán nóng dạng cuộn |
| 7214 | 7228.30 | thanh/que khác, cán nóng |
| 7216 | 7228.70 | thép hình |

Chọn mã 8 số đối ứng: lọc mã con trong nhóm đối ứng theo đúng tiêu chí đọc được của dòng hàng (cuộn/không cuộn,
dải độ dày trong mô tả mã, đã/chưa phủ). Còn ≥ 2 mã khớp thì in tất cả kèm tiêu chí phân biệt; không khớp mã nào
thì in mã 6 số + "cần xác định thêm", không ghép đuôi.

## 4. Nội dung phiếu (theo mẫu duyệt)

1. **Đầu phiếu:** tên hàng rút gọn từ mô tả, TK/dòng, nước, luồng.
2. **4 ô tín hiệu:**
   - *Mã HS*: `ĐÚNG` (xanh) chỉ khi mọi tiêu chí máy soát được đều khớp (hợp kim/không hợp kim theo 1(f), chiều
     rộng ≥/< 600 mm, cuộn/không cuộn, dải độ dày trong mô tả mã, đã/chưa phủ). Lệch một tiêu chí → `CẦN XEM LẠI`
     (đỏ) + tiêu chí lệch. Thiếu dữ liệu quyết định → `CHƯA ĐỦ` (vàng). Dưới ô luôn ghi "theo tiêu chí máy soát được".
   - *Thuế NK*: thuế suất MFN (+ FTA của nước xuất xứ nếu có); so với `--thue-suat` khai → "khớp TK" / "LỆCH".
   - *CBPG/PVTM*: đúng kết luận của `tinh_cho_lo` (Bị áp x% / Không áp / Ngoài phạm vi / Chưa đủ dữ liệu).
   - *Cần làm rõ*: số điểm cần người xem (thông số không đọc được, mã HS lệch, thuế suất lệch, kết luận CBPG giả định).
3. **Kiểm hóa cần xem tận mắt:** sinh từ các ngưỡng thật đã dùng để kết luận — mỗi dòng: thông số, ngưỡng làm đổi
   kết luận, giá trị khai. Ví dụ: "Đo chiều rộng: phải trên 2.300 mm thì nằm ngoài phạm vi chống bán phá giá — khai 2440 mm".
4. **Vì sao mã này:** 2–4 dòng lập luận (1(f) → nhóm → phân nhóm → mã 8 số), mỗi dòng nêu căn cứ.
5. **Mã nghi ngờ tương tự:** mã đang khai + mã đối ứng (hợp kim ↔ không hợp kim), mỗi mã: mô tả, điều kiện rơi vào,
   thuế NK, CBPG (chạy `tinh_cho_lo` cho chính lô với mã đó). Một dòng nhắc chứng từ quyết định (Mill Test) và
   khoảng cách tới ngưỡng ("cao hơn ngưỡng 0,3% là 0,19 điểm %"). Hai mã khác thuế suất hoặc khác kết luận CBPG
   thì nói rõ chênh lệch.
6. **Đối chiếu phạm vi CBPG:** bảng vụ × (độ dày, chiều rộng, carbon, …) với chip ✓/✗ — lấy từ các bước "Phạm vi"
   của `tinh_cho_lo`.
7. **Chân phiếu:** ngày đồng bộ dữ liệu CBPG, Biểu thuế 2026, Chú giải Chương 72, trạng thái so luật với ILMS.

## 5. Xử lý thiếu / lỗi

- Thông số không đọc được từ mô tả → không đoán; ghi vào "Cần làm rõ" và mục tận mắt.
- Khoảng giá trị (Cr 0,49–0,52) → so CẢ hai đầu: hai đầu cùng phía ngưỡng thì kết luận; vắt qua ngưỡng →
  `CHƯA ĐỦ` + "Mill Test quyết định".
- Mã không có trong Biểu thuế → dừng, in các mã con thật cùng tiền tố (như lệnh `code`).
- Dữ liệu CBPG cũ hơn 7 ngày → cảnh báo đầu phiếu (giữ luật hiện có).
- Phiếu là công cụ hỗ trợ: chân phiếu ghi "Kết quả soát tự động — đối chiếu chứng từ gốc trước khi kết luận".

## 6. Kiểm thử

- `tests/test_kiemtra.py`: đọc mô tả (dòng A709 mẫu + 5 cách viết ECUS khác: `40*2440*5729`, `T40 x W2440`,
  `Cr:0.5%`, `0,49-0,52%`, thiếu kích thước); 1(f) (dưới/đúng/trên ngưỡng, khoảng vắt ngưỡng, Bo 0,0008%);
  ghép cặp (7225.40.90 ↔ 7208.51.00; 7208.39.90 dày 3 mm cuộn ↔ 7225.30.90; mã đối ứng không tồn tại → mã 6 số);
  phiếu đầy đủ cho dòng A709 khớp nội dung mẫu đã duyệt (4 ô, 4 dòng tận mắt, 2 mã nghi ngờ, 2 vụ CBPG ngoài phạm vi).
- Không cần mạng; chạy cùng bộ `python -m unittest discover -s tests`.

## 7. Ngoài phạm vi bản 1

Cặp nghi ngờ cho chương khác (nhôm 76, đồng 74…); đọc trực tiếp tệp ECUS/ảnh chụp màn hình; xuất Word.

## 8. Đưa vào ILMSv2 (CEO 05-11: "thêm chức năng này cho ILMS v2 luôn")

**Một luật một chỗ:** luật nằm ở ILMS, skill chép nguyên văn (như luật PVTM).

### 8.1 Luật thuần — ILMS `backend/app/services/kiem_tra_dong.py` (không chạm CSDL)

Gộp 4 thành phần §3 (`doc_dong_hang`, `la_hop_kim`, `cap_nghi_ngo`, `lap_phieu`) vào MỘT tệp luật thuần.
Dữ liệu biểu thuế đưa vào qua hai hàm do nơi gọi cấp — nên cùng một tệp chạy được ở cả hai đầu:

- `tra_ma(code) -> {code, desc_vn, desc_en, mfn, fta, ...} | None`
- `ma_con(tien_to) -> [ma 8 so]`
- kết quả PVTM truyền vào sẵn (ILMS: `pvtm_kho.tinh_cho_lo`; skill: `pvtm_local.tinh_cho_lo`).

ILMS: hai hàm đọc bảng `hs_codes`. Skill: đọc `data/hs_tree.json`; `chep_luat_ilms.py` chép thêm tệp này
(nguyên văn, chỉ thay import) — `kiem_khop.py` thêm phần so phiếu máy ↔ ILMS cho các dòng hàng mẫu.

### 8.2 API (trình duyệt — không đổi lược đồ CSDL)

| Phương thức | Đường dẫn | Quyền | Việc |
|---|---|---|---|
| POST | `/api/tracuu/kiem-tra` | `tracuu.view` | Body `{ma, mo_ta, nuoc?, thue_suat?, tk?, dong?, luong?, nsx?, nxk?, day?, rong?, carbon?, dang?, mac?, tc?}` → JSON phiếu (§4). Không ghi gì vào CSDL. Mô tả quá dài (> 2.000 ký tự) hay mã sai dạng → 422. |

Không thêm bảng, không thêm cột. Không lưu lịch sử phiếu (bản 1).

### 8.3 Màn hình

Tab "Tra cứu HS" thêm sub-tab thứ tư **"Kiểm tra dòng hàng"** (cạnh Mã HS · Phòng vệ thương mại · Văn bản):
ô mã HS, ô nước xuất xứ, ô thuế suất khai, ô lớn dán "Mô tả hàng hóa" ECUS, nút **Kiểm tra** → phiếu đúng mẫu A
đã duyệt (4 ô tín hiệu, tận mắt, lập luận, mã nghi ngờ, phạm vi CBPG); nút **In phiếu** (in 1 tờ A4).
Mã nghi ngờ bấm được → mở hồ sơ mã đó ở sub-tab Mã HS. Mọi vai có `tracuu.view` dùng được (không có số tiền).

### 8.4 TruePilot

Tool XANH `kiem_tra_dong_hang` (chỉ đọc) gọi cùng luật — nhân viên hỏi bằng lời trong ô chat cũng ra phiếu.

### 8.5 Thứ tự làm

1. ILMS: luật thuần + test đơn vị (dòng A709 khớp mẫu) → API + e2e → màn hình (Chromium thật) → tool TruePilot.
2. Ba lượt rà (soi-hong-im-lang, /code-review, /simplify) → CEO duyệt merge → deploy.
3. Skill: `chep_luat_ilms.py` chép `kiem_tra_dong.py`; lệnh `kiemtra` + in chữ/HTML; `kiem_khop` so phiếu.
