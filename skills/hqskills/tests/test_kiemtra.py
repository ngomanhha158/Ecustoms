# -*- coding: utf-8 -*-
"""Lệnh `kiemtra` — phiếu kiểm tra dòng hàng trên dữ liệu thật (hs_tree.json + data/pvtm.json).

Luật là bản chép ILMS (kiem_tra_dong_local.py); test này canh đường nối của skill: đọc Biểu thuế trên máy,
tính PVTM bằng pvtm_local, báo lỗi nhập rõ ràng, xuất chữ / HTML không vỡ.
Chạy: python -m unittest discover -s skills/hqskills/tests
"""
import contextlib
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import kiem_tra_in as ki  # noqa: E402
import pvtm_local as pl  # noqa: E402

with open(os.path.join(ki.DATA, "hs_tree.json"), encoding="utf-8") as f:
    CODES = json.load(f)["codes"]
KHO = pl.doc_kho()
A709 = {"ma": "72254090", "nuoc": "CN", "thue_suat": "0", "mo_ta": (
    "Thép tấm hợp kim crom được cán phẳng, chưa được gia công quá mức cán nóng, chứa C=0.07%-> 0.09% "
    "Cr= 0.49%->0.52%,KT: 40x2440x5729mm,TC: ASTM A709-2024,Mác: A709Gr50W. Mới 100%")}


class PhieuA709(unittest.TestCase):
    def test_dung_mau_duyet(self):
        p = ki.kiem_tra(dict(A709), CODES, KHO)
        o = {x["khoa"]: x["gt"] for x in p["o"]}
        self.assertEqual((o["ma_hs"], o["thue"], o["cbpg"]), ("ĐÚNG", "0%", "KHÔNG ÁP"))
        viec = [x["viec"] for x in p["tan_mat"]]
        self.assertIn("Đo độ dày: phải trên 25,4 mm thì nằm ngoài phạm vi chống bán phá giá", viec)
        self.assertEqual([x["code"] for x in p["nghi_ngo"]], ["72254090", "72085100"])
        self.assertTrue(all(v["ket_luan"] == "Ngoài phạm vi" for v in p["pvtm"]))

    def test_can_cu_nguyen_van(self):
        p = ki.kiem_tra(dict(A709), CODES, KHO)
        cc = p["lap_luan"][0]["can_cu"][0]
        self.assertEqual((cc["nhan"], cc["nhan_manh"]), ("Chú giải 1(f) Chương 72", "Crôm từ 0,3% trở lên"))
        self.assertIn("- Crôm từ 0,3% trở lên", cc["trich"])
        self.assertTrue(all(x.get("can_cu") for x in p["tan_mat"]))
        self.assertTrue(all(isinstance(x, dict) for v in p["pvtm"] for x in v["van_ban"]))

    def test_cap_khong_xe_gach_giua_cau(self):
        cap = ki.kt._cap({"desc_vn": CODES["72259220"]["desc_vn"]})
        self.assertTrue(cap[-1].endswith("kẽm - nhôm - magiê"), cap)

    def test_in_chu_va_html(self):
        p = ki.kiem_tra(dict(A709), CODES, KHO)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ki.in_chu(p)
        self.assertIn("KIỂM HÓA CẦN XEM TẬN MẮT", buf.getvalue())
        h = ki.in_html(p)
        self.assertTrue(h.startswith("<!doctype html>") and "7208.51.00" in h and "<mark>Crôm từ 0,3% trở lên</mark>" in h and "<script" not in h)


class LoiNhap(unittest.TestCase):
    def test_bao_ro(self):
        for sai, chu in (({"ma": "7225"}, "đủ 8 số"), ({"ma": "99999999"}, "Không có mã"),
                         ({"thue_suat": "KCT"}, "không phải số"), ({"nuoc": "Atlantis"}, "")):
            with self.assertRaises(SystemExit) as e:
                ki.kiem_tra({**A709, **sai}, CODES, KHO)
            self.assertIn(chu, str(e.exception))

    def test_ten_nuoc_va_thue_co_phan_tram(self):
        p = ki.kiem_tra({**A709, "nuoc": "Trung Quốc", "thue_suat": "5%"}, CODES, KHO)
        self.assertEqual(p["dau"]["nuoc"], "CN")
        self.assertIn("LỆCH TK", p["o"][1]["ct"])


if __name__ == "__main__":
    unittest.main()
