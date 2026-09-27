# -*- coding: utf-8 -*-
"""Soát lô theo QUY CÁCH trước khi kết luận thuế phòng vệ thương mại.

pvtm_local.py là BẢN CHÉP luật của máy chủ (kiem_khop.py canh 0 lệch), nên không
sửa ở đó. Lớp này bọc ngoài kết quả của pvtm_local.tinh_cho_lo và thêm ba việc
mà luật gốc chưa làm:

1. Phạm vi theo quy cách: độ dày, chiều rộng, hàm lượng carbon, đường kính lõi,
   dạng (tấm/cuộn) đọc từ `quy_cach` của từng vụ. Lô nằm ngoài khoảng thì
   KHÔNG THUỘC PHẠM VI vụ đó.
2. Điều kiện đi kèm loại trừ mác thép (vd AD20 chỉ loại trừ thép DẠNG TẤM) và
   loại trừ theo quy cách (vd AC03.AD20: tấm dày từ 10 mm) — đọc từ
   data/dieu_kien_bo_sung.json (chép tay từ nguyên văn QĐ, dongbo không ghi đè).
3. Thiếu thông số quyết định thì kết luận CHƯA ĐỦ DỮ LIỆU, không đoán.
"""
import json
import os
import re

import pvtm_local as pl

TEP_BO_SUNG = os.path.join(pl.DATA, "dieu_kien_bo_sung.json")

# khóa lô -> tên quy cách (đã bỏ dấu) mang thông số đó, đơn vị in ra
THONG_SO = {
    "day": (("do day",), "mm", "Độ dày"),
    "rong": (("chieu rong", "be rong"), "mm", "Chiều rộng"),
    "carbon": (("ham luong carbon",), "%", "Hàm lượng carbon"),
    "loi": (("duong kinh loi",), "mm", "Đường kính lõi"),
}
TEN_DANG = {"tam": "tấm", "cuon": "cuộn"}
_DANG = {"tam": "tam", "tấm": "tam", "plate": "tam", "sheet": "tam",
         "cuon": "cuon", "cuộn": "cuon", "coil": "cuon"}

_SO = r"\d+(?:[.,]\d+)*"
_TOAN_TU = [  # dài trước ngắn, để "nho hon hoac bang" không bị bắt thành "nho hon"
    (r"lon hon hoac bang|khong nho hon|>=|≥", ">="),
    (r"nho hon hoac bang|khong qua|toi da|<=|≤", "<="),
    (r"lon hon|tren|>", ">"),
    (r"nho hon|duoi|<", "<"),
]


def doc_so(t):
    """'1.880' -> 1880 (chấm ngăn nghìn); '0,108' -> 0.108; '0.30' -> 0.3."""
    if "," in t:
        return float(t.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", t):
        return float(t.replace(".", ""))
    return float(t)


def khoang(text):
    """Chuỗi quy cách -> danh sách (toán tử, giá trị). Rỗng nếu không có số (vd 'Bất kể')."""
    t = pl.bo_dau(text)
    tol = 0.0
    m = re.search(r"dung sai\s*\+\s*/\s*-\s*(" + _SO + ")", t)
    if m:
        tol = doc_so(m.group(1))
        t = t[:m.start()]
    m = re.search(r"(?:tu\s*)?(" + _SO + r")\s*(?:mm|%)?\s*(?:den|–|-)\s*(" + _SO + ")", t)
    if m:
        return [(">=", doc_so(m.group(1)) - tol), ("<=", doc_so(m.group(2)) + tol)]
    m = re.search(r"tu\s*(" + _SO + r")\s*(?:mm|%)?\s*tro len", t)
    if m:
        return [(">=", doc_so(m.group(1)))]
    ds = []
    for mau, op in _TOAN_TU:
        for mm in re.finditer(r"(?:" + mau + r")\s*(" + _SO + ")", t):
            ds.append((op, doc_so(mm.group(1))))
        t = re.sub(r"(?:" + mau + r")\s*" + _SO, " ", t)   # đã đọc thì xóa, tránh bắt lại ở toán tử ngắn
    return ds


def dat(gia_tri, dieu_kien):
    so_sanh = {">=": gia_tri >= dieu_kien[1] - 1e-9, "<=": gia_tri <= dieu_kien[1] + 1e-9,
               ">": gia_tri > dieu_kien[1] + 1e-9, "<": gia_tri < dieu_kien[1] - 1e-9}
    return so_sanh[dieu_kien[0]]


def chuan_dang(v):
    if not v:
        return None
    d = _DANG.get(v.strip().lower()) or _DANG.get(pl.bo_dau(v.strip()))
    if not d:
        raise SystemExit(f"--dang phải là 'tam' (tấm) hoặc 'cuon' (cuộn), nhận '{v}'")
    return d


def _so_lo(lo, khoa):
    v = lo.get(khoa)
    return None if v in (None, "") else pl.so(v)


def doc_bo_sung():
    if not os.path.exists(TEP_BO_SUNG):
        return {}
    with open(TEP_BO_SUNG, encoding="utf-8") as f:
        return {k: v for k, v in json.load(f).items() if not k.startswith("_")}


def _dieu_kien_quy_cach(vu):
    """quy_cach của vụ -> {khóa lô: [(op, giá trị)]}, {khóa: chuỗi gốc}, danh sách quy cách chữ."""
    so, goc, chu = {}, {}, []
    for q in vu.get("quy_cach", []):
        ten = pl.bo_dau(q["ten"]).strip()
        if ten == "thanh phan loi":          # "C từ 0,04% đến 0,2%; P ≤ 0,03%; …" — chỉ đọc C
            for doan in q["gia_tri"].split(";"):
                if pl.bo_dau(doan).strip().startswith("c "):
                    so["carbon"], goc["carbon"] = khoang(doan.strip()[1:]), f"{q['ten']}: {doan.strip()}"
            chu.append(q)
            continue
        khoa = next((k for k, (ten_qc, _dv, _n) in THONG_SO.items() if ten in ten_qc), None)
        dk = khoang(q["gia_tri"]) if khoa else []
        if khoa and dk:
            so[khoa], goc[khoa] = dk, f"{q['ten']}: {q['gia_tri']}"
        else:
            chu.append(q)
    return so, goc, chu


def pham_vi(vu, lo):
    """-> (các bước, có quy cách nằm ngoài phạm vi?, thông số còn thiếu, quy cách chữ tự đối chiếu)."""
    can_cu = vu.get("so_hieu") or vu["ma_vu_viec"]
    so, goc, chu = _dieu_kien_quy_cach(vu)
    buoc, ngoai, thieu = [], False, []
    for khoa, dk in so.items():
        _t, dv, nhan = THONG_SO[khoa]
        v = _so_lo(lo, khoa)
        if v is None:
            thieu.append(nhan)
            continue
        ok = all(dat(v, d) for d in dk)
        ngoai |= not ok
        buoc.append({"buoc": f"Phạm vi — {nhan}", "ket_qua": f"lô {v:g} {dv}; QĐ: {goc[khoa]}",
                     "dat": ok, "can_cu": f"{can_cu} — mô tả hàng hóa"})
    dang = chuan_dang(lo.get("dang"))
    for q in chu:
        if pl.bo_dau(q["ten"]).strip() == "dang" and dang:
            ok = TEN_DANG[dang] in q["gia_tri"].lower()
            ngoai |= not ok
            buoc.append({"buoc": "Phạm vi — Dạng", "ket_qua": f"lô dạng {TEN_DANG[dang]}; QĐ: {q['gia_tri']}",
                         "dat": ok, "can_cu": f"{can_cu} — mô tả hàng hóa"})
    tu_doi_chieu = [f"{q['ten']}: {q['gia_tri']}" for q in chu if not (pl.bo_dau(q["ten"]).strip() == "dang" and dang)]
    return buoc, ngoai, thieu, tu_doi_chieu


NHAN_KHOA = {**{k: v[2] for k, v in THONG_SO.items()}, "dang": "Dạng (tấm/cuộn)"}


def _khop_dieu_kien(dk, lo):
    """Điều kiện loại trừ theo quy cách -> ('khop' | 'truot' | 'thieu', số điều kiện đã biết, khóa còn thiếu)."""
    biet, thieu = 0, []
    for khoa, yeu_cau in dk.items():
        v = chuan_dang(lo.get("dang")) if khoa == "dang" else _so_lo(lo, khoa)
        if v is None:
            thieu.append(khoa)
            continue
        biet += 1
        if not (v == yeu_cau if khoa == "dang" else dat(v, yeu_cau)):
            return "truot", biet, thieu
    return ("thieu" if thieu else "khop"), biet, thieu


def _mac_ke_thua(kho, ma_vu, lo):
    """Loại trừ mác thép kế thừa từ vụ khác (vd AC03.AD20 kế thừa danh mục của AD20)."""
    goc = next((v for v in kho["vu_viec"] if v["ma_vu_viec"] == ma_vu), None)
    mac = pl.chuan_mac_thep(lo.get("mac_thep"))
    if not goc or not mac:
        return None
    return next((x for x in goc.get("loai_tru", []) if x["kieu"] == "mac_thep"
                 and pl.chuan_mac_thep(x["mac_thep"]) == mac
                 and pl.khop_tieu_chuan(x["tieu_chuan"], lo.get("tieu_chuan"))), None)


def soat(kho, lo):
    """Như pvtm_local.tinh_cho_lo nhưng soát thêm quy cách. ket_luan thêm 2 giá trị:
    'khong_thuoc_pham_vi' (quy cách ngoài vụ) và 'chua_du' (thiếu thông số quyết định)."""
    r = pl.tinh_cho_lo(kho, lo)
    bs = doc_bo_sung()
    theo_ma = {v["ma_vu_viec"]: v for v in kho["vu_viec"]}
    dang = chuan_dang(lo.get("dang"))
    for k in r["vu_viec"]:
        vu, them = theo_ma[k["ma_vu_viec"]], bs.get(k["ma_vu_viec"], {})
        buoc_pv, ngoai, thieu, tu_dc = pham_vi(vu, lo)
        k["tu_doi_chieu"] = tu_dc + [x["noi_dung"] for x in vu.get("loai_tru", [])
                                     if x["kieu"] in ("mo_ta", "vu_khac") and x.get("noi_dung")]
        k["thieu"] = thieu
        # pvtm_local chỉ đếm "Đối chiếu N trường hợp loại trừ…"; ở đây đã liệt kê đủ trong tu_doi_chieu
        k["canh_bao"] = [c for c in k["canh_bao"] if not c.startswith("Đối chiếu ")]
        if ngoai:
            k.update(cac_buoc=buoc_pv, ket_luan="khong_thuoc_pham_vi", muc_thue=0.0)
            continue

        # Loại trừ theo quy cách (bảng bổ sung)
        cho_du, lt_khop, quyet_dinh = [], None, []
        for lt in them.get("loai_tru_quy_cach", []):
            khop, biet, con_thieu = _khop_dieu_kien(lt["dieu_kien"], lo)
            if khop == "khop":
                lt_khop = lt
                break
            if khop == "thieu":
                cho_du.append(lt)
                if biet:   # đã khớp phần biết được, chỉ còn thiếu -> thông số đó QUYẾT ĐỊNH kết luận
                    quyet_dinh.append((lt, con_thieu))
        if lt_khop:
            k.update(cac_buoc=buoc_pv + [{"buoc": "Loại trừ theo quy cách", "ket_qua": lt_khop["trich"],
                                          "dat": True, "can_cu": lt_khop["can_cu"]}],
                     ket_luan="khong_ap", muc_thue=0.0)
            continue

        # Loại trừ mác thép: điều kiện đi kèm
        lm = them.get("loai_tru_mac_thep", {})
        loai_tru_mac = next((b for b in k["cac_buoc"] if b["buoc"] == "Loại trừ mác thép" and b["dat"]), None)
        ke_thua = _mac_ke_thua(kho, lm["ke_thua_tu"], lo) if lm.get("ke_thua_tu") and not loai_tru_mac else None
        if loai_tru_mac or ke_thua:
            if lm.get("chi_khi_dang"):
                can = TEN_DANG[lm["chi_khi_dang"]]
                if dang is None:
                    k.update(ket_luan="chua_du", muc_thue=None)
                    k["cac_buoc"] = buoc_pv + k["cac_buoc"] + [{
                        "buoc": "Điều kiện loại trừ mác thép", "dat": None, "can_cu": lm["can_cu"],
                        "ket_qua": f"chỉ áp dụng cho hàng dạng {can} — chưa nhập --dang"}]
                    k["thieu"] = thieu + ["Dạng (tấm/cuộn)"]
                    continue
                if dang != lm["chi_khi_dang"]:
                    lai = pl.tinh_muc_thue(vu, {**lo, "code": r["code"], "mac_thep": None}).dict()
                    k.update(ket_luan=lai["ket_luan"], muc_thue=lai["muc_thue"], nha_sx_khop=lai["nha_sx_khop"])
                    k["canh_bao"] = lai["canh_bao"]
                    k["cac_buoc"] = buoc_pv + [{
                        "buoc": "Loại trừ mác thép", "dat": False, "can_cu": lm["can_cu"],
                        "ket_qua": f"chỉ loại trừ hàng dạng {can}; lô dạng {TEN_DANG[dang]}"}] + lai["cac_buoc"]
                    _ghi_thieu(k, thieu)
                    continue
                buoc_dang = {"buoc": "Điều kiện loại trừ mác thép", "dat": True, "can_cu": lm["can_cu"],
                             "ket_qua": f"hàng dạng {can}"}
            else:
                buoc_dang = None
            if ke_thua:
                k.update(ket_luan="khong_ap", muc_thue=0.0)
                k["cac_buoc"] = [{"buoc": "Loại trừ mác thép", "dat": True, "can_cu": lm["can_cu"],
                                  "ket_qua": f"{ke_thua['mac_thep']} theo {ke_thua['tieu_chuan']} "
                                             f"(danh mục loại trừ của {lm['ke_thua_tu']})"}]
            k["cac_buoc"] = buoc_pv + k["cac_buoc"] + ([buoc_dang] if buoc_dang else [])
            if lm.get("ho_so"):
                k["canh_bao"].append(f"Hồ sơ để được loại trừ ({lm['can_cu']}): {lm['ho_so']}")
            _ghi_thieu(k, thieu)
            continue

        k["cac_buoc"] = buoc_pv + k["cac_buoc"]
        if quyet_dinh and k["ket_luan"] == "ap":
            lt, con_thieu = quyet_dinh[0]
            k.update(ket_luan="chua_du", muc_thue=None)
            k["cac_buoc"].append({"buoc": "Loại trừ theo quy cách", "dat": None, "can_cu": lt["can_cu"],
                                  "ket_qua": f"{lt['trich']} — thiếu " + ", ".join(NHAN_KHOA[x] for x in con_thieu)})
            k["thieu"] = thieu + [NHAN_KHOA[x] for x in con_thieu]
            continue
        for lt in cho_du:
            k["canh_bao"].append(f"Có thể được loại trừ nếu: {lt['trich']} ({lt['can_cu']}) — nhập đủ quy cách để xét.")
        _ghi_thieu(k, thieu)
    r["bi_ap"] = any(k["ket_luan"] == "ap" for k in r["vu_viec"])
    r["chua_du"] = any(k["ket_luan"] == "chua_du" for k in r["vu_viec"])
    return r


def _ghi_thieu(k, thieu):
    if thieu and k["ket_luan"] == "ap":
        k["canh_bao"].append("Chưa nhập " + ", ".join(thieu) + " — kết luận ÁP đang GIẢ ĐỊNH lô nằm trong "
                             "phạm vi quy cách của vụ.")
