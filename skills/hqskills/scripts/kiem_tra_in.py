# -*- coding: utf-8 -*-
"""Lệnh `kiemtra` — phiếu kiểm tra nhanh MỘT dòng hàng tờ khai (mẫu A, CEO duyệt 05-11-2026).

Luật dựng phiếu KHÔNG viết ở đây: kiem_tra_dong_local.py là bản chép nguyên văn ILMS
services/kiem_tra_dong.py (scripts/chep_luat_ilms.py). Tệp này chỉ: đọc Biểu thuế trên máy
(hs_tree.json), tính PVTM bằng pvtm_local.tinh_cho_lo, rồi in phiếu dạng chữ hoặc HTML.
"""
import html
import json
import os
import re

import kiem_tra_dong_local as kt
import pvtm_local as pl

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def kiem_tra(dau_vao, codes, kho):
    """dau_vao như ILMS KiemTraIn. Sai dữ liệu -> SystemExit (ILMS trả 422/404)."""
    code = re.sub(r"\D", "", dau_vao.get("ma") or "")
    if len(code) != 8:
        raise SystemExit("Mã HS phải đủ 8 số")
    if code not in codes:
        raise SystemExit(f"Không có mã {code[:4]}.{code[4:6]}.{code[6:]} trong Biểu thuế")
    ts = dau_vao.get("thue_suat")
    if ts not in (None, "") and not re.fullmatch(r"\s*\d+(?:[.,]\d+)?\s*%?\s*", ts):
        raise SystemExit(f"Thuế suất khai '{ts}' không phải số (vd 0, 5, 7,5)")
    try:
        dau_vao = {**dau_vao, "ma": code, "nuoc": pl.chuan_nuoc(dau_vao.get("nuoc")),
                   "dang": pl.chuan_dang(dau_vao.get("dang"))}
    except ValueError as e:
        raise SystemExit(str(e))

    def tra_ma(c):
        e = codes.get(c)
        return {**e, "code": c} if e else None   # không có `cap`: luật tự tách cấp theo ' - '

    def ma_con(p):
        return sorted(c for c in codes if c.startswith(p) and len(c) == 8)

    tt = kt.thong_so(dau_vao)
    lo = kt.lo_pvtm(tt, dau_vao)
    pv_ma = pl.tinh_cho_lo(kho, {"code": code, **lo}) if kho else None
    ds = kt.nghi_ngo(code, tt, tra_ma, ma_con)
    nghi = {m["code"]: pl.tinh_cho_lo(kho, {"code": m["code"], **lo}) for m in ds} if kho else {}
    return kt.lap_phieu(dau_vao, tra_ma, ma_con, pv_ma, nghi, tt=tt, ds_nghi_ngo=ds)


_DAU = {"tot": "✓", "canh": "!", "xau": "✗"}
_LY_DO = {"ngoai_chuong_72": "Chỉ soát mã nghi ngờ cho thép Chương 72.",
          "khong_gi": "Thép không gỉ: không có cặp hợp kim / không hợp kim để đặt cạnh.",
          "khong_co_cap": "Nhóm mã này chưa có cặp đối ứng trong bảng ghép."}


def _ma(c):
    return f"{c[:4]}.{c[4:6]}.{c[6:]}" if len(c) == 8 else c


def _dau_phieu(d):
    return " · ".join(x for x in [d.get("tk") and f"TK {d['tk']}" + (f" / {d['dong']}" if d.get("dong") else ""),
                                  d.get("nuoc"), d.get("luong") and f"luồng {d['luong']}"] if x)


def in_chu(p):
    d = p["dau"]
    print(f"PHIẾU KIỂM TRA DÒNG HÀNG — {d.get('ten') or _ma(d['ma'])}" + (f"  [{_dau_phieu(d)}]" if _dau_phieu(d) else ""))
    print("=" * 78)
    for o in p["o"]:
        print(f" {_DAU[o['muc']]} {o['nhan']:<14} {o['gt']:<14} {o['ct']}")
    if p["can_lam_ro"]:
        print("\nCẦN LÀM RÕ")
        for x in p["can_lam_ro"]:
            print(f"  ✗ {x}")
    print("\nKIỂM HÓA CẦN XEM TẬN MẮT")
    for x in p["tan_mat"] or [{"viec": "Không có thông số nào cần đo để giữ kết luận.", "khai": ""}]:
        print(f"  [ ] {x['viec']}" + (f"   (khai {x['khai']})" if x["khai"] else ""))
    print("\nVÌ SAO MÃ NÀY")
    for i, x in enumerate(p["lap_luan"], 1):
        print(f"  {i}. {x}")
    print("\nMÃ NGHI NGỜ TƯƠNG TỰ")
    if len(p["nghi_ngo"]) > 1:
        for x in p["nghi_ngo"]:
            nhan = "đang khai" if x["dang_khai"] else ("cần xác định" if x["can_xac_dinh"] else "nghi ngờ")
            print(f"  {_ma(x['code'])} [{nhan}] {' · '.join(x.get('cap') or [])}")
            print(f"      Khi: {x['khi']} | Thuế: {x['thue']} | CBPG: {x['cbpg'][0]} {x['cbpg'][1]}".rstrip())
        if p["ghi_nghi_ngo"]:
            print(f"  {p['ghi_nghi_ngo']}")
    else:
        print(f"  {_LY_DO.get(p['ly_do_nghi_ngo'], '')}")
    print("\nĐỐI CHIẾU PHẠM VI CBPG")
    if not p["pvtm"]:
        print("  Mã này không thuộc vụ phòng vệ thương mại nào đang áp (dữ liệu trên máy).")
    for v in p["pvtm"]:
        print(f"  [{v['vu']}] {v['so_hieu']} => {v['ket_luan'].upper()}")
        for t in v["tieu_chi"]:
            print(f"      {t['ten']}: {t['qd']} — lô {t['lo']} {({True: '✓', False: '✗'}).get(t['dat'], '?')}")
    print("\nKết quả soát tự động theo Biểu thuế, Chú giải Chương 72 và kho phòng vệ thương mại trên máy —"
          "\nđối chiếu chứng từ gốc (Mill Test, C/O) trước khi kết luận.")


_CSS = """:root{--nen:#fff;--chu:#1b2430;--phu:#5b6675;--vien:#d9dee5;--tot:#0f7a4a;--canh:#a86200;--xau:#b42318;
--nen-tot:#e8f5ee;--nen-canh:#fff4e0;--nen-xau:#fdecea}
@media (prefers-color-scheme:dark){:root{--nen:#14181e;--chu:#e6e9ee;--phu:#9aa4b2;--vien:#2c333d;--tot:#4cc38a;
--canh:#f0a63a;--xau:#ff7b6e;--nen-tot:#123324;--nen-canh:#3a2a10;--nen-xau:#3d1a17}}
body{margin:0;padding:16px;background:var(--nen);color:var(--chu);font:14px/1.5 "Segoe UI",Roboto,Arial,sans-serif}
article{max-width:960px;margin:auto;border:1px solid var(--vien);border-radius:8px;overflow:hidden}
header{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;padding:12px 16px;border-bottom:1px solid var(--vien)}
.o4{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));border-bottom:1px solid var(--vien)}
.o{padding:14px;border-top:4px solid;border-right:1px solid var(--vien)}.o:last-child{border-right:0}
.nhan{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--phu)}
.gt{font-size:20px;font-weight:700;font-variant-numeric:tabular-nums}.ct{font-size:12.5px;color:var(--phu)}
.tot{border-color:var(--tot);color:var(--tot)}.canh{border-color:var(--canh);color:var(--canh)}.xau{border-color:var(--xau);color:var(--xau)}
main{display:grid;gap:20px;padding:16px}h3{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.06em}
ul.tm{list-style:none;margin:0;padding:0;display:grid;gap:6px}
ul.tm li{display:grid;grid-template-columns:18px 1fr auto;gap:10px;padding:8px 12px;border-radius:6px;background:var(--nen-canh)}
ul.tm li span.hop{width:14px;height:14px;border:2px solid var(--canh);border-radius:2px;margin-top:3px}
.mono{font-family:Consolas,monospace;font-size:12.5px}.wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13.5px}th{text-align:left;font-size:12px;color:var(--phu);padding:6px 8px 6px 0}
td{border-top:1px solid var(--vien);padding:8px 8px 8px 0;vertical-align:top}tr.khai td{background:var(--nen-tot)}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600}
.p-tot{background:var(--nen-tot);color:var(--tot)}.p-canh{background:var(--nen-canh);color:var(--canh)}.p-xau{background:var(--nen-xau);color:var(--xau)}
.do{color:var(--xau)}footer{padding:10px 16px;border-top:1px dashed var(--vien);font-size:12px;color:var(--phu)}
@media print{body{padding:0}@page{size:A4;margin:12mm}}"""


def in_html(p):
    e = html.escape
    d = p["dau"]
    pill = lambda chu, muc: f'<span class="pill p-{muc}">{e(chu)}</span>'   # noqa: E731
    o4 = "".join(f'<div class="o {o["muc"]}"><div class="nhan">{e(o["nhan"])}</div><div class="gt">{e(o["gt"])}</div>'
                 f'<div class="ct">{e(o["ct"])}</div></div>' for o in p["o"])
    muc = []
    if p["can_lam_ro"]:
        muc.append(("Cần làm rõ", '<ul class="do">' + "".join(f"<li>{e(x)}</li>" for x in p["can_lam_ro"]) + "</ul>"))
    muc.append(("Kiểm hóa cần xem tận mắt", '<ul class="tm">' + "".join(
        f'<li><span class="hop"></span><span>{e(x["viec"])}</span><span class="mono">khai {e(x["khai"])}</span></li>'
        for x in p["tan_mat"]) + "</ul>" if p["tan_mat"] else "<p>Không có thông số nào cần đo để giữ kết luận.</p>"))
    muc.append(("Vì sao mã này", "<ol>" + "".join(f"<li>{e(x)}</li>" for x in p["lap_luan"]) + "</ol>"))
    if len(p["nghi_ngo"]) > 1:
        dong = "".join(
            f'<tr class="{"khai" if x["dang_khai"] else ""}"><td class="mono"><b>{_ma(x["code"])}</b><br>'
            + (pill("đang khai", "tot") if x["dang_khai"] else pill("cần xác định" if x["can_xac_dinh"] else "nghi ngờ", "canh"))
            + f'</td><td>{e(" · ".join(x.get("cap") or []))}</td><td>{e(x["khi"])}</td><td>{e(x["thue"])}</td>'
            f'<td>{e(x["cbpg"][0])}<div class="ct">{e(x["cbpg"][1])}</div></td></tr>' for x in p["nghi_ngo"])
        nn = ('<div class="wrap"><table><tr><th>Mã HS</th><th>Mô tả</th><th>Rơi vào mã này khi</th><th>Thuế NK</th>'
              f'<th>CBPG</th></tr>{dong}</table></div>' + (f"<p>{e(p['ghi_nghi_ngo'])}</p>" if p["ghi_nghi_ngo"] else ""))
    else:
        nn = f"<p>{e(_LY_DO.get(p['ly_do_nghi_ngo'], ''))}</p>"
    muc.append(("Mã nghi ngờ tương tự", nn))
    if p["pvtm"]:
        dau = {True: "✓", False: "✗"}
        dong = "".join(
            f'<tr><td><b>{e(v["vu"])}</b><div class="mono">{e(v["so_hieu"])}</div></td><td>'
            + "<br>".join(f'{e(t["ten"])}: {e(t["qd"])} — lô {e(t["lo"])} {dau.get(t["dat"], "?")}' for t in v["tieu_chi"])
            + f'</td><td>{pill(v["ket_luan"], v["muc"])}</td></tr>' for v in p["pvtm"])
        cb = f'<div class="wrap"><table><tr><th>Vụ</th><th>Tiêu chí theo QĐ — lô khai</th><th>Kết luận</th></tr>{dong}</table></div>'
    else:
        cb = "<p>Mã này không thuộc vụ phòng vệ thương mại nào đang áp.</p>"
    muc.append(("Đối chiếu phạm vi CBPG", cb))
    than = "".join(f"<section><h3>{e(t)}</h3>{n}</section>" for t, n in muc)
    return (f'<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
            f'initial-scale=1"><title>Phiếu kiểm tra {_ma(d["ma"])}</title><style>{_CSS}</style></head><body><article>'
            f'<header><b>{e(d.get("ten") or _ma(d["ma"]))}</b><span class="mono">{e(_dau_phieu(d))}</span></header>'
            f'<div class="o4">{o4}</div><main>{than}</main><footer>Kết quả soát tự động theo Biểu thuế, Chú giải Chương 72 '
            "và kho phòng vệ thương mại trên máy — đối chiếu chứng từ gốc (Mill Test, C/O) trước khi kết luận.</footer>"
            "</article></body></html>")


def cmd_kiemtra(a, codes):
    try:
        kho = pl.doc_kho()
        canh = pl.canh_bao_cu(kho)
        if canh:
            print(canh + "\n")
    except pl.ChuaDongBo:
        kho = None
        print("! Máy chưa đồng bộ kho PVTM (chạy `dongbo`) — phiếu chưa có phần CBPG.\n")
    vao = {"ma": a.ma, "mo_ta": a.mo_ta or "", "nuoc": a.nuoc, "thue_suat": a.thue_suat, "tk": a.tk, "dong": a.dong,
           "luong": a.luong, "nsx": a.nsx, "nxk": a.nxk, "day": a.day, "rong": a.rong, "carbon": a.carbon,
           "dang": a.dang, "mac_thep": a.mac, "tieu_chuan": a.tc}
    p = kiem_tra(vao, codes, kho)
    if a.json:
        print(json.dumps(p, ensure_ascii=False, indent=1))
    elif a.html:
        with open(a.html, "w", encoding="utf-8") as f:
            f.write(in_html(p))
        print(f"Đã ghi phiếu HTML: {a.html} (mở bằng trình duyệt, Ctrl+P để in A4)")
    else:
        in_chu(p)
