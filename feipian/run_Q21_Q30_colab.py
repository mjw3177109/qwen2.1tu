"""Q21–Q30 image generation queue in an already-running Colab V5.3 Qwen2.1 session.

Run AFTER V5.3 model/server + job function cells, from within the same Python kernel.
Requires the original news.zip, since ChatGPT's uploaded archive is not accessible to Colab.
Does not pretend to start a free Colab GPU remotely.
"""
from __future__ import annotations
import base64, datetime, hashlib, io, json, os, re, tempfile, time, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from google.colab import files as colab_files

REQUIRED = ["generate_one", "gh_read", "gh_write_bytes", "gh_write_json", "GH_HEADERS",
            "GH_BASE", "BRANCH", "REPO", "COMFY", "OUT", "v53_policy",
            "get_preservation_module"]
absent = [name for name in REQUIRED if name not in globals()]
if absent:
    raise RuntimeError("请先运行主 Colab V5.3 的配置、安装、启动和执行函数单元；缺少: "+", ".join(absent))

MANIFEST_PATH = "feipian/Q21_Q30_MANIFEST.json"
RESOLUTION = 512          # T4 14.6GB tested only at lower resolution; change to 640 cautiously.
OVERRIDE = False          # never overwrite existing GitHub output unless consciously enabled.
STOP_ON_FIRST_ERROR = True
ZFILE = Path("/content/news.zip")
if not ZFILE.exists():
    print("请上传之前的原始 news.zip，包含全部《废片之城》母图。上传一次即可。")
    uploaded = colab_files.upload()
    if len(uploaded) != 1:
        raise RuntimeError("一次仅上传一个 news.zip")
    name, raw = next(iter(uploaded.items()))
    if not name.lower().endswith(".zip"):
        raise RuntimeError("需要 news.zip")
    ZFILE.write_bytes(raw)

raw_manifest, _ = gh_read_text(MANIFEST_PATH)
manifest = json.loads(raw_manifest)
if manifest.get("batch") != "Q21-Q30" or len(manifest.get("tasks", [])) != 10:
    raise RuntimeError("GitHub 分镜任务清单不正确")
task_map = {t["id"]: t for t in manifest["tasks"]}
created = {}

with zipfile.ZipFile(ZFILE) as _z:
    index = {}
    for name in _z.namelist():
        if name.startswith("/") or ".." in name.replace("\\", "/").split("/"):
            raise ValueError("非法 ZIP 文件路径")
        if "/母图/" in name:
            subpath = name.split("/母图/", 1)[1]
            if subpath in index:
                raise ValueError("母图路径重复: "+subpath)
            index[subpath] = name
    missing = sorted(set(t["source"].removeprefix("母图/") for t in task_map.values()
                         if not t["source"].startswith("@")) - set(index))
    if missing:
        raise RuntimeError("news.zip 缺少母图: "+", ".join(missing))
    print("✅ ZIP 母图已匹配，任务:",len(task_map),"，未直接使用示例/预览图作为新生成输出。")

def source_bytes(t):
    ref = t["source"]
    if ref.startswith("@"):
        dep = ref[1:]
        if dep in created:
            return created[dep]
        dep_path = task_map[dep]["output"]
        item = gh_read(dep_path,missing_ok=True)
        if item is None or item.get("encoding")!="base64":
            raise RuntimeError(f"{t['id']} 缺少前置已验收画面: {dep_path}")
        return base64.b64decode(item["content"])
    with zipfile.ZipFile(ZFILE) as z:
        return z.read(index[ref.removeprefix("母图/")])

def make_reference_input(task,blob):
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(blob))).convert("RGB")
    original = COMFY/"input"/f"feipian_original_{task['id']}.png"
    original.parent.mkdir(parents=True,exist_ok=True)
    im.save(original)
    mode = "local_patch" if task["id"] in ("Q23_ROOF_BLOCK_RECORD","Q28_SCREEN_BLOCK") else "full_redraw"
    if mode == "local_patch":
        # Areas chosen against each newly generated overhead reference image:
        # User character placements, not the surrounding roof/screen/room geometry.
        ww,hh=im.size
        bounds = ([0.20,0.45,0.83,0.82] if task["id"].startswith("Q23_") else
                  [0.08,0.30,0.93,0.92])
        x0,y0,x1,y1=(round(bounds[0]*ww),round(bounds[1]*hh),
                     round(bounds[2]*ww),round(bounds[3]*hh))
        # Rectangle is a rough region: manual QA of character positions is mandatory.
        region={"mode":"patch","crop_box":[x0,y0,x1,y1],
                "polygon":[[x0,y0],[x1,y0],[x1,y1],[x0,y1]],
                "feather":2.0}
        policy={"edit_mode":"local_patch","edit_region":region}
        v53_policy.validate_task_policy(policy,im.size)
        frame = im.crop((x0,y0,x1,y1))
    else:
        # These Q prompts explicitly authorize camera/frame transformation, asset views,
        # or scene-wide dawn lighting; log the user's original per-shot instruction.
        policy={"edit_mode":"full_redraw","full_redraw_authorized":True,
                "full_redraw_user_instruction":task["optimized_prompt"][9:]}
        v53_policy.validate_task_policy(policy,im.size)
        frame=im
    # This resizes the MODEL INPUT for GPU, not the original final reference.
    max_pixels = RESOLUTION*RESOLUTION
    if frame.width*frame.height > max_pixels:
        factor=(max_pixels/(frame.width*frame.height))**0.5
        nw=max(32,round(frame.width*factor/32)*32)
        nh=max(32,round(frame.height*factor/32)*32)
        frame=frame.resize((nw,nh),Image.Resampling.LANCZOS)
    input_name=f"feipian_source_{task['id']}.png"
    frame.save(COMFY/"input"/input_name)
    return input_name,original,policy

def generate_task(t):
    output_path=t["output"]
    if not re.fullmatch(r"feipian/Q(?:2[1-9]|30)_[A-Z0-9_]+[.]png",output_path):
        raise RuntimeError("禁止写入非 feipian 的路径: "+output_path)
    if gh_read(output_path,missing_ok=True) and not OVERRIDE:
        print("⏭ 已有 GitHub 成品，不覆盖:",output_path)
        return
    blob=source_bytes(t)
    name,original,policy=make_reference_input(t,blob)
    print("▶️ ",t["id"],"源:",t["source"],"模式:",policy["edit_mode"])
    generated=generate_one(t["id"],t["optimized_prompt"],name,t["seed"],RESOLUTION)
    candidate=Image.open(generated).convert("RGB")
    orig=Image.open(original).convert("RGB")
    if policy["edit_mode"]=="local_patch":
        module=get_preservation_module()
        result,mask_pix=module.composite(orig,policy["edit_region"],candidate)
        method="SOURCE_PRESERVED_QWEN_PATCH"
    else:
        # New shot perspectives cannot be pixel-preserved. Keep native generated output;
        # no fake claim of full-resolution source preservation.
        result=candidate
        method="EXPLICIT_SHOT_VIEW_GENERATION"
    memory=io.BytesIO()
    result.save(memory,format="PNG",optimize=True)
    png=memory.getvalue()
    gh_write_bytes(output_path,png,f"feipian: produce {t['id']}")
    record_path=f"feipian/results/{t['id']}.json"
    result_json={"schema_version":1,"id":t["id"],"status":"GENERATED_AWAITING_VISUAL_QA",
      "output_path":output_path,"method":method,"dimensions":list(result.size),
      "source":t["source"],"source_sha256":hashlib.sha256(blob).hexdigest(),
      "reference_paths":t["references"],"reference_images_used_directly":False,
      "engine":"Qwen-Image-2.1 / Colab T4", "completed_at":
      datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "qa_note":"Review scene/camera, character identity, object count, hands, and dependencies. Auxiliary images are listed as references but the single-image workflow does not ingest them."}
    gh_write_json(record_path,result_json)
    created[t["id"]]=png
    print("✅ 已上传待验收 PNG:",f"https://github.com/{REPO}/blob/{BRANCH}/{output_path}")

for index,task_id in enumerate(manifest["generation_order"],1):
    task=task_map[task_id]
    print(f"\n====== 第 {index}/10 个镜头：{task_id} ======")
    try:
        generate_task(task)
    except Exception as e:
        safe=str(e).replace(GITHUB_TOKEN,"[REDACTED]")[:600]
        print("❌ 此任务尚未生成:",task_id,type(e).__name__,safe)
        try:
            gh_write_json(f"feipian/results/{task_id}_attempt.json",
               {"id":task_id,"status":"RETRYABLE_FAILED","error":safe,
                "at":datetime.datetime.now(datetime.timezone.utc).isoformat()})
        except Exception:
            print("⚠️ 上传失败记录也未成功")
        if STOP_ON_FIRST_ERROR:
            raise
    time.sleep(1)
print("\n批次尝试完成。请在 GitHub feipian 逐张检查生成候选图，通过审查前不标成最终 SUCCEEDED。")
