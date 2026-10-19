# Qwen-Image-2.1 编辑协议 V5.3：原图优先、范围确认、严格禁止默认整图重绘

**V5.3 从 2026-10-19 起执行。** GitHub 接单 → 确认母图、人物/场景保真需求和编辑范围 → 提交单图或 ZIP → Colab 执行 → 原图保真合成 → GitHub 结果。旧版已经 SUCCEEDED 的图和记录不会覆盖。

## 核心规则（真实代码硬性拦截，不靠提示词承诺）

1. **局部 Qwen 修改**：任务须使用 \`edit_mode=local_patch\` + \`edit_region\` 原图像素坐标（\`crop_box\`、\`polygon\`）；仅把裁剪框传给 Qwen。Qwen 只生成裁剪框，最终仅将 polygon 内的像素合成到 **原始分辨率** 母图上，未选中像素保持完全一致。
2. **纯白帽改黄帽**：\`edit_mode=local_recolor\` + \`edit_region.mode=recolor\` + \`color_transform=white_to_safety_yellow\`，CPU 遮罩改色，不调用 Qwen，也不缩小原始母图。其它颜色变换暂不开放自动执行，避免错改。
3. **没有范围**：禁止模型运行；Colab 会写入 \`jobs/review/<任务ID>.json\`（\`status=NEEDS_REGION\`），提示补齐母图上的坐标。相同未修改任务不会每次重复尝试。
4. **用户明确要求全图风格改变**：必须同时提交 \`edit_mode=full_redraw\`、\`full_redraw_authorized=true\`、\`full_redraw_user_instruction\`（用户真实原话，至少8字符）。没有三者，不能执行整图重绘。只有这个模式允许整图缩小推理。
5. **冲突及边界**：多边形、裁剪区域无效或超出原图、局部选区覆盖原图85%以上，统一阻止。不能把旧流程上传却未验收的图片误认作新的保真成品。
6. **任务执行和完成**：结果分别写入 \`images/<job_id>.png\`、\`jobs/results/<job_id>.json\`，失败尝试写入 \`jobs/attempts/<job_id>.json\`，缺范围写入 \`jobs/review/<job_id>.json\`。GPU 代码仍需用户启动 Colab，不能在聊天中自动唤醒免费 T4。

## 一、单张图任务格式

**局部 Qwen 编辑（改变物体、动作等）：**

\`\`\`json
{
  "schema_version":1,
  "id":"edit_SH001_local_001",
  "kind":"image_edit",
  "input_b64_path":"jobs/inputs/edit_SH001_local_001.jpg.b64",
  "input_sha256":"<原始图片真实 SHA256>",
  "prompt":"<image1> 只修改画面中指定的安全帽区域，人物脸部和其他画面不动。",
  "resolution":512,
  "seed":42,
  "edit_mode":"local_patch",
  "edit_region":{
    "mode":"patch",
    "crop_box":[550,0,1040,310],
    "polygon":[[661,158],[674,122],[674,88],[685,64],[739,26],[963,20],[936,47],[904,58],[863,72],[821,91],[778,113],[728,144],[682,162]],
    "feather":2
  }
}
\`\`\`

**纯局部安全帽改色（当前支持，零人脸重绘）：**

\`\`\`json
{
  "edit_mode":"local_recolor",
  "edit_region":{
    "mode":"recolor",
    "color_transform":"white_to_safety_yellow",
    "polygon":[[661,158],[674,122],[674,88],[685,64],[739,26],[963,20],[936,47],[904,58],[863,72],[821,91],[778,113],[728,144],[682,162]],
    "feather":1.5
  }
}
\`\`\`

以上多边形是**那一张工厂图片**的示范定位，不能套用其他母图。不要把上述示例中带尖括号的 SHA256 当作真实数据上传。

**整图重绘（只有用户明确要求才允许）：**

\`\`\`json
{
  "edit_mode":"full_redraw",
  "full_redraw_authorized":true,
  "full_redraw_user_instruction":"把整张照片重新绘制成油画风格，允许背景和人物细节发生变化"
}
\`\`\`

必须同时保留该任务原本的母图、提示词、seed、resolution 和有效任务 ID。

## 二、批量 ZIP 格式

\`\`\`text
Qwen_Batch/
  sources/
    SH001.jpg
    SH002.png
  prompts/
    SH001.txt
    SH002.txt
  regions/
    SH001.json
    SH002.json
  global_rules.txt
  batch.csv                  # 可选；一图多改或显式整图授权时必用
\`\`\`

不提供 CSV 时，\`sources/SH001.jpg\`、\`prompts/SH001.txt\`、\`regions/SH001.json\` 自动匹配。带 CSV 时可填写：

\`\`\`csv
source,prompt_file,edit_mode,region_file,resolution,seed
sources/SH001.jpg,prompts/SH001.txt,local_patch,regions/SH001.json,512,42
sources/SH002.png,prompts/SH002.txt,local_recolor,regions/SH002.json,512,42
\`\`\`

整图重绘 CSV 另加两列 \`full_redraw_authorized\` 和 \`full_redraw_user_instruction\`，且必须填写用户的真实授权原话。ZIP 内的局部任务缺少 region 文件时会**整批拒绝入队，不会先上传一半**，并告知哪个源图缺少选区。多张图无法准确配对时先发给 ChatGPT 做逐张核对，而不是让程序猜。

## 三、效果和成本界限

- **保留原图**不等于 AI 超分。V5.3 不会凭空生成原图不存在的纹理；可在后续明确提出单独的 1080P/4K 超分任务。
- **遮罩外完全保持原图**可以从像素验证；但遮罩内的人脸/文字若被选中，仍然可能发生变化，所以尽量不要把脸放入 polygon。
- **局部 Qwen 模式仍可能需要在小裁剪框内缩放**以满足 T4 资源限制；它不再默认缩小和重新生成整张照片。
- 仓库公开，因此上传其中的母图、成品和提示词均可能公开访问。敏感照片不要上传到公开仓库。

## 四、真实验收状态

- 原任务 \`edit_20261019_yellowhelmet01\` 的 V5.2 Qwen GPU 输出与 CPU 高清后处理均已成功，旧文件保留。
- V5.3 改动已经在代码层面接入，包含单元测试、Notebook Python 语法检查、像素保护测试和 GitHub Actions 自动 CI。
- **V5.3 尚未在新的真实 Qwen T4 局部编辑任务上完成 GPU 验收**；首次运行需观察日志，不能把 CI 测试当作真实 GPU 生成成功。

[打开 Colab V5.3](https://colab.research.google.com/github/mjw3177109/qwen2.1tu/blob/main/Colab_Qwen21_Edit_Batch_V5.ipynb)

---

## V5.2 人脸锁定与高清局部编辑（2026-10-19）

### 首张实际修复结果

- [原 Qwen2.1 输出：672×384](https://github.com/mjw3177109/qwen2.1tu/blob/main/images/edit_20261019_yellowhelmet01.png) — 成功完成 GPU 工作流，但整张照片被低分辨率重绘；不作为正式交付质量。
- [高清保真输出：1388×808](https://github.com/mjw3177109/qwen2.1tu/blob/main/images/edit_20261019_yellowhelmet01_HQ.png) — GitHub Actions CPU 后处理，基于 **原始 JPG** 的局部安全帽改色，不重新生成任何人脸，外部像素全部保持原样。注意这是后处理，不是第二次 GPU 推理。
- [GitHub Actions 已成功完成](https://github.com/mjw3177109/qwen2.1tu/actions/runs/39216742802)，[质量验收 JSON](https://github.com/mjw3177109/qwen2.1tu/blob/main/jobs/results/edit_20261019_yellowhelmet01_HQ.json)。
- [质量脚本](https://github.com/mjw3177109/qwen2.1tu/blob/main/tools/qwen_preserve_original.py) 支持 `recolor`（CPU 原图局部颜色变更）与 `patch`（Qwen 裁剪编辑图按遮罩贴回原图）。

### 今后图像局部编辑的推荐模式

- **纯颜色、材质色相变化**：优先 `recolor`。用原图 + 精确多边形选区做像素级色彩修改，无需运行 GPU；人脸、设备、构图严格 0 变化。
- **局部替换物体、局部增删物体**：Qwen 使用 `edit_region` 裁剪后的图片生成，仅把 `polygon` 遮罩内部合成到原始分辨率，保留其他部分的原始像素。
- **用户明确要求整体风格变换或改变画面全局结构**：可以仍走整图模式，但不能保证人物脸完全不变。

待办 JSON 中新增可选 `edit_region`：

```json
{
  "edit_region": {
    "mode": "patch",
    "crop_box": [550, 0, 1040, 310],
    "polygon": [[661, 158], [674, 122], [674, 88], [685, 64], [705, 45], [739, 26], [765, 20], [963, 20], [961, 37], [936, 47], [904, 58], [863, 72], [821, 91], [778, 113], [728, 144], [682, 162]],
    "feather": 2.0
  }
}
```

坐标为母图**原始尺寸**的绝对像素坐标。模型只接收 `crop_box` 裁剪区域；Qwen 输出会缩放为该裁剪框大小，并且仅替换 `polygon` 内的像素。上例只是这张工厂母图的定位数据，不能拿去直接套到别的图片。

**真实高清度边界**：保留原图的实际 1388×808 像素；不会凭空产生原图没有的高清细节。若需要进一步超分辨率，可另启独立的超分流程，并逐张核验人脸一致性。

---

## V5.1 补丁（2026-10-19）：修复 Unknown model architecture! 错误

症状：Colab 已下载模型，执行任务时 `UnetLoaderGGUF` 报 `ValueError: This model is not currently supported - (Unknown model architecture!)`。

原因：旧版 `city96/ComfyUI-GGUF` 不识别 Qwen-Image-2.1 的模型架构。已改为 `leejet/ComfyUI-GGUF`，并确保 ComfyUI 服务重启以加载新节点。**不需要更换或重新下载 GGUF/编码器/VAE 权重。**

**如果当前 Colab 会话还在、模型文件还存在**：

在旧的 Notebook 末尾新建一个代码单元，运行：

```python
!curl -fsSL https://raw.githubusercontent.com/mjw3177109/qwen2.1tu/main/tools/repair_qwen21_gguf_colab.py -o /content/repair_qwen21_gguf_colab.py && python /content/repair_qwen21_gguf_colab.py
```

看到 `SUCCESS: leejet/ComfyUI-GGUF` 后，再运行旧 Notebook 的最后一格“执行当前待办队列”，不要重新提交母图。

**如果 Colab 运行时已断开**：

重新打开 <https://colab.research.google.com/github/mjw3177109/qwen2.1tu/blob/main/Colab_Qwen21_Edit_Batch_V5.ipynb>，设置 GPU 后运行全部。这份 Notebook 已是 V5.1，含最新 GGUF、GitHub Contents 写权限实际预检、可重试失败记录。会话重置后临时模型需要重新下载。

成功结果：`images/<job_id>.png`、`jobs/results/<job_id>.json`（status=SUCCEEDED）；运行故障：`jobs/attempts/<job_id>.json`（status=RETRYABLE_FAILED，可重新执行）。如果提示 `HTTP 403`，说明 Colab Secrets 中的 GitHub Token 缺少仓库 Contents: Read and write 或已失效。

**验证边界**：已更新 GitHub 代码并对独立修复脚本做 Python 语法检查；未能远程操作用户的 Colab T4 GPU，需观察实际重跑输出才能确认。

---

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
