# Qwen2.1 图片编辑协议 V5｜单图与批量任务

## 对话下单：默认自动识别

- **一张图片 + 说明**：单图编辑；图片是母图，文字是编辑目标。
- **多张图 + 一个要求**：一图一任务，统一编辑目标。
- **一个 ZIP + 对应的 txt/CSV**：按文件名或清单配对逐图编辑。
- **一张图 + 不同版本要求**：同一母图拆为多个 job_id。
- **有歧义才询问**：比如多图多提示词无法匹配、源图与参考图混合、没有编辑目标；不强迫每次选择“单张/批量”。

ChatGPT 在本对话负责理解母图与修改要求、优化提示词、审查配对、提交到 GitHub，**不得调用 ChatGPT 图片生成替代 Qwen-Image-2.1**。实际图像必须由 GPU 工作流执行，GitHub 结果 JSON 是完成的证据。

## ZIP 文件夹协议（推荐）

```text
Qwen_Batch/
  sources/SH001.png
  sources/SH002.jpg
  prompts/SH001.txt
  prompts/SH002.txt
  global_rules.txt            # 可选，所有任务共享约束
  batch_prompt.txt            # 可选，对所有母图应用相同的编辑目标
  batch.csv                   # 可选，精确指定一图多改和参数
```

- 文件名主干相同自动配对：sources/SH001.png ⇔ prompts/SH001.txt。
- 当全部图片共用一条编辑指令时，可以**只提供 batch_prompt.txt**。
- 如果有 batch.csv，按 CSV 权威配对；同一 source 可以多次出现，每行必须有不同 task_id。
- CSV 列：`task_id,source,prompt_file,prompt,resolution,seed`。prompt_file 与 prompt 只填一个；resolution 默认 512，只支持 512/640/768；seed 默认 42。
- 全局约束写 global_rules.txt。没有指定改动的位置应最大限度保持母图原样。
- 原始图片支持 PNG/JPG/JPEG/WEBP，每张不超过 4 MB；一批默认最多 100 个任务。
- 不接受默默忽略缺少提示词的图片、重复任务 ID、模糊配对、遮罩或多个参考图。

## 标准任务

```json
{
  "schema_version": 1,
  "id": "edit_SH001_v1",
  "kind": "image_edit",
  "input_b64_path": "jobs/inputs/edit_SH001_v1.png.b64",
  "input_sha256": "sha256-of-original-image",
  "prompt": "<image1> 用母图作为唯一编辑依据，...",
  "resolution": 512,
  "seed": 42,
  "created_at": "queued_by_colab"
}
```

任务提交顺序：**先上传并验证母图** `jobs/inputs/` → 再写 `jobs/pending/` → Colab GPU 读取 → `images/<id>.png` → `jobs/results/<id>.json` → `queue/events.json`。

未成功上传母图的提示词，只能保存在 `jobs/drafts/`，不可声称已经 GPU 入队。

## 对话与 GPU 的真实边界

**已验证：聊天中的单张母图可以经临时 base64 文本中转上传到 GitHub**，并与优化后的提示词一起进入待办队列，不必再次在 Colab 上传图片。多图批次也优先使用同一方式；受传输大小、附件类型和队列工具限制，若不能完成全部图片数据上传，则会明确报告未上传的文件，再使用 Colab 的批量 ZIP 一次上传兜底。ChatGPT 仍不能远程启动免费 Colab GPU，也不能把任务入队等同于生成成功。

免费 Colab 不作为后台无人值守的 Worker；打开 Notebook，按顺序运行环境单元和批量导入单元，再执行任务单元。生成成功后 PNG 自动保存 GitHub；后台检查 GitHub 事件的 ChatGPT 通知并非实时通知。

**隐私**：仓库目前公开，母图 base64 不是加密；任何人可从仓库恢复原图，不要提交敏感/私密素材。需要隐私请先改为私有仓库。

## 版本范围

- V5：单图/多图 ZIP，自动配对、每图独立/全局规则、一图多改、队列执行、失败记录、完成通知。
- 非 V5：文生图无母图、多参考图、蒙版局部编辑、视频、LoRA、不受限制的 1024+ 分辨率；遇到这些需求单独启用新 workflow，不偷偷改执行类型。
