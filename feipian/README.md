# 《废片之城》Q21–Q31（包含最后一张 Q31）

✅ **11 个任务的提示词及母图配对已提交，GitHub Actions 静态检查通过。**

⚠️ **真实 Qwen GPU 推理尚未执行，当前 feipian 目录仍没有 Q21–Q31 的成品 PNG。** 不要把静态检查成功当作出图成功。

**最新一键入口**：[Colab Q21–Q31 完整批次](https://colab.research.google.com/github/mjw3177109/qwen2.1tu/blob/main/feipian/Colab_Q21_Q31.ipynb)

1. 打开 Notebook，在 Colab 中选择 T4 GPU，确认左侧 Secrets 已设置可写 GitHub Token。
2. 点击运行全部。当最后一个单元弹出上传窗口，上传此前给出的 **原始 news.zip**（文件 SHA256 已锁定，防止错传）。
3. 程序按依赖顺序执行共 11 个镜头，逐张将候选图保存在 **feipian/Qxx_*.png**，将执行记录放在 **feipian/results/**。中途 Colab 免费额度断开时，下次可继续未完成镜头。
4. 每张图标记为 **GENERATED_AWAITING_VISUAL_QA**，待检验身份一致性、机位和道具构造。Q25 选择已有的晨光屋顶母图，不谎称新推理。

- [Q21–Q31 提示词及依赖清单](./Q21_Q31_MANIFEST.json)
- [专用批次执行脚本](./run_Q21_Q31_colab.py)
- [CI 静态检查](https://github.com/mjw3177109/qwen2.1tu/actions/workflows/feipian_q21_q31_ci.yml)

## 历史 Q21–Q30 入口

如你只想单独执行前十个镜头，可继续使用 [Q21–Q30 Notebook](./Colab_Q21_Q30.ipynb)、[旧版清单](./Q21_Q30_MANIFEST.json) 和 [旧版运行脚本](./run_Q21_Q30_colab.py)。两个批次共用输出路径，默认不会覆盖已有图。

---

# 《废片之城》Q21–Q30 第三批

此文件夹用于保存第三批真实 Qwen-Image-2.1 输出以及对应的任务、提示词与结果记录。**目前十张 PNG 尚未执行 GPU 生成；不要把提示词入库当作出图完成。**

## 一键执行入口

打开：[Colab Q21–Q30 专用批次](https://colab.research.google.com/github/mjw3177109/qwen2.1tu/blob/main/feipian/Colab_Q21_Q30.ipynb)

选择 T4 GPU → 运行全部 → 在最后一格出现上传窗口时上传原始 `news.zip`。请勿上传之前工具误生成的拼版图片。Colab 脚本会读取已经核对的原始母图、依赖和优化提示词，按依赖顺序运行；每张真正生成或选用的成品自动放在 `feipian/Qxx_*.png`，附 `feipian/results/Qxx_*.json` 质量记录。断线后重新运行会跳过已经上传的文件，不会随意覆盖。

- [Q21-Q30 优化提示词和源图对应关系](./Q21_Q30_MANIFEST.json)
- [GPU 批次执行源码](./run_Q21_Q30_colab.py)
- [静态验证工作流](https://github.com/mjw3177109/qwen2.1tu/actions/workflows/feipian_q21_q30_ci.yml)

特别注意：

1. Q22/Q27 的正俯视、Q30 的多视角手机，需要按照原始提示词重构画面，属于机位/镜头改变。Q23/Q28 采用严格局部插入，其他框景变化依据脚本单图参考实现。
2. Q25 直接使用 ZIP 中同机位的清晨参考 `SCN07_ROOFTOP_DAYBREAK.png`，不会谎称重新运行 Qwen。
3. 使用的是 T4 轻量版单图编辑：`references` 记录的是待核对辅助参考，**目前并非多图条件输入**。输出会标记 `GENERATED_AWAITING_VISUAL_QA`，需要验收人脸、人物数量、动作、场景拓扑后才可认为合格。
4. 上传的 `news.zip` 与图片可能包含创作素材。仓库公开，请确认允许公开使用。GitHub Token 只放 Colab Secrets。
5. ChatGPT 不能远程替你启动免费 Colab 会话，未看到 GPU 真实运行记录前不能报告任务完成。

## 预期生成的十张文件

- `Q21_HALL_CONSOLE_HAND.png`
- `Q22_ROOF_TOP.png`
- `Q23_ROOF_BLOCK_RECORD.png`
- `Q24_ROOF_PHONE_HAND.png`
- `Q25_ROOF_DAWN_MATCH.png`
- `Q26_ROOF_FIFTH_XIAOQI.png`
- `Q27_SCREEN_TOP.png`
- `Q28_SCREEN_BLOCK.png`
- `Q29_SCREEN_LINCHU_CLOSE.png`
- `Q30_PROP_PHONE_SINGLE.png`
