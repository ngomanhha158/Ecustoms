# -*- coding: utf-8 -*-
"""Kiểm doi_chieu.py: phát hiện lệch, khác cách viết, giá trị đọc không chắc, và ưu tiên chứng từ."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import doi_chieu as dc  # noqa: E402
import pvtm_local as pl  # noqa: E402
import soat_lo  # noqa: E402


def dong_cua(dong, truong):
    return next(d for d in dong if d["truong"] == truong)


class DoiChieu(unittest.TestCase):
    HO_SO = {"chung_tu": [
        {"loai": "mill_test", "nha_sx": "Hingfui Steel Co., Ltd", "mac_thep": "LRA", "tieu_chuan": "LR",
         "day": 12, "rong": 1500, "carbon": 0.18, "dang": "tam", "khong_chac": ["carbon"]},
        {"loai": "co", "nuoc": "China", "nha_sx": "HINGFUI STEEL CO LTD", "ma_hs": "7208.51"},
        {"loai": "hoa_don", "nha_xk": "ABC Trading Limited", "mac_thep": "LR A", "rong": 1520},
        {"loai": "to_khai", "ma_hs": "72085100", "nuoc": "CN", "nha_xk": "ABC Trading Ltd"},
    ]}

    def setUp(self):
        self.dong, self.lo, self.cb = dc.doi_chieu(self.HO_SO)

    def test_lech_chieu_rong(self):
        self.assertTrue(dong_cua(self.dong, "rong")["ket"].startswith("✗"))
        self.assertEqual(self.lo["rong"], 1500)          # ưu tiên Mill Test
        self.assertTrue(any("Chiều rộng" in c and "lệch" in c for c in self.cb))

    def test_khong_chac_khong_bao_gio_la_khop(self):
        d = dong_cua(self.dong, "carbon")
        self.assertTrue(d["ket"].startswith("?"))
        self.assertEqual(d["gia_tri"]["mill_test"], "【0.18】")

    def test_khac_cach_viet(self):
        for t in ("nha_sx", "nha_xk", "mac_thep"):
            self.assertTrue(dong_cua(self.dong, t)["ket"].startswith("⚠"), t)

    def test_ma_hs_6_so_khop_8_so_va_nuoc_quy_doi(self):
        self.assertTrue(dong_cua(self.dong, "ma_hs")["ket"].startswith("✓"))
        self.assertTrue(dong_cua(self.dong, "nuoc")["ket"].startswith("✓"))
        self.assertEqual(self.lo["ma_hs"], "72085100")   # ưu tiên tờ khai (đủ 8 số)

    def test_canh_bao_mac_viet_khac_qd_va_soat_thue(self):
        kho = pl.doc_kho()
        self.assertTrue(any("'LRA'" in c and "'LR A'" in c for c in dc.canh_bao_cach_viet_mac(kho, self.lo)))
        r = soat_lo.soat(kho, dc.lo_tinh_thue(self.lo))
        self.assertEqual(next(k for k in r["vu_viec"] if k["ma_vu_viec"] == "AD20")["ket_luan"], "khong_ap")

    def test_thieu_ma_hs_8_so(self):
        with self.assertRaises(SystemExit):
            dc.lo_tinh_thue({"ma_hs": "7208.51"})


if __name__ == "__main__":
    unittest.main()
