# Qwen-Image-2.1 编辑图任务队列 V4

## 目标

在聊天里发「母图 + 修改提示词」后，我将任务放进 GitHub；图片计算仍需有实际 GPU 执行环境。完成的 PNG 和可追踪结果信息保存到此仓库。

**注意：Google Colab 免费运行时不能充当长期无人值守的远程 GPU Worker。** Google 官方 FAQ 明确列出免费版限制运行分布式计算 Worker（https://research.google.com/colaboratory/faq.html）。本版本提供**交互式一键执行待办任务**：在 Colab 中点击执行任务格，处理当时已有的任务，并上传结果；不后台轮询空队列、不自动远程启动 Colab。需要真正不经手动启动的全自动，使用自有 RTX 4090、合规的付费/自托管 GPU 服务。

## 运行入口

[打开 Colab V4 队列 Notebook](https://colab.research.google.com/github/mjw3177109/qwen2.1tu/blob/main/Colab_Qwen21_Edit_Queue_V4.ipynb)

- 延用已经配置的 Colab Secrets：`GITHUB_TOKEN`（只给目标仓库的 Contents 读写权限）。
- 运行时选择 GPU，按序执行初始化、安装、下载模型、ComfyUI 启动、建立工作流、任务执行这几个单元。
- 任务执行单元默认处理**最多 3 张待办图片**，之后停止，不持续占用免费 GPU。
- 每次 ChatGPT 提交新任务后，再次手动运行最后一个「处理待办任务」单元。

## 用户之后怎样发任务

直接在当前 ChatGPT 对话上传母图，文字说明修改要求即可。建议格式：

```
修改要求：把蓝色衣服改成黑色皮夹克。
必须保持：人物脸、体型、站位、背景、画风、相机视角不变。
尺寸：512（可选，默认 512）
数量：1（可选，当前每个任务一张）
```

我将把输入图片压缩至适合 Github Contents API 的体积（上传源码仍可能公开），创建以下文件：

```
jobs/
  inputs/<JOB_ID>.jpg.b64    # 母图 JPEG 内容的 base64 文本
  pending/<JOB_ID>.json     # 编辑提示词、输入路径、哈希、分辨率与种子
  results/<JOB_ID>.json     # 执行结果成功/失败、图片 URL 和错误信息
images/<JOB_ID>.png         # 成品图
queue/events.json           # 最近的任务完成/失败通知事件
```

pending 文件示例：

```json
{
  "schema_version": 1,
  "id": "edit_20261019_001",
  "kind": "image_edit",
  "input_b64_path": "jobs/inputs/edit_20261019_001.jpg.b64",
  "input_sha256": "<图片二进制 SHA256>",
  "prompt": "<image1> 保持原图人物和背景不变，将衣服改为黑色。",
  "resolution": 512,
  "seed": 42,
  "created_at": "2026-10-19T01:00:00Z"
}
```

## 如何确认结果

- 待办任务：[jobs/pending](https://github.com/mjw3177109/qwen2.1tu/tree/main/jobs/pending)
- 任务结果：[jobs/results](https://github.com/mjw3177109/qwen2.1tu/tree/main/jobs/results)
- PNG 成品：[images](https://github.com/mjw3177109/qwen2.1tu/tree/main/images)
- 最近结果事件：[queue/events.json](https://github.com/mjw3177109/qwen2.1tu/blob/main/queue/events.json)

成功：`status = "SUCCEEDED"`，附 GitHub 图片链接；失败：`status = "FAILED"`，附错误描述；没有 results 文件：尚未处理或被中断，可重新执行待办。

如果你启用了 ChatGPT 完成通知，计划任务最多按配置频率检查 GitHub 状态一次，**不会即时通知，也不能使 Colab 自动启动**。

## 安全与验收

1. **仓库当前是公开的**：母图（即使 base64 编码）与成品都能被公开访问。base64 不是加密；敏感照片不要这样提交。需要私密时应改成私有仓库并重新核验 Colab Token 权限。
2. Token 只从 Colab Secrets 读取，禁止提交到仓库或写进日志。
3. 模型不上传 GitHub；临时磁盘随 Colab 会话结束而清空。
4. Colab T4 下载的 GGUF 主模型、W4A8 编码器、VAE 总共约 11GB；单卡显存/内存/依赖兼容性**仍需真实运行验收**。
5. 本任务队列采用幂等文件路径，能跳过已经写入 results 的任务；如执行中断，可重新点击最后一个执行单元。
6. 图片结果质量、人脸/构图一致性仍需实际目视审查，不把 GPU 完成等同于视觉验收通过。
