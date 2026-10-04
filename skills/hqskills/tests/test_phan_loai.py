# -*- coding: utf-8 -*-
"""Lệnh `phanloai` — gợi ý mã HS từ tên hàng theo 6 quy tắc GRI. Dữ liệu dựng tại chỗ, không đọc Biểu thuế thật.

Chạy: python -m unittest discover -s skills/hqskills/tests
"""
import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import phan_loai as pl  # noqa: E402
import query_hs as q  # noqa: E402

N7222 = "Thép không gỉ dạng thanh và que khác; thép không gỉ ở dạng góc, khuôn và hình khác"
N7213 = "Sắt hoặc thép không hợp kim, dạng thanh và que, ở dạng cuộn cuốn không đều, được cán nóng"
CODES = {
    "7222": {"desc_vn": N7222},
    "72221100": {"desc_vn": N7222 + " - - Dạng thanh và que, chưa được gia công quá mức cán nóng: - - - Có mặt cắt ngang hình tròn", "mfn": "0"},
    "72221900": {"desc_vn": N7222 + " - - Dạng thanh và que, chưa được gia công quá mức cán nóng: - - - Loại khác", "mfn": "0"},
    "72224000": {"desc_vn": N7222 + " - - Các dạng góc, khuôn và hình", "mfn": "0"},
    "7213": {"desc_vn": N7213},
    "72139190": {"desc_vn": N7213 + " - - Loại khác: - - - Loại khác", "mfn": "10"},
    "7221": {"desc_vn": ""},
    "72210000": {"desc_vn": "Thanh và que thép không gỉ được cán nóng, dạng cuộn cuốn không đều", "mfn": "0"},
    "9810": {"desc_vn": "Thép không gỉ dạng thanh tròn cán nóng để sản xuất tanh lốp"},
    "98100000": {"desc_vn": "Thép không gỉ dạng thanh tròn cán nóng để sản xuất tanh lốp - - Loại khác", "mfn": "0"},
}
CHU_GIAI = {"72": "Sắt và thép. Chú giải. 1. Chương này không bao gồm thép đúc dạng thanh thuộc Chương 73. "
                  "(d) Thép là vật liệu dễ uốn có chứa sắt."}
DN = {"inox": "thép không gỉ"}


class TachTen(unittest.TestCase):
    def test_bo_hieu_model_xuat_xu_va_moi_100(self):
        t = pl.tach_ten("Thép không gỉ dạng thanh tròn, hiệu POSCO, model X1, xuất xứ Hàn Quốc, hàng mới 100%", DN)
        self.assertEqual(t["tu"], ["thep", "khong", "gi", "dang", "thanh", "tron"])
        self.assertTrue(any("POSCO" in b for b in t["bo_qua"]))
        self.assertTrue(any("Hàn Quốc" in b for b in t["bo_qua"]))

    def test_thong_so_tach_rieng_khong_vao_tu_khoa(self):
        t = pl.tach_ten("Thép tấm dày 12mm x 1500mm", DN)
        self.assertIn("12mm x 1500mm", t["thong_so"][0])
        self.assertNotIn("12", t["tu"])

    def test_tu_thuong_mai_thay_bang_tu_bieu_thue(self):
        t = pl.tach_ten("ống inox 304", DN)
        self.assertEqual(t["dong_nghia"], {"inox": "thép không gỉ"})
        self.assertEqual(t["tu"][:4], ["ong", "thep", "khong", "gi"])

    def test_dau_hieu_gri(self):
        t = pl.tach_ten("Bộ gồm bút và sổ, kèm hộp giấy; xe đạp dạng tháo rời; hỗn hợp cao su", DN)
        self.assertEqual(set(t["dau_hieu"]), {"2(a)", "2(b)", "3", "5"})


class PhanLoai(unittest.TestCase):
    def kq(self, ten, **kw):
        return pl.phan_loai(ten, CODES, CHU_GIAI, {}, **kw)

    def test_cum_lien_thang_tu_roi(self):
        r = self.kq("Thép không gỉ dạng thanh tròn cán nóng")
        self.assertEqual(r["nhom"][0]["nhom"], "7222")
        self.assertEqual(r["nhom"][0]["ma"][0]["ma"], "72221100")
        self.assertEqual(r["do_tin_cay"], "khá")

    def test_chuong_98_khong_la_ung_vien(self):
        r = self.kq("Thép không gỉ dạng thanh tròn cán nóng")
        self.assertNotIn("9810", [n["nhom"] for n in r["nhom"]] + [n["nhom"] for n in r["lan_can"]])
        self.assertEqual([n["nhom"] for n in self.kq("Thép không gỉ thanh tròn cán nóng", chuong="98")["nhom"]], ["9810"])

    def test_nhom_canh_tranh_lay_mo_ta_tu_ma_8_so_khi_dong_4_so_trong(self):
        r = self.kq("Thép không gỉ dạng thanh tròn cán nóng")
        lc = {x["nhom"]: x["mo_ta"] for x in r["lan_can"]}
        self.assertIn("7221", lc)
        self.assertTrue(lc["7221"].startswith("Thanh và que thép không gỉ"))

    def test_cau_loai_tru_chi_lay_cau_nhac_toi_tu_cua_hang(self):
        r = self.kq("Thép không gỉ dạng thanh tròn cán nóng")
        self.assertEqual(len(r["nhom"][0]["loai_tru"]), 1)
        self.assertIn("không bao gồm thép đúc dạng thanh", r["nhom"][0]["loai_tru"][0])

    def test_gri6_dong_phan_biet_nguyen_van_va_bo_phan_lap_mo_ta_nhom(self):
        r = self.kq("Thép không gỉ dạng thanh tròn cán nóng")
        n = r["nhom"][0]   # chỉ 1 mã khớp đủ → dòng phân biệt lấy từ MỌI mã 8 số của nhóm
        self.assertEqual(n["nhom"], "7222")
        self.assertIn("Có mặt cắt ngang hình tròn", n["phan_biet"])
        self.assertIn("Loại khác", n["phan_biet"])
        self.assertTrue(all(not m["mo_ta"].startswith(N7222) for m in n["ma"]))
        self.assertTrue(any("GRI 6" in c for c in r["cau_hoi"]))

    def test_nhieu_nhom_sat_diem_thi_bao_gri3_va_hoi_dac_trung_co_ban(self):
        r = pl.phan_loai("thép thanh", {k: v for k, v in CODES.items() if not k.startswith("98")}, CHU_GIAI, {})
        g = r["gri"]["3"]
        self.assertTrue(len(g["3a_chua_tach_duoc"]) >= 2)
        self.assertEqual(g["3c_nhom_cuoi_cung"], max(g["3a_chua_tach_duoc"]))
        self.assertTrue(any("3(b)" in c for c in r["cau_hoi"]))

    def test_khong_khop_gi_thi_gri4(self):
        r = self.kq("xyzabc qwerty")
        self.assertEqual(r["nhom"], [])
        self.assertTrue(r["gri"]["4"])
        self.assertEqual(r["do_tin_cay"], "thấp")

    def test_in_ra_khong_loi_va_co_du_muc(self):
        r = self.kq("Bộ gồm thép không gỉ thanh tròn cán nóng kèm hộp")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            pl.in_ket_qua(r, CODES)
        ra = buf.getvalue()
        for muc in ("[QT 1]", "[QT 3]", "[QT 5]", "[QT 6]", "CẦN HỎI", "CHỈ LÀ GỢI Ý"):
            self.assertIn(muc, ra)


class XepHangCum(unittest.TestCase):
    def test_search_cung_duoc_cong_diem_cum_lien(self):
        kq = q.xep_hang(CODES, "thep khong gi can nong")
        self.assertEqual(kq[0][1], "72210000")   # có cả "thep khong gi" lẫn "can nong" liền nhau


if __name__ == "__main__":
    unittest.main()
