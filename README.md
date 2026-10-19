# Qwen-Image-2.1 图片编辑任务系统 V5.3

**默认原图保真 + 局部编辑 + 缺区域阻止执行 + 用户明确授权才整图重绘。**

## 快速入口

- [Colab V5.3：GitHub 待办任务 / ZIP 批量处理](https://colab.research.google.com/github/mjw3177109/qwen2.1tu/blob/main/Colab_Qwen21_Edit_Batch_V5.ipynb)
- [完整 V5.3 协议、区域 JSON 和 batch.csv 示例](./BATCH_PROTOCOL_V5.md)
- [批量 ZIP 入队脚本](./tools/qwen_batch_ingest.py)
- [硬性区域保护策略](./tools/qwen_v53_policy.py)
- [母图局部像素保真合成](./tools/qwen_preserve_original.py)
- [尚未执行的任务](./jobs/pending/)
- [需人工确认区域](./jobs/review/)
- [任务成功结果](./jobs/results/)
- [可重试失败记录](./jobs/attempts/)
- [成品 PNG](./images/)
- [自动回归测试](https://github.com/mjw3177109/qwen2.1tu/actions/workflows/qwen_v53_ci.yml)

## 对话下单：只需要发母图和修改要求

在 ChatGPT 对话中发原图、中文修改要求，或同时上传 ZIP。ChatGPT 负责母图/提示词匹配、改写成 Qwen 可理解的局部编辑指令、判断需要改的区域是否足够明确。**语义上的“只改帽子”并不等于准确的像素坐标**：在没有坐标区域之前，系统只会标记 NEEDS_REGION，不会让 Qwen 猜选区后重绘整张图。

- **local_patch（局部 Qwen）**：必须有原图坐标的 crop_box 与 polygon，只将裁剪框送给 Qwen，生成结果用 polygon 遮罩贴回原图大小，遮罩外原像素不变。
- **local_recolor（局部无损改色）**：目前只内置 white_to_safety_yellow，CPU 精准改色、不调用 Qwen。
- **full_redraw（整图重绘）**：必须有 full_redraw_authorized=true，且保存用户明确要求全图重绘的原始指令；否则禁止。
- **无坐标/歧义**：批量 ZIP 在入队前拒绝；已经进入待办目录的旧任务在 Colab 中写入 jobs/review/<id>.json，等待人工补充坐标。不会静默执行整图。

## 目前已验证

- 首张 Qwen2.1 GPU 编辑 [edit_20261019_yellowhelmet01](./images/edit_20261019_yellowhelmet01.png) 的原任务状态为 SUCCEEDED；该旧版整图模式造成面容变形和分辨率降低，不推荐沿用。
- [原图保真高清版](./images/edit_20261019_yellowhelmet01_HQ.png) 已由 GitHub Actions 真正生成、上传并验收，采用局部 CPU 改色保留 1388×808 原图，不是第二次 Qwen GPU 推理。
- V5.3 的区域策略、ZIP 入队校验、Notebook Python 语法和遮罩外像素一致性已通过 GitHub Actions 自动测试。
- **V5.3 新的真实 T4 局部 Qwen 裁剪推理尚待验收**。代码通过 CI 不代表已经在 Colab GPU 上跑完新模式。

## 使用提醒

GitHub Token 只放在 Colab Secrets 里（名称 GITHUB_TOKEN），不要放进仓库或截图。免费 Colab GPU 仍需手动启动，ChatGPT 无法直接远程启动它。该仓库公开：母图、成品和提示词均可被外部查看；base64 不是隐私保护。
