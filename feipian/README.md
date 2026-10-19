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
