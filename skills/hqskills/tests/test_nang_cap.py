# -*- coding: utf-8 -*-
"""Nâng cấp 1-7 (CEO 25-09-2026): cách miễn trừ, soát đặc tính hàng, tóm tắt vụ, mã thuộc nhiều vụ,
thử lại khi mạng chập chờn, xếp hạng tìm văn bản. Không cần mạng — dữ liệu dựng tại chỗ.

Chạy: python -m unittest discover -s skills/hqskills/tests
"""
import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import ilms_api  # noqa: E402
import pvtm_local as pl  # noqa: E402
import query_hs as q  # noqa: E402


def vu(ma, ma_hs, tu="2024-01-01", den=None, giai_doan="chinh_thuc"):
    return {"ma_vu_viec": ma, "ma_hs": ma_hs, "hieu_luc_tu": tu, "hieu_luc_den": den, "giai_doan": giai_doan}


class TrungMa(unittest.TestCase):
    def test_chi_liet_ke_ma_thuoc_tu_hai_vu_dang_ap(self):
        kho = {"vu_viec": [vu("AD15.QUE", ["83113099", "83119000"]), vu("AD15.DAY", ["83113099", "72171010"]),
                           vu("CU", ["83113099"], den="2020-01-01")]}   # vụ hết hạn không tính
        self.assertEqual(pl.trung_ma(kho), {"83113099": ["AD15.QUE", "AD15.DAY"]})


class LechPhu(unittest.TestCase):
    CHUA = "Các sản phẩm ... chưa dát phủ, phủ, mạ hoặc tráng"
    DA = "Các sản phẩm ... đã dát phủ (clad), phủ, mạ (coated) hoặc tráng - - Được sơn"

    def test_da_son_ma_chua_phu_thi_canh_bao(self):
        self.assertIn("ĐÃ sơn", pl.lech_phu("đã sơn lót", self.CHUA))
        self.assertIn("ĐÃ sơn", pl.lech_phu("mạ kẽm", self.CHUA))

    def test_chua_son_ma_da_phu_thi_canh_bao(self):
        self.assertIn("CHƯA sơn", pl.lech_phu("chưa sơn, có phủ dầu", self.DA))

    def test_khop_nhom_hoac_phu_dau_thi_im(self):
        for dt, mo_ta in (("đã sơn lót", self.DA), ("có phủ dầu", self.CHUA), ("không phủ dầu", self.CHUA),
                          ("chưa mạ", self.CHUA), ("thép cán nóng", self.CHUA), ("", self.CHUA)):
            self.assertEqual(pl.lech_phu(dt, mo_ta), "", dt)


class NhanMien(unittest.TestCase):
    def test_nhan_theo_thu_tuc(self):
        self.assertIn("kiểm định", q._nhan_mien({"thu_tuc": "kiem_dinh"}))
        self.assertIn("Bộ Công Thương", q._nhan_mien({"thu_tuc": "xin_mien_tru"}))
        self.assertEqual(q._nhan_mien({"thu_tuc": None}), "")
        self.assertEqual(q._nhan_mien({}), "")   # dữ liệu đồng bộ trước phase141


class TomTat(unittest.TestCase):
    def test_moi_vu_mot_dong_dang_ap_truoc(self):
        kho = {"dong_bo_luc": "2026-09-28T00:00:00+00:00", "vu_viec": [
            {**vu("CU", ["1"], den="2020-01-01"), "ten_hang": "Hàng cũ", "nuoc": [], "muc_khong_chung_tu": 5},
            {**vu("MOI", ["2"]), "ten_hang": "Hàng mới", "nuoc": [{"nuoc": "CN", "muc_toan_quoc": 27.83}],
             "muc_khong_chung_tu": 27.83, "so_hieu": "1/QĐ-BCT", "da_doi_chieu": True}]}
        ra = io.StringIO()
        with contextlib.redirect_stdout(ra):
            q.cmd_tom_tat(kho)
        s = ra.getvalue()
        self.assertLess(s.index("[MOI]"), s.index("[CU]"))
        self.assertIn("CN 27,83%", s)
        self.assertIn("chưa đối chiếu", s.split("[CU]")[1])


class XepHangVanBan(unittest.TestCase):
    def ds(self):
        than = "Căn cứ Luật... " * 40   # văn bản nào cũng đầy "căn cứ"
        return [{"so_hieu": "32/2026/QĐ-TTg", "tieu_de": "Danh mục ngành sản phẩm", "rel": "a",
                 "noi_dung": than + "thép cán nóng, thép cán nguội, nền kinh tế " * 30},
                {"so_hieu": "2822/QĐ-BCT", "tieu_de": "CBPG thép cán phẳng được sơn", "rel": "b",
                 "noi_dung": than + "(i) Các sản phẩm có lớp nền là thép cán nóng;"},
                {"so_hieu": "9/QĐ", "tieu_de": "Khác", "rel": "c", "noi_dung": than}]

    def test_co_dau_khong_khop_can_cu(self):
        kq = q.xep_hang_vb(self.ds(), "lớp nền thép cán nóng")
        self.assertEqual(kq[0][1]["so_hieu"], "2822/QĐ-BCT")
        self.assertNotIn("9/QĐ", [v["so_hieu"] for _d, v, _t in kq], "chỉ có 'căn cứ' thì không được khớp 'cán'")

    def test_khong_dau_van_dua_van_ban_dung_len_dau(self):
        self.assertEqual(q.xep_hang_vb(self.ds(), "lop nen thep can nong")[0][1]["so_hieu"], "2822/QĐ-BCT")

    def test_trich_doan_to_dam_tu_khop_tren_ban_goc(self):
        doan = q.xep_hang_vb(self.ds(), "lớp nền thép cán nóng")[0][2][0]
        self.assertIn("**lớp** **nền**", doan)


class ThuLaiMang(unittest.TestCase):
    def setUp(self):
        self.goc = ilms_api._goi_mot

    def tearDown(self):
        ilms_api._goi_mot = self.goc

    def test_get_thu_lai_roi_qua(self):
        lan = []

        def gia(*a):
            lan.append(1)
            if len(lan) < 3:
                raise TimeoutError()
            return {"ok": 1}
        ilms_api._goi_mot = gia
        self.assertEqual(ilms_api._goi("GET", "/x"), {"ok": 1})
        self.assertEqual(len(lan), 3)

    def test_post_khong_thu_lai_bao_loi_de_doc(self):
        lan = []

        def gia(*a):
            lan.append(1)
            raise TimeoutError()
        ilms_api._goi_mot = gia
        with self.assertRaises(SystemExit) as e:
            ilms_api._goi("POST", "/x")
        self.assertEqual(len(lan), 1, "POST có thể đã ghi / đã tốn một lượt OCR — không thử lại")
        self.assertIn("chập chờn", str(e.exception))


if __name__ == "__main__":
    unittest.main()
