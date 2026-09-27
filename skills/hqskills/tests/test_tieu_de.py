# -*- coding: utf-8 -*-
"""Tiêu đề hồ sơ vụ theo "Mô tả hàng hóa" (CEO 27-09) trên dữ liệu thật data/pvtm.json.

Bản chép ILMS services/pvtm.tieu_de; so với máy chủ bằng scripts/kiem_khop.py.
Chạy: python -m unittest discover -s skills/hqskills/tests
"""
import os
import sys
import unicodedata
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import pvtm_local as pl  # noqa: E402

KHO = pl.doc_kho()


class TieuDe(unittest.TestCase):
    def test_vu_ceo_chi(self):
        v = next(x for x in KHO["vu_viec"] if x["ma_vu_viec"] == "AC03.AD20")
        self.assertTrue(pl.tieu_de(v["mo_ta"], v["ten_hang"]).startswith(
            "Sắt hoặc thép hợp kim hoặc không hợp kim được cán phẳng; được cán nóng; "
            "độ dày từ 1,2mm đến 25,4mm; có chiều rộng lớn hơn 1.880mm"))

    def test_moi_vu_nguyen_van(self):
        for v in KHO["vu_viec"]:
            td = pl.tieu_de(v["mo_ta"], v["ten_hang"])
            mt = " ".join(unicodedata.normalize("NFC", v["mo_ta"] or "").split())
            with self.subTest(v["ma_vu_viec"]):
                self.assertTrue(td)
                self.assertTrue(not mt or mt.lower().endswith(td.lower()), td)
                self.assertFalse(td.lower().startswith(("hàng hóa", "hàng hoá", "một số sản phẩm", "sản phẩm ")), td)

    def test_bien(self):
        nfd = unicodedata.normalize("NFD", "Hàng hoá bị áp dụng thuế là các sản phẩm thép mạ kẽm.")
        self.assertEqual(pl.tieu_de(nfd, "x"), "Thép mạ kẽm.")
        self.assertEqual(pl.tieu_de("", "Thép cán nóng"), "Thép cán nóng")
        self.assertEqual(pl.tieu_de(None, "Thép mạ"), "Thép mạ")
        que = "Que hàn inox 308 có bọc thuốc, kể cả sản phẩm đóng hộp."
        self.assertEqual(pl.tieu_de(que, "x"), que)


if __name__ == "__main__":
    unittest.main()
