# -*- coding: utf-8 -*-
"""So luật tính thuế CBPG trên máy (pvtm_local.py) với máy chủ ILMSv2.

pvtm_local.py là BẢN CHÉP luật của ILMS. Script này dựng mọi kiểu lô từ dữ
liệu đã đồng bộ (không C/O, C/O từng nước, nước không bị áp, từng nhà SX tự
xuất, từng công ty TM, nhà XK sai, mác thép loại trừ đúng/sai tiêu chuẩn, mã
HS loại trừ), gọi CẢ HAI bên rồi so kết luận, mức thuế, từng bước, cảnh báo.
Kèm tiêu đề hồ sơ từng vụ (`tieu_de`, theo Mô tả hàng hóa), và PHIẾU KIỂM TRA DÒNG HÀNG (lệnh `kiemtra`,
bản chép kiem_tra_dong_local.py) so nguyên phiếu với POST /api/tracuu/kiem-tra trên các dòng mẫu DONG_MAU.

Chạy sau mỗi lần `dongbo` hoặc khi ILMS đổi luật:
    python scripts/kiem_khop.py
Cần ILMS_URL + ILMS_USER/ILMS_PASS. Lệch dù một lô là thoát mã 1.
"""
import json
import os
import sys
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ilms_api  # noqa: E402
import pvtm_local as pl  # noqa: E402

TRUONG = ("ma_vu_viec", "ket_luan", "muc_thue", "cac_buoc", "canh_bao", "nha_sx_khop", "thieu", "tu_doi_chieu")


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
    # Soát quy cách (ILMS phase138): mỗi ô quy cách vụ dùng — thiếu, trong và ngoài khoảng; dạng tấm/cuộn
    mac = next(((x["mac_thep"], x["tieu_chuan"]) for x in vu["loai_tru"] if x["kieu"] == "mac_thep"), None)
    for dang in (None, "tam", "cuon"):
        for day, rong, carbon, loi in ((None,) * 4, (8, 1500, 0.2, 1.2), (12, 2000, 0.35, 4.3)):
            q = {"code": code, "nuoc_co": nuoc, "dang": dang, "day": day, "rong": rong, "carbon": carbon, "loi": loi}
            lo.append(q)
            if mac:
                lo.append({**q, "mac_thep": mac[0], "tieu_chuan": mac[1]})
    return lo


def rut(kq):
    # Thứ tự các vụ không phải luật (ILMS không chốt thứ tự khi trùng ngày hiệu lực) -> so theo mã vụ.
    # Qua JSON như đường mạng: bên máy giữ tuple (vd pham_vi.dk), bên ILMS là list — cùng giá trị, không phải lệch.
    kq = json.loads(json.dumps(kq))
    return sorted(({k: v[k] for k in TRUONG} for v in kq["vu_viec"]), key=lambda v: v["ma_vu_viec"])


QUY_CACH = ("day", "rong", "carbon", "loi", "dang")


def chay(in_chi_tiet=True):
    """So mọi lô dựng từ dữ liệu trên máy + tiêu đề từng vụ. Trả (số lô, số lệch)."""
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
                                                        "tieu_chuan": lo.get("tieu_chuan"),
                                                        **{k: lo[k] for k in QUY_CACH if lo.get(k) is not None}}))
            for a in (may, chu):
                for v in a:
                    v["muc_thue"] = None if v["muc_thue"] is None else round(float(v["muc_thue"]), 4)
            if may != chu:
                lech += 1
                if in_chi_tiet:
                    print(f"LỆCH [{vu['ma_vu_viec']}] lô {lo}")
                    print(f"  máy : {may}")
                    print(f"  ILMS: {chu}")
    for vu in kho["vu_viec"]:
        may = pl.tieu_de(vu["mo_ta"], vu["ten_hang"])
        chu = ilms_api.get(f"/pvtm/vu-viec/{urllib.parse.quote(vu['ma_vu_viec'], safe='')}").get("tieu_de")
        if may != chu:
            lech += 1
            if in_chi_tiet:
                print(f"LỆCH tiêu đề [{vu['ma_vu_viec']}]")
                print(f"  máy : {may}")
                print(f"  ILMS: {chu}")
    return so_lo + len(kho["vu_viec"]), lech


# Dòng hàng mẫu cho phiếu kiểm tra: hợp kim ngoài phạm vi, không hợp kim trong phạm vi, khai lệch, không gỉ, ngoài thép.
DONG_MAU = [
    {"ma": "72254090", "nuoc": "CN", "thue_suat": "0", "mo_ta": "Thép tấm hợp kim crom được cán phẳng, chưa được gia "
     "công quá mức cán nóng, chứa C=0.07%-> 0.09% Cr= 0.49%->0.52%,KT: 40x2440x5729mm,TC: ASTM A709-2024,Mác: A709Gr50W"},
    {"ma": "72085100", "nuoc": "CN", "thue_suat": "0", "mo_ta": "Thép tấm không hợp kim cán nóng, C 0.18%, 12 x 1500 x 6000mm"},
    {"ma": "72085100", "nuoc": "Trung Quốc", "thue_suat": "5%", "mo_ta": "Thép tấm cán nóng, Cr 0.4%, KT: 20x2000x6000mm"},
    {"ma": "72192200", "nuoc": "KR", "mo_ta": "Thép không gỉ cán nóng dạng tấm, Cr 18%, C 0.05%, 6 x 1500 mm"},
    {"ma": "72103011", "nuoc": "CN", "mo_ta": "Tôn mạ kẽm 0,5 x 1200 x C"},
    {"ma": "84713020", "nuoc": "CN", "thue_suat": "0", "mo_ta": "Máy tính xách tay"},
]


def chay_phieu(in_chi_tiet=True):
    """So phiếu kiểm tra dòng hàng trên máy với ILMS. Trả (số dòng, số lệch); dòng mã máy không có thì bỏ qua."""
    import kiem_tra_in as ki
    with open(os.path.join(ki.DATA, "hs_tree.json"), encoding="utf-8") as f:
        codes = json.load(f).get("codes", {})
    kho = pl.doc_kho()
    so = lech = 0
    for d in DONG_MAU:
        if d["ma"] not in codes:
            continue
        so += 1
        may = json.loads(json.dumps(ki.kiem_tra(dict(d), codes, kho)))   # tuple -> list như JSON của ILMS
        chu = ilms_api.post("/kiem-tra", d)
        if may != chu:
            lech += 1
            if in_chi_tiet:
                print(f"LỆCH phiếu {d['ma']} ({d['mo_ta'][:40]}…)")
                for k in sorted(set(may) | set(chu)):
                    if may.get(k) != chu.get(k):
                        print(f"  [{k}] máy : {may.get(k)}")
                        print(f"  [{k}] ILMS: {chu.get(k)}")
    return so, lech


def main():
    if not ilms_api.bat():
        raise SystemExit("Cần ILMS_URL + ILMS_USER/ILMS_PASS để so với máy chủ.")
    so, lech = chay()
    print(f"{so} lô + tiêu đề, {lech} lệch.")
    so_p, lech_p = chay_phieu()
    print(f"{so_p} phiếu kiểm tra dòng hàng, {lech_p} lệch.")
    lech += lech_p
    sys.exit(1 if lech else 0)


if __name__ == "__main__":
    main()
