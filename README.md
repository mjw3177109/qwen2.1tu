# Qwen-Image-2.1 编辑图片 · Google Colab 免费 GPU

使用 Google Colab（免费 GPU 资源视可用性而定）执行 Qwen-Image-2.1-Turbo 单图编辑，生成的 PNG 自动上传到本仓库的 `images/` 文件夹。

## 运行

[在 Google Colab 打开 Notebook](https://colab.research.google.com/github/mjw3177109/qwen2.1tu/blob/main/Colab_Qwen21_Edit_GitHub_AutoPush.ipynb)

1. 在 GitHub 创建 **Fine-grained personal access token**，仅授权本仓库 `mjw3177109/qwen2.1tu` 的 **Contents: Read and write**。不需要提供给 ChatGPT。
2. 在 Colab 左侧「🔑 Secrets」创建名称 `GITHUB_TOKEN`，将 Token 放入值，并打开允许 Notebook 访问的开关。
3. Colab「运行时 → 更改运行时类型 → GPU」，然后从上往下执行所有单元格。
4. 上传 PNG/JPG/WEBP 原图，修改提示词，运行编辑；生成的图片自动发布到仓库 `images/` 下。

## 重要说明

- **当前无法从 ChatGPT 远程启动或保持你的 Colab 运行时**。Notebook 必须在你自己登录的 Colab 页面运行。
- 使用量化 GGUF Q4 主模型 + W4A8 文本编码器 + VAE；下载总量约 11 GB（不包含运行时依赖）。
- 这是低显存方案，**尚未经 Colab 免费 T4 实机验收**。T4 系统内存、显存、GPU 配额及量化编码器兼容性可能导致失败。
- 不包含 LoRA，也不上传大模型、Token 或原始图片到 GitHub；只提交生成结果。
- **仓库目前是公开的**，自动上传的图片也会公开。不要上传任何不愿公开的内容。
- 上传 GitHub 有文件大小限制，单张 PNG 需低于 100 MiB，且建议小于 20 MiB。
- 模型受到原作者许可证约束；商用前核实 Qwen Research License。

## 目录

```
Colab_Qwen21_Edit_GitHub_AutoPush.ipynb
README.md
images/      # 首次成功生成并上传后自动出现
```
