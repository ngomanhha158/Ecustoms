# HQskills

Bộ skill Claude cho nghiệp vụ hải quan.

| Skill | Việc |
|---|---|
| [`HQskills`](skills/hqskills) | Tra cứu mã HS, Biểu thuế 2026, Chú giải Chương, GRI và văn bản pháp luật (CBPG, NĐ/TT, công văn); tính thuế CBPG cho lô hàng có soát quy cách; đối chiếu chéo chứng từ (`chungtu`); cảnh báo thời hạn (`canhbao`); soạn báo cáo, công văn theo NĐ 30/2020 (`/baocao`, `/excel`, `/phaply`, `/phanbien`) và xuất .docx. Chạy độc lập trên máy, đồng bộ dữ liệu bằng `dongbo`. |

## Cài một skill

Chép thư mục skill vào `%USERPROFILE%\.claude\skills\` (dùng riêng), hoặc
vào `.claude/skills/` của một repo (cả đội dùng chung):

```powershell
git clone https://github.com/ngomanhha158/Ecustoms.git
Copy-Item -Recurse Ecustoms\skills\hqskills "$env:USERPROFILE\.claude\skills\"
```

Dữ liệu nền là văn bản pháp luật công khai (Biểu thuế XNK 2026, TT 31/2022,
quyết định và công văn của Bộ Công Thương, Bộ Tài chính). Công cụ tự xây,
không chứa nội dung của skill bên thứ ba.
