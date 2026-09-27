# -*- coding: utf-8 -*-
"""Đối chiếu chéo bộ chứng từ một lô (Mill Test, C/O, hóa đơn, tờ khai) rồi soát thuế PVTM.

Claude ĐỌC chứng từ (PDF/ảnh) và ghi ra JSON; script này KHÔNG đọc ảnh, chỉ so theo luật
cố định để phần kết luận không phụ thuộc vào việc mô hình "thấy" gì:

{
  "chung_tu": [
    {"loai": "mill_test", "so": "MTC-123", "nha_sx": "…", "mac_thep": "LR A", "tieu_chuan": "LR",
     "day": 12, "rong": 1500, "carbon": 0.18, "dang": "tam", "khong_chac": ["carbon"]},
    {"loai": "co", "so": "E26…", "nuoc": "CN", "nha_sx": "…", "nha_xk": "…", "ma_hs": "7208.51"},
    {"loai": "hoa_don", "so": "INV-9", "nha_xk": "…", "mac_thep": "LRA"},
    {"loai": "to_khai", "so": "1023648796", "ma_hs": "72085100", "nuoc": "CN", "nha_xk": "…"}
  ]
}

`khong_chac`: tên các trường đọc không chắc chắn (mờ, che, viết tay) — được báo riêng và
không bao giờ bị coi là đã khớp.
"""
import pvtm_local as pl

LOAI = {"mill_test": "Mill Test", "co": "C/O", "hoa_don": "Hóa đơn", "to_khai": "Tờ khai", "khac": "Khác"}
# trường -> (nhãn, thứ tự ưu tiên chứng từ khi lấy giá trị để tính thuế)
TRUONG = {
    "ma_hs": ("Mã HS", ("to_khai", "co", "hoa_don", "mill_test")),
    "nuoc": ("Nước xuất xứ", ("co", "to_khai", "mill_test", "hoa_don")),
    "nha_sx": ("Nhà sản xuất", ("mill_test", "co", "to_khai", "hoa_don")),
    "nha_xk": ("Nhà xuất khẩu", ("hoa_don", "co", "to_khai", "mill_test")),
    "mac_thep": ("Mác thép", ("mill_test", "hoa_don", "to_khai", "co")),
    "tieu_chuan": ("Tiêu chuẩn", ("mill_test", "hoa_don", "to_khai", "co")),
    "day": ("Độ dày (mm)", ("mill_test", "hoa_don", "to_khai", "co")),
    "rong": ("Chiều rộng (mm)", ("mill_test", "hoa_don", "to_khai", "co")),
    "carbon": ("Carbon (%)", ("mill_test",)),
    "loi": ("Đường kính lõi (mm)", ("mill_test", "hoa_don", "to_khai", "co")),
    "dang": ("Dạng", ("mill_test", "hoa_don", "to_khai", "co")),
}


def _chuan(truong, v):
    """Giá trị -> khóa so sánh. So nhà SX/XK, mác thép theo chuẩn của luật tính thuế."""
    if v in (None, ""):
        return None
    if truong == "ma_hs":
        return pl.la_ma_hs(str(v)) or str(v)
    if truong == "nuoc":
        try:
            return pl.chuan_nuoc(str(v))
        except ValueError:
            return pl.bo_dau(str(v))
    if truong in ("nha_sx", "nha_xk"):
        return pl.chuan_ten_cong_ty(str(v))
    if truong == "mac_thep":
        return pl.chuan_mac_thep(str(v))
    if truong == "tieu_chuan":
        return pl._chuan_tc(str(v))
    if truong == "dang":
        try:
            return pl.chuan_dang(str(v))
        except ValueError:   # chữ lạ: giữ nguyên để hiện thành điểm lệch, không đoán
            return pl.bo_dau(str(v))
    return pl.so(v)


def _khop_ma_hs(a, b):
    """Mã HS: C/O thường ghi 6 số — khớp nếu mã ngắn là tiền tố của mã dài."""
    return a.startswith(b) or b.startswith(a)


def doi_chieu(ho_so):
    """-> (các dòng so sánh, lô dùng để tính thuế, cảnh báo)."""
    ct = ho_so.get("chung_tu") or []
    if not ct:
        raise SystemExit("Hồ sơ không có chứng từ nào (khóa 'chung_tu').")
    dong, lo, canh_bao = [], {}, []
    for truong, (nhan, uu_tien) in TRUONG.items():
        gia_tri = [(c.get("loai", "khac"), c.get(truong), truong in (c.get("khong_chac") or []))
                   for c in ct if c.get(truong) not in (None, "")]
        if not gia_tri:
            continue
        khoa = [(l, _chuan(truong, v), v, kc) for l, v, kc in gia_tri]
        chac = [x for x in khoa if not x[3]]
        if truong == "ma_hs":
            lech = any(not _khop_ma_hs(a[1], b[1]) for a in chac for b in chac)
        elif truong in ("day", "rong", "carbon", "loi"):
            lech = len({round(x[1], 4) for x in chac}) > 1
        else:
            lech = len({x[1] for x in chac}) > 1
        cach_viet = (truong in ("nha_sx", "nha_xk", "mac_thep", "tieu_chuan") and not lech
                     and len({str(x[2]).strip() for x in chac}) > 1)
        if lech:
            ket = "✗ LỆCH"
        elif any(x[3] for x in khoa):
            ket = "? CÓ GIÁ TRỊ ĐỌC KHÔNG CHẮC"
        elif cach_viet:
            ket = "⚠ khớp nhưng khác cách viết"
        else:
            ket = "✓ khớp" if len(khoa) > 1 else "— chỉ có trên 1 chứng từ"
        dong.append({"truong": truong, "nhan": nhan, "ket": ket,
                     "gia_tri": {l: (f"【{v}】" if kc else str(v)) for l, _k, v, kc in khoa}})
        # giá trị để tính thuế: theo thứ tự ưu tiên chứng từ, bỏ qua giá trị không chắc nếu còn giá trị chắc
        ung = sorted(khoa, key=lambda x: (x[3], uu_tien.index(x[0]) if x[0] in uu_tien else 99))
        lo[truong] = ung[0][2]
        if ung[0][3]:
            canh_bao.append(f"{nhan}: chỉ có giá trị đọc KHÔNG CHẮC ({ung[0][2]}) — kiểm bản gốc trước khi dùng.")
        if lech:
            canh_bao.append(f"{nhan} lệch giữa các chứng từ — kết quả dưới đây dùng giá trị trên "
                            f"{LOAI.get(ung[0][0], ung[0][0])} ({ung[0][2]}); cần làm rõ trước khi xác định thuế.")
    return dong, lo, canh_bao


def canh_bao_cach_viet_mac(kho, lo):
    """Mác thép khớp danh mục loại trừ khi bỏ dấu cách nhưng viết khác QĐ (vd 'LRA' vs 'LR A')."""
    mac = lo.get("mac_thep")
    if not mac:
        return []
    ra = set()
    for v in kho["vu_viec"]:
        for x in v.get("loai_tru", []):
            if x["kieu"] == "mac_thep" and pl.chuan_mac_thep(x["mac_thep"]) == pl.chuan_mac_thep(mac) \
                    and x["mac_thep"].strip() != str(mac).strip():
                ra.add(f"Chứng từ ghi mác '{mac}', {v['so_hieu']} ghi '{x['mac_thep']}' — công cụ coi là trùng "
                       f"(bỏ dấu cách), nhưng nên đề nghị thống nhất cách viết trên chứng từ.")
    return sorted(ra)


def lo_tinh_thue(lo):
    """Lô đã đối chiếu -> đầu vào cho pvtm_local.tinh_cho_lo."""
    ma = pl.la_ma_hs(str(lo.get("ma_hs") or ""))
    if not ma or len(ma) != 8:
        raise SystemExit(f"Chưa có mã HS 8 số trên chứng từ (đang có: {lo.get('ma_hs') or 'không'}) — "
                         "không tính được thuế PVTM.")
    return {"code": ma, "nuoc_co": lo.get("nuoc"), "nha_sx": lo.get("nha_sx"), "nha_xk": lo.get("nha_xk"),
            "mac_thep": lo.get("mac_thep"), "tieu_chuan": lo.get("tieu_chuan"), "day": lo.get("day"),
            "rong": lo.get("rong"), "carbon": lo.get("carbon"), "loi": lo.get("loi"), "dang": lo.get("dang")}
