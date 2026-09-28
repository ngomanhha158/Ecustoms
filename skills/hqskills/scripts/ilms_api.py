# -*- coding: utf-8 -*-
"""Nối công cụ với kho Tra cứu HS của ILMSv2 (/api/tracuu).

Bật khi có biến môi trường:
    ILMS_URL   vd https://<dia-chi-may-chu>
    ILMS_TOKEN token đăng nhập, HOẶC ILMS_USER + ILMS_PASS để tự đăng nhập
Không có ILMS_URL -> các lệnh chạy trên tệp máy như cũ.
"""
import http.client
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid

URL = os.environ.get("ILMS_URL", "").rstrip("/")
_token = os.environ.get("ILMS_TOKEN", "")


def bat():
    return bool(URL)


def _goi(method, path, body=None, headers=None, raw=None, timeout=30):
    """GET đứt mạng / quá giờ thì thử lại (tối đa 3 lần — đọc lặp lại vô hại).
    POST không thử lại (có thể đã ghi / đã tốn một lượt OCR) — báo lỗi dễ đọc."""
    for _lan in range(3 if method == "GET" else 1):
        try:
            return _goi_mot(method, path, body, headers, raw, timeout)
        except (TimeoutError, ConnectionError, http.client.IncompleteRead, http.client.RemoteDisconnected) as e:
            loi = e
    raise SystemExit(f"Mạng tới ILMS chập chờn ({type(loi).__name__}) khi gọi {method} {path} — thử lại sau ít phút.")


def _goi_mot(method, path, body, headers, raw, timeout):
    req = urllib.request.Request(URL + path, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    data = raw
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as r:
            txt = r.read().decode("utf-8")
            return json.loads(txt) if txt else None
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail")
        except Exception:
            detail = None
        if isinstance(detail, list):   # lỗi kiểm dữ liệu của FastAPI: lấy câu người đọc được
            detail = "; ".join(str(x.get("msg", "")).removeprefix("Value error, ") for x in detail)
        raise SystemExit(f"ILMS trả lỗi {e.code}: {detail or e.reason}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Không kết nối được ILMS ({URL}): {e.reason}")


def _dang_nhap():
    global _token
    if _token:
        return _token
    u, p = os.environ.get("ILMS_USER"), os.environ.get("ILMS_PASS")
    if not (u and p):
        raise SystemExit("Thiếu ILMS_TOKEN hoặc ILMS_USER + ILMS_PASS.")
    _token = _goi("POST", "/api/auth/login", {"username": u, "password": p})["access_token"]
    return _token


def get(path, **params):
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    return _goi("GET", f"/api/tracuu{path}" + (f"?{q}" if q else ""),
                headers={"Authorization": f"Bearer {_dang_nhap()}"})


def post(path, body):
    return _goi("POST", f"/api/tracuu{path}", body=body, headers={"Authorization": f"Bearer {_dang_nhap()}"})


def ocr_van_ban(duong_dan):
    """POST /api/tracuu/van-ban/ocr-preview — ILMS OCR bằng Gemini, KHÔNG lưu gì.
    Trả {so_hieu, ten, ngay_ban_hanh, co_quan, noi_dung (số/mã không chắc bọc 【…】), canh_bao}."""
    ten = os.path.basename(duong_dan)
    mime = "application/pdf" if ten.lower().endswith(".pdf") else "image/jpeg"
    with open(duong_dan, "rb") as f:
        tep = f.read()
    ranh = uuid.uuid4().hex
    raw = (f'--{ranh}\r\nContent-Disposition: form-data; name="tep"; filename="{ten}"\r\n'
           f"Content-Type: {mime}\r\n\r\n").encode() + tep + f"\r\n--{ranh}--\r\n".encode()
    return _goi("POST", "/api/tracuu/van-ban/ocr-preview", raw=raw, timeout=300, headers={
        "Authorization": f"Bearer {_dang_nhap()}", "Content-Type": f"multipart/form-data; boundary={ranh}"})


def them_van_ban(meta, noi_dung):
    """POST multipart /api/tracuu/van-ban (cần quyền tracuu.manage)."""
    ranh = uuid.uuid4().hex
    phan = []
    for k, v in {**meta, "noi_dung": noi_dung}.items():
        if v in (None, ""):
            continue
        phan.append(f'--{ranh}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n')
    raw = ("".join(phan) + f"--{ranh}--\r\n").encode("utf-8")
    return _goi("POST", "/api/tracuu/van-ban", raw=raw, headers={
        "Authorization": f"Bearer {_dang_nhap()}",
        "Content-Type": f"multipart/form-data; boundary={ranh}"})
