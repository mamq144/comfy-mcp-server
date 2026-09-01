import os
import glob
import json
import random
import shutil
import base64
import subprocess
import asyncio
import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route

COMFY_BASE_URL = "http://127.0.0.1:8188"
COMFY_ROOT_DIR = r"D:\Stability_Data\Packages\ComfyUI"
COMFY_OUTPUT_DIR = os.path.join(COMFY_ROOT_DIR, "output")
COMFY_INPUT_DIR = os.path.join(COMFY_ROOT_DIR, "input")
COMFY_NODES_DIR = os.path.join(COMFY_ROOT_DIR, "custom_nodes")
COMFY_MODELS_DIR = os.path.join(COMFY_ROOT_DIR, "models")
WORKSPACE_DIR = r"E:\AI_Workspace"

CALL_HISTORY = {
    "last_tool": None,
    "last_args_str": "",
    "repeat_count": 0
}

TOOLS = [
    {
        "name": "write_local_file",
        "description": "كتابة أو حفظ محتوى نصي كامل جديد داخل ملف على القرص مباشرة (يدعم ملفات srt, txt, py, json وغيرها).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path_or_name": {
                    "type": "string",
                    "description": "اسم الملف أو مساره الكامل"
                },
                "content": {
                    "type": "string",
                    "description": "المحتوى النصي الكامل المراد كتابته وحفظه داخل الملف"
                }
            },
            "required": ["file_path_or_name", "content"]
        }
    },
    {
        "name": "edit_local_file",
        "description": "تعديل واستبدال جزء محدد من النص داخل ملف نصي أو ملف ترجمة (استبدال النص القديم بالنص الجديد المترجم).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path_or_name": {
                    "type": "string",
                    "description": "اسم الملف أو مساره الكامل"
                },
                "old_text": {
                    "type": "string",
                    "description": "النص الإنجليزي أو القديم المراد البحث عنه واستبداله"
                },
                "new_text": {
                    "type": "string",
                    "description": "النص العربي أو الجديد البديل"
                }
            },
            "required": ["file_path_or_name", "old_text", "new_text"]
        }
    },
    {
        "name": "install_custom_node",
        "description": "تثبيت عقدة مخصصة جديدة من GitHub تلقائياً داخل مجلد custom_nodes وتثبيت مكتباتها.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "github_url": {
                    "type": "string",
                    "description": "رابط مستودع GitHub الخاص بالعقدة (مثل: https://github.com/ltdrdata/ComfyUI-Manager.git)"
                }
            },
            "required": ["github_url"]
        }
    },
    {
        "name": "download_model_file",
        "description": "تنزيل موديل جديد من رابط مباشر أو Hugging Face وحفظه في مجلد الموديلات المناسب.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "download_url": {
                    "type": "string",
                    "description": "رابط التحميل المباشر للموديل"
                },
                "model_category": {
                    "type": "string",
                    "enum": ["checkpoints", "unet", "loras", "vae", "clip", "controlnet"],
                    "description": "نوع الموديل لتحديد المجلد المناسب"
                },
                "filename": {
                    "type": "string",
                    "description": "اسم الملف مع الامتداد مثل model.safetensors"
                }
            },
            "required": ["download_url", "model_category", "filename"]
        }
    },
    {
        "name": "restart_comfyui",
        "description": "إعادة تشغيل خادم ComfyUI برمجياً لتفعيل العقد والموديلات المثبتة حديثاً.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "execute_custom_workflow",
        "description": "بناء وإرسال أي مسار عمل (Workflow JSON) تريده إلى ComfyUI مباشرة لأي نموذج (Wan, FLUX, SDXL, Hunyuan3D).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_prompt": {
                    "type": "object",
                    "description": "مخطط العقد الكامل بتنسيق ComfyUI Prompt API"
                }
            },
            "required": ["workflow_prompt"]
        }
    },
    {
        "name": "inspect_node_definitions",
        "description": "فحص منافذ ومدخلات أي عقدة في ComfyUI لمعرفة طريقة ربطها الصحيحة.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_class_name": {
                    "type": "string",
                    "description": "اسم العقدة مثل KSampler أو UNETLoader أو VHS_VideoCombine"
                }
            },
            "required": ["node_class_name"]
        }
    },
    {
        "name": "generate_flux_image",
        "description": "توليد صورة FLUX سينمائية فائقة الدقة والعمل في الخلفية.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "الوصف الإنجليزي للصورة"},
                "model_name": {"type": "string", "default": ""},
                "width": {"type": "integer", "default": 1024},
                "height": {"type": "integer", "default": 1024},
                "steps": {"type": "integer", "default": 25},
                "guidance": {"type": "number", "default": 3.5},
                "seed": {"type": "integer", "default": -1}
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "animate_image_to_video",
        "description": "تحريك صورة ثابتة وتحويلها إلى مقطع فيديو سينمائي عالي الدقة (Image-to-Video).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_name_or_path": {
                    "type": "string",
                    "default": "",
                    "description": "اسم الصورة المراد تحريكها"
                },
                "motion_bucket_id": {
                    "type": "integer",
                    "default": 127
                },
                "frames": {
                    "type": "integer",
                    "default": 25
                },
                "fps": {
                    "type": "integer",
                    "default": 8
                },
                "seed": {
                    "type": "integer",
                    "default": -1
                }
            },
            "required": []
        }
    },
    {
        "name": "get_latest_comfy_output",
        "description": "جلب أحدث صورة أو فيديو تم إنتاجه من مجلد ComfyUI وعرضه في الشاشة.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_type": {
                    "type": "string",
                    "default": "image",
                    "description": "image للصور أو video للفيديو"
                }
            },
            "required": []
        }
    },
    {
        "name": "list_output_files",
        "description": "استعراض كافة الملفات والمخرجات في مجلد ComfyUI مرتبة من الأحدث للأقدم.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "extension": {"type": "string", "default": ""}
            },
            "required": []
        }
    },
    {
        "name": "list_workspace_files",
        "description": "استعراض قائمة الملفات في مجلد مساحة العمل (E:\\AI_Workspace).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "extension": {"type": "string", "default": ""}
            },
            "required": []
        }
    },
    {
        "name": "view_local_file",
        "description": "فتح وعرض أي صورة أو قراءة محتوى أي ملف نصي أو ترجمة من القرص مباشرة.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path_or_name": {
                    "type": "string",
                    "description": "اسم الملف أو مساره الكامل"
                }
            },
            "required": ["file_path_or_name"]
        }
    },
    {
        "name": "check_task_status",
        "description": "التحقق من حالة طابور التوليد الجاري في ComfyUI.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_all_models",
        "description": "عرض كافة الموديلات المتوفرة في النظام بجميع أنواعها.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_system_stats",
        "description": "فحص استهلاك VRAM لكرت RTX 4090 وحالة الذاكرة والنظام.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "interrupt_generation",
        "description": "إيقاف عملية التوليد الحالية في ComfyUI فوراً.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

def find_file_in_folders(filename_or_path: str):
    if not filename_or_path:
        return None
    if os.path.isabs(filename_or_path) and os.path.exists(filename_or_path):
        return filename_or_path
    
    p1 = os.path.join(COMFY_OUTPUT_DIR, filename_or_path)
    if os.path.exists(p1):
        return p1
    p2 = os.path.join(WORKSPACE_DIR, filename_or_path)
    if os.path.exists(p2):
        return p2
    p3 = os.path.join(COMFY_INPUT_DIR, filename_or_path)
    if os.path.exists(p3):
        return p3
    return None

def resolve_target_file_path(target: str) -> str:
    if not target:
        return os.path.join(WORKSPACE_DIR, "output.txt")
    if os.path.isabs(target):
        return target
    found = find_file_in_folders(target)
    if found:
        return found
    return os.path.join(WORKSPACE_DIR, os.path.basename(target))

def get_latest_output_image():
    if not os.path.exists(COMFY_OUTPUT_DIR):
        return None
    valid_exts = [".png", ".jpg", ".jpeg", ".webp"]
    all_imgs = []
    for root, _, files in os.walk(COMFY_OUTPUT_DIR):
        for f in files:
            if os.path.splitext(f)[1].lower() in valid_exts:
                all_imgs.append(os.path.join(root, f))
    if not all_imgs:
        return None
    all_imgs.sort(key=os.path.getmtime, reverse=True)
    return all_imgs[0]

async def get_available_models(client: httpx.AsyncClient):
    models = {"checkpoints": [], "unets": [], "clip": [], "vae": [], "loras": []}
    for endpoint, key in [
        ("CheckpointLoaderSimple", "checkpoints"),
        ("UNETLoader", "unets"),
        ("DualCLIPLoader", "clip"),
        ("VAELoader", "vae"),
        ("LoraLoader", "loras")
    ]:
        try:
            r = await client.get(f"{COMFY_BASE_URL}/object_info/{endpoint}", timeout=5.0)
            if r.status_code == 200:
                first_input = list(r.json().get(endpoint, {}).get("input", {}).get("required", {}).values())
                if first_input and isinstance(first_input[0], list) and len(first_input[0]) > 0:
                    models[key] = first_input[0][0]
        except Exception:
            pass
    return models

async def execute_tool(name: str, args: dict):
    # تتبع وفحص التكرار
    current_args_str = json.dumps(args, sort_keys=True)
    if CALL_HISTORY["last_tool"] == name and CALL_HISTORY["last_args_str"] == current_args_str:
        CALL_HISTORY["repeat_count"] += 1
    else:
        CALL_HISTORY["last_tool"] = name
        CALL_HISTORY["last_args_str"] = current_args_str
        CALL_HISTORY["repeat_count"] = 1

    if CALL_HISTORY["repeat_count"] > 3:
        return [{
            "type": "text",
            "text": (
                f"⚠️ **توقف أمان تلقائي:** تم تكرار طلب الأداة `{name}` 3 مرات متتالية بنفس المدخلات.\n"
                f"يرجى توجيه النموذج بالخطوة التالية يدوياً."
            )
        }]

    # 1. كتابة ملف كامل
    if name == "write_local_file":
        target = args.get("file_path_or_name", "").strip()
        content = args.get("content", "")
        save_path = resolve_target_file_path(target)
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            return [{
                "type": "text",
                "text": f"✅ **تم حفظ وكتابة الملف بنجاح:** `{save_path}`\n- الحجم: {len(content)} حرف."
            }]
        except Exception as e:
            return [{"type": "text", "text": f"فشل كتابة الملف: {str(e)}"}]

    # 2. تعديل واستبدال نص في ملف
    elif name == "edit_local_file":
        target = args.get("file_path_or_name", "").strip()
        old_text = args.get("old_text", "")
        new_text = args.get("new_text", "")
        actual_path = find_file_in_folders(target)

        if not actual_path:
            return [{"type": "text", "text": f"تعذر العثور على الملف لتعديله: `{target}`"}]

        try:
            encodings = ["utf-8", "utf-8-sig", "windows-1256", "latin-1"]
            file_content = None
            used_enc = "utf-8"
            for enc in encodings:
                try:
                    with open(actual_path, "r", encoding=enc) as f:
                        file_content = f.read()
                    used_enc = enc
                    break
                except UnicodeDecodeError:
                    continue

            if file_content is None:
                return [{"type": "text", "text": f"تعذر فك تشفير الملف لقراءته."}]

            if old_text not in file_content:
                return [{
                    "type": "text",
                    "text": f"⚠️ النص القديم المطلوب استبداله غير موجود في الملف: `{os.path.basename(actual_path)}`"
                }]

            updated_content = file_content.replace(old_text, new_text, 1)
            with open(actual_path, "w", encoding=used_enc) as f:
                f.write(updated_content)

            return [{
                "type": "text",
                "text": f"✅ **تم استبدال وحفظ النص بنجاح في:** `{os.path.basename(actual_path)}`"
            }]
        except Exception as e:
            return [{"type": "text", "text": f"فشل تعديل الملف: {str(e)}"}]

    # 3. تثبيت عقد مخصصة من GitHub
    elif name == "install_custom_node":
        repo_url = args.get("github_url", "").strip()
        if not repo_url.startswith("http"):
            return [{"type": "text", "text": "يرجى تقديم رابط GitHub صالح يبدأ بـ https://"}]
        
        folder_name = os.path.splitext(os.path.basename(repo_url))[0]
        target_dir = os.path.join(COMFY_NODES_DIR, folder_name)

        if os.path.exists(target_dir):
            return [{"type": "text", "text": f"العقدة مثبتة مسبقاً في: `{target_dir}`"}]

        try:
            res = subprocess.run(["git", "clone", repo_url, target_dir], capture_output=True, text=True, check=True)
            req_path = os.path.join(target_dir, "requirements.txt")
            if os.path.exists(req_path):
                subprocess.run(["pip", "install", "-r", req_path], capture_output=True, text=True)

            return [{
                "type": "text",
                "text": f"✅ **تم تثبيت العقدة بنجاح!**\n- **المسار:** `{target_dir}`\n\nيرجى استخدام أداة `restart_comfyui` لتفعيلها الآن داخل النظام."
            }]
        except Exception as e:
            return [{"type": "text", "text": f"فشل تثبيت العقدة: {str(e)}"}]

    # 4. تنزيل موديلات جديدة
    elif name == "download_model_file":
        url = args.get("download_url", "").strip()
        category = args.get("model_category", "checkpoints").lower()
        fname = args.get("filename", "").strip()

        dest_dir = os.path.join(COMFY_MODELS_DIR, category)
        os.makedirs(dest_dir, exist_ok=True)
        save_path = os.path.join(dest_dir, fname)

        if os.path.exists(save_path):
            return [{"type": "text", "text": f"الملف موجود مسبقاً في: `{save_path}`"}]

        try:
            async with httpx.AsyncClient(timeout=600.0) as dl_client:
                async with dl_client.stream("GET", url, follow_redirects=True) as resp:
                    if resp.status_code != 200:
                        return [{"type": "text", "text": f"فشل التحميل، كود الخطأ: {resp.status_code}"}]
                    with open(save_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                            f.write(chunk)

            size_mb = round(os.path.getsize(save_path) / (1024 * 1024), 2)
            return [{
                "type": "text",
                "text": f"✅ **اكتمل تحميل الموديل بنجاح!**\n- **الملف:** `{fname}` ({size_mb} MB)\n- **المسار:** `{save_path}`"
            }]
        except Exception as e:
            return [{"type": "text", "text": f"فشل تحميل الموديل: {str(e)}"}]

    # 5. إعادة تشغيل خادم ComfyUI برمجياً
    elif name == "restart_comfyui":
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(f"{COMFY_BASE_URL}/manager/reboot", timeout=5.0)
                return [{"type": "text", "text": "🔄 تم إرسال أمر إعادة التشغيل لخادم ComfyUI بنجاح، جاري إعادة تحميل العقد والموديلات."}]
            except Exception:
                return [{"type": "text", "text": "⚠️ تم إرسال أمر الإنعاش، إذا لم يستجب ComfyUI تلقائياً يرجى الضغط على Restart في واجهة Stability Matrix."}]

    # 6. تنفيذ مسار مخصص
    elif name == "execute_custom_workflow":
        workflow = args.get("workflow_prompt", {})
        async with httpx.AsyncClient() as client:
            post_resp = await client.post(f"{COMFY_BASE_URL}/prompt", json={"prompt": workflow}, timeout=20.0)
            if post_resp.status_code != 200:
                return [{"type": "text", "text": f"رفض ComfyUI للمسار: {post_resp.text}"}]
            prompt_id = post_resp.json().get("prompt_id", "Unknown")
            return [{"type": "text", "text": f"🚀 **تم إرسال المسار المخصص وبدأ التنفيذ!** (Prompt ID: `{prompt_id}`)"}]

    # 7. فحص مواصفات عقدة
    elif name == "inspect_node_definitions":
        node_name = args.get("node_class_name", "").strip()
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{COMFY_BASE_URL}/object_info/{node_name}", timeout=10.0)
            if resp.status_code == 200:
                return [{"type": "text", "text": json.dumps(resp.json(), ensure_ascii=False, indent=2)}]
            return [{"type": "text", "text": f"تعذر العثور على العقدة `{node_name}`."}]

    # 8. توليد FLUX
    elif name == "generate_flux_image":
        prompt = args.get("prompt", "")
        model_name = args.get("model_name", "")
        width = int(args.get("width", 1024))
        height = int(args.get("height", 1024))
        steps = int(args.get("steps", 25))
        guidance = float(args.get("guidance", 3.5))
        seed = int(args.get("seed", -1))
        if seed == -1:
            seed = random.randint(1, 1125899906842624)

        async with httpx.AsyncClient() as client:
            models = await get_available_models(client)
            is_unet = False
            if not model_name:
                flux_unets = [m for m in models["unets"] if "flux" in m.lower()]
                flux_ckpts = [m for m in models["checkpoints"] if "flux" in m.lower()]
                if flux_unets:
                    model_name, is_unet = flux_unets[0], True
                elif flux_ckpts:
                    model_name, is_unet = flux_ckpts[0], False
                elif models["unets"]:
                    model_name, is_unet = models["unets"][0], True
                else:
                    model_name, is_unet = models["checkpoints"][0], False
            else:
                is_unet = model_name in models["unets"]

            clip_t5 = next((c for c in models["clip"] if "t5" in c.lower()), models["clip"][0] if models["clip"] else "")
            clip_l = next((c for c in models["clip"] if "clip_l" in c.lower() or "vi-l" in c.lower()), models["clip"][1] if len(models["clip"]) > 1 else clip_t5)
            vae_name = next((v for v in models["vae"] if "ae" in v.lower() or "flux" in v.lower()), models["vae"][0] if models["vae"] else "")

            workflow = {
                "1": {"inputs": {"unet_name" if is_unet else "ckpt_name": model_name, **({"weight_dtype": "default"} if is_unet else {})}, "class_type": "UNETLoader" if is_unet else "CheckpointLoaderSimple"},
                "2": {"inputs": {"clip_name1": clip_t5, "clip_name2": clip_l, "type": "flux"}, "class_type": "DualCLIPLoader"},
                "3": {"inputs": {"vae_name": vae_name}, "class_type": "VAELoader"},
                "4": {"inputs": {"text": prompt, "clip": ["2", 0]}, "class_type": "CLIPTextEncode"},
                "5": {"inputs": {"guidance": guidance, "conditioning": ["4", 0]}, "class_type": "FluxGuidance"},
                "6": {"inputs": {"text": "", "clip": ["2", 0]}, "class_type": "CLIPTextEncode"},
                "7": {"inputs": {"width": width, "height": height, "batch_size": 1}, "class_type": "EmptyLatentImage"},
                "8": {"inputs": {"seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0, "model": ["1", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0]}, "class_type": "KSampler"},
                "9": {"inputs": {"samples": ["8", 0], "vae": ["3" if is_unet or vae_name else "1", 0 if is_unet or vae_name else 2]}, "class_type": "VAEDecode"},
                "10": {"inputs": {"filename_prefix": "MCP_FLUX", "images": ["9", 0]}, "class_type": "SaveImage"}
            }

            post_resp = await client.post(f"{COMFY_BASE_URL}/prompt", json={"prompt": workflow}, timeout=15.0)
            prompt_id = post_resp.json().get("prompt_id", "Unknown") if post_resp.status_code == 200 else "Error"
            return [{"type": "text", "text": f"🚀 **تم إرسال مهمة FLUX بنجاح!** (Prompt ID: `{prompt_id}`)"}]

    # 9. تحريك فيديو (SVD)
    elif name == "animate_image_to_video":
        target_img = args.get("image_name_or_path", "").strip()
        motion_bucket_id = int(args.get("motion_bucket_id", 127))
        frames = int(args.get("frames", 25))
        fps = int(args.get("fps", 8))
        seed = int(args.get("seed", -1))
        if seed == -1:
            seed = random.randint(1, 1125899906842624)

        actual_img_path = find_file_in_folders(target_img) if target_img else get_latest_output_image()
        if not actual_img_path:
            return [{"type": "text", "text": "لم يتم العثور على أي صورة لتحريكها."}]

        img_basename = os.path.basename(actual_img_path)
        os.makedirs(COMFY_INPUT_DIR, exist_ok=True)
        dest_input_path = os.path.join(COMFY_INPUT_DIR, img_basename)
        if not os.path.exists(dest_input_path) or os.path.getmtime(actual_img_path) > os.path.getmtime(dest_input_path):
            shutil.copy2(actual_img_path, dest_input_path)

        async with httpx.AsyncClient() as client:
            models = await get_available_models(client)
            svd_models = [c for c in models["checkpoints"] if "svd" in c.lower()]
            svd_model = svd_models[0] if svd_models else (models["checkpoints"][0] if models["checkpoints"] else "svd.safetensors")

            workflow = {
                "1": {"inputs": {"ckpt_name": svd_model}, "class_type": "ImageOnlyCheckpointLoader"},
                "2": {"inputs": {"image": img_basename, "upload": "image"}, "class_type": "LoadImage"},
                "3": {"inputs": {"width": 1024, "height": 576, "video_frames": frames, "motion_bucket_id": motion_bucket_id, "fps": fps, "augmentation_level": 0.02, "clip_vision": ["1", 1], "init_image": ["2", 0], "vae": ["1", 2]}, "class_type": "SVD_img2vid_Conditioning"},
                "4": {"inputs": {"seed": seed, "steps": 20, "cfg": 2.5, "sampler_name": "euler", "scheduler": "karras", "denoise": 1.0, "model": ["1", 0], "positive": ["3", 0], "negative": ["3", 1], "latent_image": ["3", 2]}, "class_type": "KSampler"},
                "5": {"inputs": {"samples": ["4", 0], "vae": ["1", 2]}, "class_type": "VAEDecode"},
                "6": {"inputs": {"frame_rate": fps, "loop_count": 0, "filename_prefix": "MCP_Video_SVD", "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 19, "save_metadata": True, "pingpong": False, "save_output": True, "images": ["5", 0]}, "class_type": "VHS_VideoCombine"}
            }

            post_resp = await client.post(f"{COMFY_BASE_URL}/prompt", json={"prompt": workflow}, timeout=15.0)
            prompt_id = post_resp.json().get("prompt_id", "Unknown") if post_resp.status_code == 200 else "Error"
            return [{"type": "text", "text": f"🎬 **بدأت عملية إنتاج الفيديو بنجاح!** (Prompt ID: `{prompt_id}`)"}]

    # 10. جلب أحدث مخرج
    elif name == "get_latest_comfy_output":
        file_type = args.get("file_type", "image").lower()
        if not os.path.exists(COMFY_OUTPUT_DIR):
            return [{"type": "text", "text": f"المجلد غير موجود: {COMFY_OUTPUT_DIR}"}]

        valid_exts = [".png", ".jpg", ".jpeg", ".webp"] if file_type == "image" else [".mp4", ".webm", ".gif", ".mov"]
        all_files = []
        for root, _, files in os.walk(COMFY_OUTPUT_DIR):
            for f in files:
                if os.path.splitext(f)[1].lower() in valid_exts:
                    all_files.append(os.path.join(root, f))

        if not all_files:
            return [{"type": "text", "text": f"لم يتم العثور على أي ملفات من نوع ({file_type})."}]

        all_files.sort(key=os.path.getmtime, reverse=True)
        latest_file = all_files[0]
        ext = os.path.splitext(latest_file)[1].lower()
        filename = os.path.basename(latest_file)

        if ext in [".png", ".jpg", ".jpeg", ".webp"]:
            try:
                with open(latest_file, "rb") as img_f:
                    b64_data = base64.b64encode(img_f.read()).decode("utf-8")
                return [
                    {"type": "image", "data": b64_data, "mimeType": "image/png"},
                    {"type": "text", "text": f"✅ **تم جلب الصورة:** `{filename}`"}
                ]
            except Exception as e:
                return [{"type": "text", "text": f"تعذر تحميل الصورة: {str(e)}"}]
        else:
            size_mb = round(os.path.getsize(latest_file) / (1024 * 1024), 2)
            return [{"type": "text", "text": f"🎬 **الملف:** `{filename}` ({size_mb} MB)\n- **المسار:** `{latest_file}`"}]

    # 11. استعراض الملفات والمعاينة
    elif name == "list_output_files":
        pattern = os.path.join(COMFY_OUTPUT_DIR, "*.*")
        files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        file_list = [f"- `{os.path.basename(f)}` ({round(os.path.getsize(f)/(1024*1024),2)} MB)" for f in files[:25]]
        return [{"type": "text", "text": "📂 **أحدث مخرجات ComfyUI:**\n\n" + "\n".join(file_list)}]

    elif name == "list_workspace_files":
        pattern = os.path.join(WORKSPACE_DIR, "*.*")
        files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        file_list = [f"- `{os.path.basename(f)}` ({round(os.path.getsize(f)/(1024*1024),2)} MB)" for f in files[:25]]
        return [{"type": "text", "text": "📁 **ملفات مساحة العمل:**\n\n" + "\n".join(file_list)}]

    elif name == "view_local_file":
        target = args.get("file_path_or_name", "").strip()
        actual_path = find_file_in_folders(target)
        if not actual_path:
            return [{"type": "text", "text": f"تعذر العثور على الملف: `{target}`"}]
        
        ext = os.path.splitext(actual_path)[1].lower()
        
        if ext in [".png", ".jpg", ".jpeg", ".webp"]:
            with open(actual_path, "rb") as img_f:
                b64_data = base64.b64encode(img_f.read()).decode("utf-8")
            return [{"type": "image", "data": b64_data, "mimeType": "image/png"}, {"type": "text", "text": f"🖼️ `{os.path.basename(actual_path)}`"}]
        
        text_exts = [".srt", ".vtt", ".txt", ".json", ".py", ".bat", ".vbs", ".md", ".log", ".csv", ".ini"]
        if ext in text_exts:
            try:
                encodings_to_try = ["utf-8", "utf-8-sig", "windows-1256", "latin-1"]
                content = ""
                for enc in encodings_to_try:
                    try:
                        with open(actual_path, "r", encoding=enc) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue

                max_chars = 12000
                if len(content) > max_chars:
                    truncated_content = content[:max_chars]
                    return [{
                        "type": "text",
                        "text": f"📄 **محتوى الملف `{os.path.basename(actual_path)}` (الدفعة الأولى):**\n\n```text\n{truncated_content}\n```"
                    }]
                else:
                    return [{
                        "type": "text",
                        "text": f"📄 **محتوى الملف `{os.path.basename(actual_path)}`:**\n\n```text\n{content}\n```"
                    }]
            except Exception as e:
                return [{"type": "text", "text": f"فشل قراءة الملف: {str(e)}"}]

        return [{"type": "text", "text": f"📦 الملف موجود: `{actual_path}` (نوع غير نصي)"}]

    # 12. أدوات المراقبة
    async with httpx.AsyncClient() as client:
        try:
            if name == "check_task_status":
                q_resp = await client.get(f"{COMFY_BASE_URL}/queue", timeout=5.0)
                running = len(q_resp.json().get("queue_running", [])) if q_resp.status_code == 200 else 0
                pending = len(q_resp.json().get("queue_pending", [])) if q_resp.status_code == 200 else 0
                return [{"type": "text", "text": f"📊 **المهام الجارية:** {running} | **قيد الانتظار:** {pending}"}]

            elif name == "get_system_stats":
                resp = await client.get(f"{COMFY_BASE_URL}/system_stats", timeout=10.0)
                return [{"type": "text", "text": resp.text if resp.status_code == 200 else f"Error: {resp.status_code}"}]

            elif name == "list_all_models":
                models = await get_available_models(client)
                return [{"type": "text", "text": json.dumps(models, ensure_ascii=False, indent=2)}]

            elif name == "interrupt_generation":
                await client.post(f"{COMFY_BASE_URL}/interrupt", timeout=5.0)
                return [{"type": "text", "text": "تم إيقاف عملية التوليد الحالية فوراً."}]

            return [{"type": "text", "text": f"الأداة '{name}' غير موجودة."}]
        except Exception as e:
            return [{"type": "text", "text": f"Execution Failed: {str(e)}"}]

async def mcp_handler(request):
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "*"})

    try:
        data = await request.json()
    except Exception:
        data = {}

    req_id = data.get("id")
    method = data.get("method")
    params = data.get("params", {})

    if method == "initialize":
        return JSONResponse({"jsonrpc": "2.0", "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "comfy-master-hub", "version": "12.0.0"}}, "id": req_id})

    elif method == "tools/list":
        return JSONResponse({"jsonrpc": "2.0", "result": {"tools": TOOLS}, "id": req_id})

    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        content = await execute_tool(tool_name, tool_args)
        return JSONResponse({"jsonrpc": "2.0", "result": {"content": content, "isError": False}, "id": req_id})

    elif method == "notifications/initialized":
        return Response(status_code=200)

    return JSONResponse({"jsonrpc": "2.0", "result": {"tools": TOOLS}, "id": req_id})

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=False)
]

routes = [Route("/{path:path}", endpoint=mcp_handler, methods=["GET", "POST", "OPTIONS"])]
app = Starlette(routes=routes, middleware=middleware)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)