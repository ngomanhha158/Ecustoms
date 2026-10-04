# -*- coding: utf-8 -*-
"""Xếp hạng tầng 2: IDF, phạm vi phủ định, chuỗi liền mạch, chuẩn hóa số. Dữ liệu dựng tại chỗ (< 1000 mã → không cache)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import query_hs as q  # noqa: E402


class PhamViPhuDinh(unittest.TestCase):
    def test_tru_toi_het_menh_de(self):
        am = q.tu_bi_phu_dinh("Máy tính cá nhân trừ máy tính loại xách tay của phân nhóm 8471.30")
        self.assertTrue({"xach", "tay"} <= am)
        self.assertNotIn("ca", am)   # "cá nhân" khẳng định

    def test_dau_phay_ve_dai_thi_dung(self):
        am = q.tu_bi_phu_dinh("Sắt hoặc thép không hợp kim, dạng thanh và que, ở dạng cuộn cuốn không đều, được cán nóng")
        self.assertEqual(am & {"hop", "kim", "thanh", "can", "nong"}, {"hop", "kim"})

    def test_liet_ke_ngan_va_ngoac_khong_cat(self):
        am = q.tu_bi_phu_dinh("thép cán nóng, chưa dát phủ (clad), phủ, mạ (coated) hoặc tráng (plated) - - Dạng cuộn")
        self.assertTrue({"phu", "ma", "trang"} <= am)
        self.assertNotIn("cuon", am)

    def test_tu_vua_khang_dinh_vua_phu_dinh_khong_tinh(self):
        am = q.tu_bi_phu_dinh("Máy điều hòa không khí, kể cả loại máy không điều chỉnh độ ẩm")
        self.assertNotIn("dieu", am)
        self.assertIn("khi", am)


class TachTu(unittest.TestCase):
    def test_so_bo_dau_nghin_tach_don_vi(self):
        self.assertEqual(q._tu("điện áp không quá 1.000 V"), ["dien", "ap", "khong", "qua", "1000", "v"])
        self.assertEqual(q._tu("1000V"), ["1000", "v"])
        self.assertEqual(q._tu("phân nhóm 8471.30"), ["phan", "nhom", "8471", "30"])


CODES = {
    "72139190": {"desc_vn": "Sắt hoặc thép không hợp kim, dạng thanh và que, được cán nóng - - Loại khác"},
    "72283010": {"desc_vn": "Thép hợp kim khác dạng thanh và que, cán nóng - - - Có mặt cắt ngang hình tròn"},
    "84713020": {"desc_vn": "Máy xử lý dữ liệu tự động - - loại xách tay - - - Máy tính xách tay kể cả notebook"},
    "84714910": {"desc_vn": "Máy xử lý dữ liệu tự động - - Loại khác - - - Máy tính cá nhân trừ máy tính loại xách tay"},
    "84151020": {"desc_vn": "Máy điều hòa không khí - - Loại treo tường, kể cả loại máy không điều chỉnh độ ẩm"},
    "84186949": {"desc_vn": "Máy làm lạnh - - Loại khác, công suất làm lạnh trên 21 kW - - - Loại khác"},
}


class XepHang(unittest.TestCase):
    def dau(self, tu_khoa):
        return q.xep_hang(CODES, tu_khoa)[0][1]

    def test_hop_kim_khong_roi_vao_khong_hop_kim(self):
        self.assertEqual(self.dau("thép hợp kim dạng thanh cán nóng"), "72283010")

    def test_khong_hop_kim_khong_roi_vao_hop_kim(self):
        self.assertEqual(self.dau("thép không hợp kim dạng thanh cán nóng"), "72139190")

    def test_tru_xach_tay_bi_phat(self):
        self.assertEqual(self.dau("máy tính xách tay"), "84713020")

    def test_chuoi_lien_mach_thang_tu_roi(self):
        self.assertEqual(self.dau("máy điều hòa không khí công suất lớn"), "84151020")


if __name__ == "__main__":
    unittest.main()
