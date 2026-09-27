# -*- coding: utf-8 -*-
"""So luật tính thuế CBPG trên máy (pvtm_local.py) với máy chủ ILMSv2.

pvtm_local.py là BẢN CHÉP luật của ILMS. Script này dựng mọi kiểu lô từ dữ
liệu đã đồng bộ (không C/O, C/O từng nước, nước không bị áp, từng nhà SX tự
xuất, từng công ty TM, nhà XK sai, mác thép loại trừ đúng/sai tiêu chuẩn, mã
HS loại trừ), gọi CẢ HAI bên rồi so kết luận, mức thuế, từng bước, cảnh báo.

Chạy sau mỗi lần `dongbo` hoặc khi ILMS đổi luật:
    python scripts/kiem_khop.py
Cần ILMS_URL + ILMS_USER/ILMS_PASS. Lệch dù một lô là thoát mã 1.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ilms_api  # noqa: E402
import pvtm_local as pl  # noqa: E402

TRUONG = ("ma_vu_viec", "ket_luan", "muc_thue", "cac_buoc", "canh_bao", "nha_sx_khop")


def cac_lo(vu):
    code = vu["ma_hs"][0]
    lo = [{"code": code}, {"code": code, "nuoc_co": "VN"}]
    for n in vu["nuoc"]:
        lo.append({"code": code, "nuoc_co": n["nuoc"]})
        lo.append({"code": code, "nuoc_co": n["nuoc"], "nha_sx": "Cong ty khong co ten", "nha_xk": "X"})
    for s in vu["nha_sx"]:
        lo.append({"code": code, "nuoc_co": s["nuoc"], "nha_sx": s["ten"], "nha_xk": s["ten"]})
        lo.append({"code": code, "nuoc_co": s["nuoc"], "nha_sx": s["ten"], "nha_xk": "Nha XK la"})
        for c in s["cong_ty_tm"][:2]:
            lo.append({"code": code, "nuoc_co": s["nuoc"], "nha_sx": s["ten"], "nha_xk": c})
    nuoc = vu["nuoc"][0]["nuoc"] if vu["nuoc"] else "CN"
    for x in vu["loai_tru"]:
        if x["kieu"] == "mac_thep":
            lo.append({"code": code, "nuoc_co": nuoc, "mac_thep": x["mac_thep"], "tieu_chuan": x["tieu_chuan"]})
            lo.append({"code": code, "nuoc_co": nuoc, "mac_thep": x["mac_thep"], "tieu_chuan": "TC khac"})
        elif x["kieu"] == "ma_hs" and pl.ma_hs_8(x.get("ma_hs")):
            lo.append({"code": pl.ma_hs_8(x["ma_hs"]), "nuoc_co": nuoc})
    return lo


def rut(kq):
    # Thứ tự các vụ không phải luật (ILMS không chốt thứ tự khi trùng ngày hiệu lực) -> so theo mã vụ.
    return sorted(({k: v[k] for k in TRUONG} for v in kq["vu_viec"]), key=lambda v: v["ma_vu_viec"])


def main():
    if not ilms_api.bat():
        raise SystemExit("Cần ILMS_URL + ILMS_USER/ILMS_PASS để so với máy chủ.")
    kho = pl.doc_kho()
    so_lo = lech = 0
    da_thu = set()
    for vu in kho["vu_viec"]:
        for lo in cac_lo(vu):
            khoa = tuple(sorted(lo.items()))
            if khoa in da_thu:
                continue
            da_thu.add(khoa)
            so_lo += 1
            may = rut(pl.tinh_cho_lo(kho, lo))
            chu = rut(ilms_api.post("/pvtm/tinh-thue", {"code": lo["code"], "nuoc_co": lo.get("nuoc_co"),
                                                        "nha_sx": lo.get("nha_sx"), "nha_xk": lo.get("nha_xk"),
                                                        "mac_thep": lo.get("mac_thep"),
                                                        "tieu_chuan": lo.get("tieu_chuan")}))
            for a in (may, chu):
                for v in a:
                    v["muc_thue"] = None if v["muc_thue"] is None else round(float(v["muc_thue"]), 4)
            if may != chu:
                lech += 1
                print(f"LỆCH [{vu['ma_vu_viec']}] lô {lo}")
                print(f"  máy : {may}")
                print(f"  ILMS: {chu}")
    print(f"{so_lo} lô, {lech} lệch.")
    sys.exit(1 if lech else 0)


if __name__ == "__main__":
    main()
