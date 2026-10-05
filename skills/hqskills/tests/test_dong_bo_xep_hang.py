# -*- coding: utf-8 -*-
"""Một luật một chỗ: scripts/hs_xep_hang.py phải đúng bằng bản ILMS đi qua chep_xep_hang_ilms.chuyen();
tu_dong_nghia.json giống hệt bản ILMS; tiền lệ ghi/đọc đúng; Chương lấy theo 2 số đầu mã.

Phần so với ILMS chỉ chạy khi có bản ILMSv2 nằm cạnh (máy dev: <cha>/ilmsV2) — không có thì bỏ qua.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC, "scripts"))
import chep_xep_hang_ilms as chep  # noqa: E402
import query_hs as q  # noqa: E402

ILMS = os.path.abspath(os.path.join(GOC, "..", "..", "..", "ilmsV2", "backend"))
NGUON = os.path.join(ILMS, "app", "services", "hs_xep_hang.py")


@unittest.skipUnless(os.path.exists(NGUON), "không có bản ILMSv2 cạnh repo")
class KhopILMS(unittest.TestCase):
    def test_ban_chep_khop(self):
        with open(NGUON, encoding="utf-8") as f:
            mong = chep.chuyen(f.read()).split("\n", 2)[2]          # bỏ 2 dòng đầu (ghi commit)
        with open(chep.DICH, encoding="utf-8") as f:
            co = f.read().split("\n", 2)[2]
        self.assertEqual(co, mong, "scripts/hs_xep_hang.py lệch ILMS — chạy scripts/chep_xep_hang_ilms.py, đừng sửa tay")

    def test_dong_nghia_khop(self):
        with open(os.path.join(ILMS, "db", "tra_cuu_seed", "tu_dong_nghia.json"), encoding="utf-8") as f:
            ilms = json.load(f)
        with open(os.path.join(GOC, "data", "tu_dong_nghia.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), ilms)


class TienLe(unittest.TestCase):
    def test_ghi_doc_va_cong_diem(self):
        codes = {"40111000": {"desc_vn": "Lốp bơm hơi mới bằng cao su - - Loại dùng cho ô tô con"},
                 "40121100": {"desc_vn": "Lốp đắp lại bằng cao su - - Loại dùng cho ô tô con"}}
        with tempfile.TemporaryDirectory() as d:
            cu_tep, cu_load = q.TEP_TIEN_LE, q.load_json
            q.TEP_TIEN_LE = os.path.join(d, "tien_le.tsv")
            q.load_json = lambda name: {"codes": codes}
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    q.cmd_tienle("Lốp bơm hơi cao su dùng cho ô tô con", "4011.10.00")
                    with self.assertRaises(SystemExit):
                        q.cmd_tienle("x", "1234")
                ds = q.tien_le()
                self.assertEqual([(i, m) for i, _t, m in ds], [(1, "40111000")])
                kq = q.xep_hang(codes, "lốp cao su ô tô con")
                self.assertEqual(kq[0][1], "40111000")
                self.assertEqual(kq[0][2].get("tien_le"), 1)
                self.assertEqual(q.xep_hang(codes, "lốp cao su ô tô con", tien_le_ds=[])[0][2].get("tien_le"), None)
            finally:
                q.TEP_TIEN_LE, q.load_json = cu_tep, cu_load


class Chuong(unittest.TestCase):
    def test_hs_tree_chuong_theo_ma(self):
        codes = q.load_json("hs_tree.json").get("codes", {})
        if not codes:
            self.skipTest("chưa nạp hs_tree.json")
        lech = [c for c, e in codes.items() if c[:2].isdigit() and e.get("chapter") != f"Chương {int(c[:2])}"]
        self.assertEqual(lech[:5], [], "Chương phải bằng 2 số đầu mã (98xx từng bị ghi Chương 97)")


if __name__ == "__main__":
    unittest.main()
