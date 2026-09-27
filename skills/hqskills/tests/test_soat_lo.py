# -*- coding: utf-8 -*-
"""Kiểm luật soát lô (bản chép ILMS trong pvtm_local.py) trên dữ liệu thật data/pvtm.json.

Chạy: python -m unittest discover -s skills/hqskills/tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import pvtm_local as pl  # noqa: E402

KHO = pl.doc_kho()


def vu(r, ma):
    return next(k for k in r["vu_viec"] if k["ma_vu_viec"] == ma)


def lo(code, **kw):
    return {"code": code, "nuoc_co": "CN", **kw}


class DocSo(unittest.TestCase):
    def test_dau_phay_va_ngan_nghin(self):
        self.assertEqual(pl.doc_so("1.880"), 1880)
        self.assertEqual(pl.doc_so("0,108"), 0.108)
        self.assertEqual(pl.doc_so("0.30"), 0.30)
        self.assertEqual(pl.doc_so("2.300"), 2300)

    def test_khoang(self):
        self.assertEqual(pl.khoang("từ 1,2 mm đến 25,4 mm"), [(">=", 1.2), ("<=", 25.4)])
        self.assertEqual(pl.khoang("không quá 1.880 mm"), [("<=", 1880)])
        self.assertEqual(set(pl.khoang("lớn hơn 1.880mm và nhỏ hơn hoặc bằng 2.300mm")), {(">", 1880), ("<=", 2300)})
        self.assertEqual(pl.khoang("Dưới 1.600 mm"), [("<", 1600)])
        self.assertEqual(pl.khoang("0,108 – 2,55 mm"), [(">=", 0.108), ("<=", 2.55)])
        lo_, hi = pl.khoang("từ 2,0 mm đến 4,0 mm, dung sai +/- 0,2 mm")
        self.assertAlmostEqual(lo_[1], 1.8)
        self.assertAlmostEqual(hi[1], 4.2)
        self.assertEqual(pl.khoang("Bất kể"), [])


class LoaiTruMacThepDangTam(unittest.TestCase):
    """AD20: 1959/QĐ-BCT chỉ loại trừ mác thép với hàng DẠNG TẤM."""

    def test_chua_nhap_dang_la_chua_du(self):
        k = vu(pl.tinh_cho_lo(KHO, lo("72085100", mac_thep="LR A", tieu_chuan="LR")), "AD20")
        self.assertEqual(k["ket_luan"], "chua_du")
        self.assertIn("Dạng (tấm/cuộn)", k["thieu"])

    def test_dang_cuon_van_bi_ap(self):
        k = vu(pl.tinh_cho_lo(KHO, lo("72085100", mac_thep="LR A", tieu_chuan="LR", dang="cuon")), "AD20")
        self.assertEqual(k["ket_luan"], "ap")
        self.assertAlmostEqual(k["muc_thue"], 27.83)

    def test_dang_tam_duoc_loai_tru(self):
        k = vu(pl.tinh_cho_lo(KHO, lo("72085100", mac_thep="LR A", tieu_chuan="LR", dang="tấm")), "AD20")
        self.assertEqual(k["ket_luan"], "khong_ap")


class PhamViQuyCach(unittest.TestCase):
    def test_rong_2000_ngoai_ad20_trong_ac03(self):
        r = pl.tinh_cho_lo(KHO, lo("72082600", day=8, rong=2000, carbon=0.2, dang="cuon"))
        self.assertEqual(vu(r, "AD20")["ket_luan"], "khong_thuoc_pham_vi")
        self.assertEqual(vu(r, "AC03.AD20")["ket_luan"], "ap")

    def test_bien_1880_thuoc_ad20_khong_thuoc_ac03(self):
        r = pl.tinh_cho_lo(KHO, lo("72082600", day=8, rong=1880, carbon=0.2, dang="cuon"))
        self.assertEqual(vu(r, "AD20")["ket_luan"], "ap")
        self.assertEqual(vu(r, "AC03.AD20")["ket_luan"], "khong_thuoc_pham_vi")

    def test_ac03_tam_tu_10mm_loai_tru(self):
        r = pl.tinh_cho_lo(KHO, lo("72082600", day=12, rong=2000, carbon=0.2, dang="tam"))
        self.assertEqual(vu(r, "AC03.AD20")["ket_luan"], "khong_ap")

    def test_ac03_thieu_dang_khi_day_12_la_chua_du(self):
        r = pl.tinh_cho_lo(KHO, lo("72082600", day=12, rong=2000, carbon=0.2))
        self.assertEqual(vu(r, "AC03.AD20")["ket_luan"], "chua_du")

    def test_ac03_ke_thua_loai_tru_mac_cua_ad20(self):
        r = pl.tinh_cho_lo(KHO, lo("72082600", rong=2000, mac_thep="LR A", tieu_chuan="LR", dang="tam"))
        self.assertEqual(vu(r, "AC03.AD20")["ket_luan"], "khong_ap")

    def test_que_han_dung_sai(self):
        self.assertEqual(vu(pl.tinh_cho_lo(KHO, lo("83111090", loi=4.1)), "AD15.QUE")["ket_luan"], "ap")
        self.assertEqual(vu(pl.tinh_cho_lo(KHO, lo("83111090", loi=4.3)), "AD15.QUE")["ket_luan"],
                         "khong_thuoc_pham_vi")

    def test_day_han_carbon_loi(self):
        k = vu(pl.tinh_cho_lo(KHO, lo("72171010", loi=1.2, carbon=0.25)), "AD15.DAY")
        self.assertEqual(k["ket_luan"], "khong_thuoc_pham_vi")

    def test_khong_nhap_quy_cach_van_ap_kem_canh_bao_gia_dinh(self):
        k = vu(pl.tinh_cho_lo(KHO, lo("72091610")), "ER01.AD08")
        self.assertEqual(k["ket_luan"], "ap")
        self.assertTrue(any("GIẢ ĐỊNH" in c for c in k["canh_bao"]))


class RaSoat27_09(unittest.TestCase):
    """Các lỗi rà soát ở ILMS PR #575 — bản chép phải cho cùng kết quả."""

    def test_nuoc_khong_bi_ap_khong_hoi_dang(self):
        r = pl.tinh_cho_lo(KHO, {"code": "72082600", "nuoc_co": "JP", "mac_thep": "LR A", "tieu_chuan": "LR"})
        self.assertEqual(vu(r, "AC03.AD20")["ket_luan"], "khong_ap")

    def test_co_chua_du_va_thong_so_quyet_dinh_dung_dau(self):
        r = pl.tinh_cho_lo(KHO, lo("72085100", mac_thep="LR A", tieu_chuan="LR"))
        self.assertTrue(r["chua_du"])
        self.assertFalse(r["bi_ap"])
        self.assertEqual(vu(r, "AD20")["thieu_khoa"][0], "dang")

    def test_o_nhap_doc_so_nhu_chu_qd(self):
        self.assertEqual(pl.chuan_lo(lo("72082600", rong="2.000", carbon="0,18"))["rong"], 2000)
        self.assertEqual(pl.doc_so("0.300"), 0.3)
        self.assertEqual(pl.khoang("trên 3 mm đến 10 mm"), [(">", 3), ("<=", 10)])

    def test_o_nhap_mo_ho_hoac_la_thi_dung(self):
        for sai in ({"day": "2.500"}, {"dang": "ống"}, {"day": -1}, {"nuoc_co": "Sao Hỏa"}):
            with self.assertRaises(SystemExit, msg=sai):
                pl.tinh_cho_lo(KHO, lo("72082600", **sai))

    def test_dieu_kien_lay_tu_du_lieu_dong_bo(self):
        theo_ma = {v["ma_vu_viec"]: v for v in KHO["vu_viec"]}
        self.assertEqual([d["loai"] for d in theo_ma["AD20"]["dieu_kien"]], ["mac_thep_chi_khi"])
        self.assertTrue(theo_ma["AC03.AD20"]["dieu_kien"][0]["loai_tru_mac"])


if __name__ == "__main__":
    unittest.main()
