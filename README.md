# Ecustoms skills

Bộ skill Claude cho nghiệp vụ hải quan của True Logistics.

| Skill | Việc |
|---|---|
| [`hs-tool-doclap`](skills/hs-tool-doclap) | Tra cứu mã HS, Biểu thuế 2026, Chú giải Chương, GRI và văn bản pháp luật (CBPG, NĐ/TT, công văn). Nối được với kho Tra cứu HS của ILMSv2. |

## Cài một skill

Chép thư mục skill vào `%USERPROFILE%\.claude\skills\` (dùng riêng), hoặc
vào `.claude/skills/` của một repo (cả đội dùng chung):

```powershell
git clone https://github.com/ngomanhha158/ecustoms-skills.git
Copy-Item -Recurse ecustoms-skills\skills\hs-tool-doclap "$env:USERPROFILE\.claude\skills\"
```

Dữ liệu nền là văn bản pháp luật công khai (Biểu thuế XNK 2026, TT 31/2022,
quyết định và công văn của Bộ Công Thương, Bộ Tài chính). Công cụ tự xây,
không chứa nội dung của skill bên thứ ba.
