---
name: transcribe-proofread
description: 把音频/视频转成逐字稿（.srt + .txt，带时间戳），再由 Claude 结合上下文校对错字，不确定处标 [?]。首次使用会检测电脑配置、自动安装 faster-whisper 并选默认模型，也可自定义。用户说"转录""逐字稿""字幕""校对转录""transcribe"时使用。
---

# transcribe-proofread：转录 + 校对

单机使用。本 skill 不上传任何音视频，转录全部在本机完成。

## 流程

### 1. 首次安装（只做一次）
运行：
```
python <skill目录>/scripts/setup.py
```
它会：检测显卡/内存/CPU → 推荐默认模型 → 建虚拟环境并安装 faster-whisper（带重试）→ 检查 ffmpeg → 写配置 `~/.transcribe-proofread/config.json`。
- 想自选模型：`python setup.py --model medium`（可选 tiny/base/small/medium/large-v3）。
- 国内网络慢：加 `--mirror`（用清华 pip 镜像，模型走 hf-mirror）。
- 只看推荐不安装：加 `--dry-run`。
- 之后随时可手改配置文件里的 `model`、`language`、`device`、`compute_type`、`hotwords`。

### 2. 转录
```
<venv的python> <skill目录>/scripts/transcribe.py <文件> -o <输出前缀> [--hotwords "词1 词2"] [--lang zh] [--model small]
```
`setup.py` 结束时会打印 venv 的 python 路径。输出 `前缀.srt` 和 `前缀.txt`（txt 每行 `[  秒数] 文字`）。
- 热词用来纠正专有名词（人名、术语），建议问用户要。
- 长音频（>10 分钟）放后台跑，不要阻塞。
- GPU 失败会自动回退 CPU 并提示。

### 3. 校对（可选，消耗 Claude 额度，先问用户）
你听不到音频，只能凭上下文推断，所以必须遵守：
1. 先问用户主题/场景/人名/术语，读转录开头几十行建立语境。
2. 用 `python scripts/proofread_merge.py split 前缀.txt <每段行数=150> <临时目录>` 切成带编号的分段。
3. 逐段校对：**严格 1 行对 1 行，不合并、不拆分、不删行、不增行**。只改明显的错字、同音误识、标点；不润色、不改意思。
4. 没把握的地方在该词后加 `[?]`，不要硬改。用户说不用标的类别（如人名）就别标。
5. 全部校对完后合并：`python scripts/proofread_merge.py merge 前缀.srt <校对后分段目录> 前缀.校对版`，用原时间戳生成 `前缀.校对版.srt/.txt`，并自动校验行数和相似度；对不上就停下来排查，不要交付。
6. 告诉用户：校对是推断不是听写，`[?]` 处请对照原音频确认。

### 4. 分人（实验性，仅在用户要求时）
本 skill 不含声纹分离。如需区分发言人：校对时按内容和语境在行首加 `【角色】`，并说明这是推测、会有误判；需要真正的声纹分离请用户另装 pyannote/whisperx。

## 默认模型规则
| 配置 | 默认 |
|---|---|
| NVIDIA 显存 ≥ 8GB | large-v3 · cuda · int8_float16 |
| NVIDIA 显存 4–8GB | medium · cuda · int8_float16 |
| 仅 CPU，内存 ≥ 16GB | medium · cpu · int8 |
| 仅 CPU，内存 8–16GB | small · cpu · int8 |
| 更低 | base · cpu · int8 |
中文建议至少 small；small 错字较多，质量要求高请用 medium 以上。GPU 路径若未验证成功会自动回退 CPU。

## 注意
- 首次转录会下载模型（small≈0.5GB，large-v3≈3GB）。
- 速度参考（CPU, small）：约 48 分钟音频需 30 分钟左右。
- 机器转写必有错，交付时注明"需人工核对"。
