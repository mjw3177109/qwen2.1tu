# Qwen-Image-2.1 图片编辑任务系统 V5

## 快速入口

- [V5 Colab GPU：处理 GitHub 待办和 ZIP 批量包](https://colab.research.google.com/github/mjw3177109/qwen2.1tu/blob/main/Colab_Qwen21_Edit_Batch_V5.ipynb)
- [单图与批量协议](./BATCH_PROTOCOL_V5.md)
- [批量 ZIP 入队脚本](./tools/qwen_batch_ingest.py)
- [待执行任务](./jobs/pending/)
- [任务结果](./jobs/results/)
- [完成/失败事件](./queue/events.json)

## 对话下单

直接把原始母图与中文编辑要求发到当前 ChatGPT 对话。由 ChatGPT 优化提示词、核对母图与任务关系、提交 GitHub。**单图已验证可以把母图从聊天附件转成 base64 文本提交到 GitHub，无需 Colab 二次上传。** 多图批次优先同理；若工具的体积或文件格式限制导致无法传递，会列出失败文件，提供 Colab 一次性 ZIP 入队兜底。

## 当前任务与能力范围

- 首次验证任务：[`edit_20261019_yellowhelmet01`](./jobs/pending/edit_20261019_yellowhelmet01.json)。原始母图已提交，等待 GPU 计算，无需在 Colab 额外上传。
- 已验证：任务队列、文本提示词、母图 GitHub 回读、批量配对器本地校验。
- **未实机验证：免费 Colab T4 上的 Qwen-Image-2.1 完整推理、GPU 显存兼容性和自动 PNG 发布。**
- 免费 Colab 不允许作为长期无人值守的分布式 Worker；ChatGPT 无法远程唤醒 GPU。需你在 Colab 手动运行 GPU 和「执行待办」单元。
- 本仓库是**公开仓库**，母图和生成结果均公开；base64 不加密。不要上传敏感图片。GitHub Token 仅放 Colab Secrets，不写入源码。
