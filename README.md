# Qwen-Image-2.1 图片编辑与 GitHub 自动归档

## 推荐入口：V4 任务队列

[打开 Colab V4 任务队列 Notebook](https://colab.research.google.com/github/mjw3177109/qwen2.1tu/blob/main/Colab_Qwen21_Edit_Queue_V4.ipynb)

操作说明与真实限制：[QUEUE_GUIDE.md](./QUEUE_GUIDE.md)。

**期望工作流**：你在 ChatGPT 上传母图并给出中文修改提示词 → ChatGPT 创建 `jobs/pending/<任务ID>.json` 和对应母图数据 → 交互式打开 Colab 后点击运行 → Colab 自动读取队列、编辑图片、把 PNG 上传到 `images/` 并写 `jobs/results/` → 配置的 ChatGPT 定时检查任务发现新结果后通知你。

> ⚠️ 免费 Colab 不能被 ChatGPT 远程启动为长期后台 Worker，Google 官方明确限制免费 Colab 运行分布式计算 Worker。Notebook 只执行当前队列，不会后台无限轮询。要实现发送后完全无人干预，需要自有常开 GPU（例如 RTX 4090）或合规的付费 GPU 服务。
>
> ⚠️ 仓库是 **public**：包括母图的 base64 文本、编辑成品与任务提示词全部公开。不要用于私密素材。
>
> ⚠️ Qwen-Image-2.1 量化推理尚未通过免费 Colab T4 实机端到端验证。GPU/内存不足或扩展节点兼容问题都可能导致失败，结果文件会记录失败原因。

### GitHub 目录

```text
Colab_Qwen21_Edit_Queue_V4.ipynb
Colab_Qwen21_Edit_GitHub_AutoPush.ipynb  # 原 V3，保留
QUEUE_GUIDE.md
jobs/
  inputs/
  pending/
  results/
queue/events.json
images/  # 第一张成品成功上传后创建
```

### 原始单图手动编辑版

[打开原版 Colab Notebook](https://colab.research.google.com/github/mjw3177109/qwen2.1tu/blob/main/Colab_Qwen21_Edit_GitHub_AutoPush.ipynb)

保留原版以兼容你的既有设置，不覆盖原有功能。两版均使用 Colab Secrets `GITHUB_TOKEN`。
