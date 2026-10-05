# -*- coding: utf-8 -*-
"""Gợi ý mã HS từ TÊN HÀNG theo 6 Quy tắc tổng quát (GRI) — lệnh `query_hs.py phanloai`.

Máy chỉ làm phần cơ học: tách tên hàng, tìm mã ứng viên trong Biểu thuế, gom theo nhóm 4 số,
rồi trình bày từng quy tắc với căn cứ đọc được (mô tả nhóm, Chú giải Chương, câu loại trừ).
Phần quyết định (bản chất, thành phần, đặc trưng cơ bản) máy KHÔNG đoán — in thành câu hỏi.

Luật xếp hạng từ khóa viết MỘT chỗ: `query_hs.xep_hang` (dùng chung với lệnh `search`).
"""
import json
import os
import re

import query_hs as q

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Từ không mang nghĩa phân loại (so sau khi bỏ dấu).
TU_BO = {"hang", "moi", "100", "loai", "dung", "cho", "cua", "va", "cac", "bang", "co", "la", "theo", "de",
         "san", "pham", "tren", "duoi", "trong", "ngoai", "chiec", "cai", "bo", "kg", "mm", "cm",
         "m", "inch", "pcs", "set", "kich", "thuoc", "quy", "cach", "duong", "kinh", "luong", "chieu", "dai",
         "rong", "day"}

# Phần KHÔNG dùng để phân loại (GRI 1 chỉ xét bản chất hàng): nhãn hiệu, model, xuất xứ, tình trạng mới.
# "hiệu"/"model" chỉ coi là nhãn hiệu khi đứng trước tên viết hoa hoặc có số ("hiệu POSCO", "model X1") — để không
# cắt nhầm "tín hiệu radio", "ký hiệu". Các từ khóa còn lại (xuất xứ, nsx, made in…) không nhập nhằng, cắt tới dấu phẩy.
_MAU_BO = re.compile(
    r"(?<!\w)(?:nhãn hiệu|nhan hieu|hiệu|hieu|thương hiệu|thuong hieu|brand|model|mã sp|ma sp|part no\.?|p/n)"
    r"\s*[:：]?\s*(?=[A-Z0-9])[^,;.()]*"
    r"|(?<!\w)(?:xuất xứ|xuat xu|nsx|nhà sản xuất|nha san xuat|hãng sx|hang sx|made in)\s*[:：]?\s*[^,;.()]*",
    re.IGNORECASE)
_MAU_MOI = re.compile(r"(?:hàng|hang)?\s*mới\s*100\s*%|(?:hang)?\s*moi\s*100\s*%|hàng mới|hang moi|new\s*100\s*%",
                      re.IGNORECASE)
# Thông số kỹ thuật (độ dày, kích thước, hàm lượng…) — in riêng để người dùng đối chiếu, không dùng tìm từ.
_MAU_THONG_SO = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:mm|cm|m|kg|g|%|inch|\"|x\s*\d+(?:[.,]\d+)?)\b"
                           r"(?:\s*x\s*\d+(?:[.,]\d+)?\s*(?:mm|cm|m)?)*", re.IGNORECASE)

# Dấu hiệu trong tên hàng kéo theo quy tắc nào (so không dấu). Chỉ là dấu hiệu — người dùng tự xác nhận.
DAU_HIEU = {
    "2(a)": ("chưa hoàn chỉnh / chưa lắp ráp / tháo rời",
             ["chua lap rap", "thao roi", "dang roi", "chua hoan chinh", "chua hoan thien", "ban thanh pham",
              "dang ckd", "dang skd", "ckd", "skd", "linh kien dong bo", "dang phoi"]),
    "2(b)": ("hỗn hợp / kết hợp nhiều chất liệu",
             ["hon hop", "pha tron", "phoi tron", "ket hop", "co pha", "tron lan", "da pha"]),
    "3":    ("bộ / nhiều mặt hàng đóng chung",
             ["bo san pham", "bo gom", "bao gom", "kem theo", "combo", "kit", "dong bo", "tron bo"]),
    "5":    ("hộp / bao bì đi kèm",
             ["hop dung", "bao dung", "vo hop", "kem hop", "tui dung", "bao bi", "hop qua", "vali dung"]),
}

# Câu trong Chú giải Chương có các cụm này là câu LOẠI TRỪ — đem ra soát khi câu nhắc tới từ của tên hàng.
_CUM_LOAI_TRU = ("không bao gồm", "loại trừ", "không áp dụng", "không thuộc", "trừ các", "trừ loại")


def tach_ten(ten):
    """Tách tên hàng khai báo → {'tu': từ phân loại, 'bo_qua': phần bỏ, 'thong_so': [...], 'dau_hieu': {qt: cụm}}.

    Bỏ nhãn hiệu/model/xuất xứ/"mới 100%" (không phải yếu tố phân loại theo GRI 1); giữ thông số kỹ thuật
    riêng; thay từ thương mại bằng từ của Biểu thuế (hx.doi_dong_nghia — cùng luật và cùng bảng với ILMS).
    """
    goc = ten.strip()
    bo_qua = [m.group(0).strip(" ,;:") for m in _MAU_BO.finditer(goc)] + \
             [m.group(0).strip() for m in _MAU_MOI.finditer(goc)]
    con = _MAU_MOI.sub(" ", _MAU_BO.sub(" ", goc))
    thong_so = [m.group(0).strip() for m in _MAU_THONG_SO.finditer(con)]
    con = _MAU_THONG_SO.sub(" ", con)
    doi, da_thay = q.hx.doi_dong_nghia(con)
    khong_dau = " ".join(q._tu(doi))
    dau_hieu = {}
    for qt, (_ten, cum) in DAU_HIEU.items():
        trung = [c for c in cum if re.search(rf"\b{re.escape(c)}\b", khong_dau)]
        if trung:
            dau_hieu[qt] = trung
    tu = [t for t in dict.fromkeys(khong_dau.split()) if t not in TU_BO and not t.isdigit()]
    return {"goc": goc, "tu": tu, "bo_qua": [b for b in bo_qua if b], "thong_so": thong_so,
            "dau_hieu": dau_hieu, "dong_nghia": da_thay}


def _cau(vb):
    vb = re.sub(r"\s+", " ", vb or "")
    return [c.strip() for c in re.split(r"(?<=[.;:])\s+", vb) if c.strip()]


def cau_loai_tru(chu_giai, tu):
    """Câu loại trừ trong Chú giải Chương có nhắc tới ít nhất một từ của tên hàng (từ ≥ 3 ký tự)."""
    tu = [t for t in tu if len(t) >= 3]
    ra = []
    for c in _cau(chu_giai):
        c_kd = q.strip_accents(c)
        if any(k in c_kd for k in map(q.strip_accents, _CUM_LOAI_TRU)) and any(t in c_kd for t in tu):
            ra.append(c if len(c) <= 260 else c[:257] + "...")
    return ra


def gom_nhom(kq, toi_da=3):
    """[(nhom4, diem_cao_nhat, [dong…])] từ kết quả `xep_hang`, giữ `toi_da` nhóm điểm cao nhất."""
    theo = {}
    for d, code, e, du in kq:
        theo.setdefault(code[:4], []).append((d, code, e, du))
    ds = [(n, max(r[0] for r in rows), rows) for n, rows in theo.items()]
    ds.sort(key=lambda x: (-x[1], x[0]))
    return ds[:toi_da]


def nhom_lan_can(tat_ca, da_chon, tu, codes, toi_da=3):
    """Nhóm 4 số KHÁC các nhóm đã chọn nhưng mô tả NHÓM (dòng 4 số) chứa ≥ 1 cụm 2 từ liền của tên hàng —
    nhóm cạnh tranh thật sự, phải đọc loại trừ ở cả hai đầu. Từ rời rạc trùng không tính (quá nhiễu)."""
    if len(tu) < 2:
        return []
    ra = []
    for d, code, e, _du in tat_ca:
        n = code[:4]
        if n in da_chon or any(n == x["nhom"] for x in ra):
            continue
        mo_ta = q.mo_ta_nhom(codes, n) or e.get("desc_vn", "")
        # Cần ≥ 2 cụm liền (hoặc cụm duy nhất) trong mô tả nhóm, không tính cặp toàn từ chung ("xu ly", "tu dong").
        if q.dem_cum_lien(tu, " ".join(q._tu(mo_ta)), bo_chung=True) >= min(2, len(tu) - 1):
            ra.append({"nhom": n, "diem": round(d, 1), "mo_ta": mo_ta})
            if len(ra) >= toi_da:
                break
    return ra


def duoi(desc, nhom_desc):
    """Phần mô tả riêng của mã con, bỏ phần lặp lại mô tả nhóm ("… - - Dạng thanh và que…" → "Dạng thanh và que…")."""
    if nhom_desc and desc.startswith(nhom_desc):
        desc = desc[len(nhom_desc):]
    return desc.strip(" -:") or desc


def diem_phan_biet(codes, nhom, ung_vien):
    """Đoạn mô tả CUỐI (sau dấu "- - -" sau cùng) của từng mã 8 số ứng viên — nguyên văn Biểu thuế, là chỗ
    phân biệt mã con với nhau (GRI 6). Không tự đặt lời."""
    ma8 = [c for c in ung_vien if len(c) == 8]
    if len(ma8) < 2:   # một mã khớp vẫn phải so với các mã anh em cùng nhóm
        ma8 = sorted(c for c in codes if c.startswith(nhom) and len(c) == 8)
    if len(ma8) < 2:
        return []
    ra = []
    for c in ma8:
        cuoi = q.doan(codes[c].get("desc_vn", ""))[-1]
        if cuoi and cuoi not in ra:
            ra.append(cuoi)
    return ra[:8]


def phan_loai(ten, codes, chapters=None, headings=None, chuong=None, toi_da_nhom=3, toi_da_ma=8,
              tien_le_ds=None, bo_tien_le_id=None):
    """Kết quả có cấu trúc (in ra hoặc xuất JSON). Không đọc tệp — để test không cần dữ liệu thật."""
    chapters = chapters or {}
    headings = headings or {}
    t = tach_ten(ten)
    tu_khoa = " ".join(t["tu"])
    # Chương 98 (mã riêng hưởng ưu đãi của Biểu thuế VN) chỉ áp SAU khi đã phân loại vào Chương 1-97
    # theo GRI — không phải nhóm cạnh tranh, bỏ khỏi ứng viên trừ khi người dùng chỉ định --chuong 98.
    if str(chuong or "") != "98":
        codes = {c: e for c, e in codes.items() if not c.startswith("98")}
    tat_ca = q.xep_hang(codes, tu_khoa, chuong, noi_long=True, tien_le_ds=tien_le_ds,
                        bo_tien_le_id=bo_tien_le_id, ten_goc=ten) if tu_khoa else []
    kq = q.loc_du_tu(tat_ca)
    nhom_ds = gom_nhom(kq, toi_da_nhom)
    du_tu = bool(kq) and kq[0][3]
    ra = {"ten": t, "tu_khoa": tu_khoa, "nhom": [], "gri": {}, "cau_hoi": [], "do_tin_cay": "thấp",
          "lan_can": nhom_lan_can(tat_ca, [n for n, _d, _r in nhom_ds], t["tu"], codes)}

    # GRI 1 — từng nhóm ứng viên: mô tả nhóm + Chú giải Chương + câu loại trừ cần soát
    for nhom, diem, rows in nhom_ds:
        ch = str(int(nhom[:2]))
        cg = chapters.get(ch, "")
        ung = [r[1] for r in rows][:toi_da_ma]
        ra["nhom"].append({
            "nhom": nhom, "diem": round(diem, 1), "mo_ta": q.mo_ta_nhom(codes, nhom),
            "chuong": ch, "co_chu_giai_chuong": bool(cg), "co_chu_giai_nhom": nhom in headings,
            "loai_tru": cau_loai_tru(cg, t["tu"]),
            "ma": [{"ma": r[1], "diem": round(r[0], 1), "mfn": r[2].get("mfn", ""),
                    "mo_ta": duoi(r[2].get("desc_vn", ""), q.mo_ta_nhom(codes, nhom))}
                   for r in rows[:toi_da_ma]],
            "phan_biet": diem_phan_biet(codes, nhom, ung),
        })

    # GRI 2 / 5 — chỉ theo dấu hiệu trong tên hàng
    for qt in ("2(a)", "2(b)", "5"):
        if qt in t["dau_hieu"]:
            ra["gri"][qt] = {"ten": DAU_HIEU[qt][0], "dau_hieu": t["dau_hieu"][qt]}

    # GRI 3 — nhiều nhóm cùng có thể áp dụng
    if len(nhom_ds) > 1 or "3" in t["dau_hieu"]:
        d0 = nhom_ds[0][1] if nhom_ds else 0
        gan = [n for n, d, _r in nhom_ds if d0 - d <= 15]
        ra["gri"]["3"] = {
            "dau_hieu": t["dau_hieu"].get("3", []),
            "3a_nhom_cu_the_hon": nhom_ds[0][0] if nhom_ds and len(gan) == 1 else None,
            "3a_chua_tach_duoc": gan if len(gan) > 1 else [],
            "3c_nhom_cuoi_cung": max(gan) if len(gan) > 1 else None,
        }
    # GRI 4 — không có mã nào khớp
    if not kq:
        ra["gri"]["4"] = True

    # Độ tin cậy: chỉ phản ánh mức khớp từ, không phải kết luận pháp lý
    if kq and du_tu and len(nhom_ds) == 1:
        ra["do_tin_cay"] = "khá"
    elif kq and du_tu:
        ra["do_tin_cay"] = "trung bình"

    # Câu hỏi cho người dùng — máy không tự trả lời
    if not du_tu:
        ra["cau_hoi"].append("Tên hàng chưa khớp đủ từ nào trong Biểu thuế: cho biết bản chất hàng (vật liệu, "
                             "công dụng, mức gia công) bằng từ ngữ của Biểu thuế.")
    if ra["gri"].get("3", {}).get("3a_chua_tach_duoc"):
        ra["cau_hoi"].append("Hàng có thể thuộc nhiều nhóm — cho biết thành phần/bộ phận nào tạo nên ĐẶC TRƯNG "
                             "CƠ BẢN của hàng (GRI 3(b)) trước khi dùng 3(c).")
    if "2(a)" in t["dau_hieu"]:
        ra["cau_hoi"].append("Hàng chưa hoàn chỉnh/tháo rời: khi nhập đã có đặc trưng cơ bản của hàng hoàn chỉnh "
                             "chưa? (GRI 2(a))")
    if "2(b)" in t["dau_hieu"]:
        ra["cau_hoi"].append("Hàng hỗn hợp: tỷ lệ từng chất liệu/thành phần là bao nhiêu? (GRI 2(b) → 3)")
    if "5" in t["dau_hieu"]:
        ra["cau_hoi"].append("Bao bì/hộp đi kèm: có thiết kế riêng cho hàng và dùng lâu dài không? "
                             "Có phải loại tái sử dụng độc lập không? (GRI 5(a)/(b))")
    for n in ra["nhom"][:1]:
        if n["phan_biet"]:
            ra["cau_hoi"].append(f"Để tách mã con trong nhóm {n['nhom']} (GRI 6), hàng thuộc dòng nào: "
                                 + " | ".join(n["phan_biet"]) + "?")
        if not n["co_chu_giai_nhom"]:
            ra["cau_hoi"].append(f"Chưa nạp Chú giải chi tiết nhóm {n['nhom']} — đọc Chú giải nhóm (EN/HS) "
                                 f"trước khi kết luận.")
    return ra


def in_ket_qua(r, codes):
    t = r["ten"]
    print(f"=== PHÂN LOẠI THEO 6 QUY TẮC GRI — '{t['goc']}' (CHỈ LÀ GỢI Ý, người có thẩm quyền kết luận) ===")
    print(f"Từ dùng phân loại: {' '.join(t['tu']) or '(không còn từ nào)'}")
    if t["dong_nghia"]:
        print("  Thay từ thương mại → từ Biểu thuế: " + "; ".join(f"{a} → {b}" for a, b in t["dong_nghia"].items()))
    if t["bo_qua"]:
        print("  Bỏ qua (không phải yếu tố phân loại): " + "; ".join(t["bo_qua"]))
    if t["thong_so"]:
        print("  Thông số để đối chiếu Chú giải/mã con: " + "; ".join(t["thong_so"]))

    print("\n[QT 1] Căn cứ nội dung nhóm và Chú giải Phần/Chương:")
    if not r["nhom"]:
        print("  Không có nhóm nào khớp từ khóa.")
    for i, n in enumerate(r["nhom"], 1):
        print(f"  {i}. Nhóm {n['nhom']} (điểm {n['diem']}): {n['mo_ta'][:140]}")
        cg = "có" if n["co_chu_giai_chuong"] else "CHƯA NẠP"
        cn = "có" if n["co_chu_giai_nhom"] else "chưa nạp"
        print(f"     Chú giải Chương {n['chuong']}: {cg} (xem `chapter {n['chuong']}`) · Chú giải nhóm: {cn}")
        for c in n["loai_tru"][:4]:
            print(f"     ⚠ Câu loại trừ cần soát: {c}")
    for lc in r.get("lan_can", []):
        print(f"  ~ Nhóm cạnh tranh {lc['nhom']}: {lc['mo_ta'][:120]} — đọc Chú giải loại trừ ở CẢ hai đầu.")
    for qt in ("2(a)", "2(b)"):
        if qt in r["gri"]:
            print(f"\n[QT {qt}] Dấu hiệu '{r['gri'][qt]['ten']}': {', '.join(r['gri'][qt]['dau_hieu'])} → "
                  f"soát theo QT {qt} (xem `gri 2`).")
    if "3" in r["gri"]:
        g = r["gri"]["3"]
        print("\n[QT 3] Nhiều nhóm có thể áp dụng:")
        if g["dau_hieu"]:
            print(f"  Dấu hiệu bộ/đóng chung: {', '.join(g['dau_hieu'])}")
        if g["3a_nhom_cu_the_hon"]:
            print(f"  3(a) Nhóm có mô tả cụ thể hơn (khớp từ sát nhất): {g['3a_nhom_cu_the_hon']} — "
                  f"các nhóm còn lại kém xa về mức khớp.")
        if g["3a_chua_tach_duoc"]:
            print(f"  3(a) Máy CHƯA tách được giữa các nhóm {', '.join(g['3a_chua_tach_duoc'])} (mức khớp sát nhau).")
            print("  3(b) Cần xác định đặc trưng cơ bản (thành phần/bộ phận/công dụng chính) — hỏi người dùng.")
            print(f"  3(c) CHỈ KHI 3(a), 3(b) không giải quyết được: nhóm có số thứ tự sau cùng = {g['3c_nhom_cuoi_cung']}.")
    if r["gri"].get("4"):
        print("\n[QT 4] Không nhóm nào khớp — phải tìm hàng GIỐNG NHẤT về bản chất; cần người dùng mô tả lại.")
    if "5" in r["gri"]:
        print(f"\n[QT 5] Dấu hiệu bao bì/hộp: {', '.join(r['gri']['5']['dau_hieu'])} → soát QT 5(a)/(b) (xem `gri 5`).")

    if r["nhom"]:
        n = r["nhom"][0]
        print(f"\n[QT 6] Phân nhóm trong nhóm {n['nhom']} (so cùng cấp: 6 số với 6 số, 8 số với 8 số):")
        khop8 = {m["ma"]: m for m in n["ma"] if len(m["ma"]) == 8}
        khop6 = {m[:6] for m in khop8}
        # In MỌI phân nhóm 6 số của nhóm để so cùng cấp (★ = có mã khớp); mã 8 số chỉ in dòng khớp.
        for pn6 in sorted({c[:6] for c in codes if c.startswith(n["nhom"]) and len(c) >= 6})[:14]:
            mo_ta6 = codes.get(pn6, {}).get("desc_vn", "") or next(
                (codes[c].get("desc_vn", "") for c in khop8 if c.startswith(pn6)), "")
            dau = "★" if pn6 in khop6 else " "
            print(f"  {dau} {q._ma(pn6)}  {duoi(mo_ta6, n['mo_ta'])[:110]}")
            for ma8, m in sorted(khop8.items()):
                if ma8.startswith(pn6):
                    print(f"        {q._ma(ma8)}  MFN={m['mfn']}  điểm {m['diem']}  {m['mo_ta'][:100]}")
        if n["phan_biet"]:
            print("  Dòng phân biệt giữa các mã con (nguyên văn): " + " | ".join(n["phan_biet"]))

    print(f"\nĐộ khớp từ khóa: {r['do_tin_cay']} (không phải độ chắc chắn pháp lý).")
    if r["cau_hoi"]:
        print("CẦN HỎI NGƯỜI DÙNG trước khi kết luận:")
        for c in r["cau_hoi"]:
            print(f"  - {c}")
    print("Bước tiếp: `code <mã>` để xem thuế/FTA/CBPG; `chapter`/`heading` để đọc Chú giải loại trừ ở CẢ hai đầu.")


def cmd_phanloai(ten, chuong=None, n=8, json_ra=False):
    codes = q.load_json("hs_tree.json").get("codes", {})
    if not codes:
        print("Dữ liệu Biểu thuế chưa được nạp — chạy scripts/import_tariff.py trước.")
        return
    chapters = q.load_json("chapter_notes.json").get("chapters", {})
    headings = q.load_json("heading_notes.json").get("headings", {})
    r = phan_loai(ten, codes, chapters, headings, chuong=chuong, toi_da_ma=n)
    if json_ra:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        in_ket_qua(r, codes)
