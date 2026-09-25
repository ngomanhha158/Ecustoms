# Ecustoms

Bộ skill Claude cho nghiệp vụ hải quan của True Logistics.

| Skill | Việc |
|---|---|
| [`Ecustoms`](skills/Ecustoms) | Tra cứu mã HS, Biểu thuế 2026, Chú giải Chương, GRI và văn bản pháp luật (CBPG, NĐ/TT, công văn). Chạy độc lập trên máy, đồng bộ dữ liệu với ILMSv2 bằng `dongbo`. |

## Cài một skill

Chép thư mục skill vào `%USERPROFILE%\.claude\skills\` (dùng riêng), hoặc
vào `.claude/skills/` của một repo (cả đội dùng chung):

```powershell
git clone https://github.com/ngomanhha158/Ecustoms.git
Copy-Item -Recurse Ecustoms\skills\Ecustoms "$env:USERPROFILE\.claude\skills\"
```

Dữ liệu nền là văn bản pháp luật công khai (Biểu thuế XNK 2026, TT 31/2022,
quyết định và công văn của Bộ Công Thương, Bộ Tài chính). Công cụ tự xây,
không chứa nội dung của skill bên thứ ba.
