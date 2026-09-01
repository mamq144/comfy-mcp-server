# Custom MCP & KoboldCPP Integration Server

A lightweight, robust, and bilingual Python-based Model Context Protocol (MCP) and integration server designed to bridge local LLM runners (like KoboldCPP) with local workspace management, file editing, and advanced ComfyUI automation workflows.

---

## 🚀 Features & Capabilities (المميزات والإمكانيات الرئيسية)

- **📁 Local Workspace Management:** Securely list, read, write, and manage workspace files within designated local directories (e.g., `E:\AI_Workspace`)[cite: 3].
- **📝 Text & Subtitle Editing:** Advanced tools to write, view, and modify text files or translation formats like `.srt` seamlessly[cite: 3].
- **🤖 KoboldCPP & ComfyUI Integration:** Built to interact smoothly with local AI setups, supporting FLUX image generation, SVD video animation, and custom workflows[cite: 3].
- *⚙️ Node & Model Management:** Automatically install custom nodes from GitHub, download models from Hugging Face, and inspect node definitions[cite: 3].
- **📊 System Monitoring:** Track VRAM usage, system stats, queue status, and manage server reboots programmatically[cite: 3].

---

## 🛠️ Complete Toolset Reference (مرجع الأدوات الكاملة)

| Tool Name (اسم الأداة) | Description (الوصف بالعربي) |
| :--- | :--- |
| `write_local_file` | كتابة أو حفظ محتوى نصي كامل جديد (srt, txt, py, json)[cite: 3]. |
| `edit_local_file` | تعديل واستبدال النصوص أو الترجمات داخل الملفات[cite: 3]. |
| `view_local_file` | فتح وعرض الصور أو قراءة محتوى الملفات من القرص[cite: 3]. |
| `generate_flux_image` | توليد صور FLUX سينمائية فائقة الدقة[cite: 3]. |
| `animate_image_to_video` | تحويل الصور الثابتة إلى مقاطع فيديو (Image-to-Video)[cite: 3]. |
| `execute_custom_workflow` | إرسال مسارات العمل المخصصة (Workflow JSON)[cite: 3]. |
| `install_custom_node` | تثبيت العقد المخصصة من GitHub تلقائياً[cite: 3]. |
| `download_model_file` | تنزيل الموديلات وحفظها في المجلد المناسب[cite: 3]. |
| `get_system_stats` | فحص استهلاك الذاكرة وكرت الشاشة (RTX 4090)[cite: 3]. |
| `restart_comfyui` | إعادة تشغيل الخادم برمجياً لتفعيل التحديثات[cite: 3]. |

---

## 📂 Project Structure (هيكلية المشروع)

```text
├── comfy_mcp_server.py    # Main server script containing tools, handlers, and logic
├── requirements.txt       # Required Python packages (httpx, uvicorn, starlette)
├── LICENSE                # MIT License protecting your intellectual property
└── README.md              # Project documentation and guide