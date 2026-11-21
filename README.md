# transcribe-proofread

Claude Code skill：音频/视频 → 逐字稿（.srt + .txt，带时间戳）→ 由 Claude 结合上下文校对错字（不确定处标 `[?]`）。全部在本机转录（faster-whisper），不上传音视频。

## 安装
```bash
git clone https://github.com/programmermars/transcribe-proofread ~/.claude/skills/transcribe-proofread
python ~/.claude/skills/transcribe-proofread/scripts/setup.py
```
Windows 用 `py -3` 代替 `python`，目录 `%USERPROFILE%\.claude\skills\`。需要 Python 3.9+ 和 ffmpeg。

`setup.py` 会检测显卡/内存，推荐默认模型（可用 `--model` 自选，`--dry-run` 只看推荐，`--mirror` 用国内镜像），并建独立 venv 安装 faster-whisper。配置在 `~/.transcribe-proofread/config.json`，可自行修改模型、语言、热词。

## 使用
装好后在 Claude Code 里说“转录 xxx.mp4 并校对”即可，流程见 [SKILL.md](SKILL.md)。

## 说明
- 校对是 Claude 凭上下文推断，听不到音频；`[?]` 处请对照原声确认。
- 不含声纹分人；校对时可按语境标注发言角色（推测，会有误判）。
- 已在 Windows 10 + Python 3.13 + CPU（small 模型）上实测。**GPU（CUDA）路径未经完整验证**，失败会自动回退 CPU。
- 速度参考：CPU + small，约 48 分钟音频用 30 多分钟。

MIT License
