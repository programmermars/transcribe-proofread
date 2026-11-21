"""转录音频/视频 → 前缀.srt + 前缀.txt。读取 ~/.transcribe-proofread/config.json，命令行参数可覆盖。
用 setup.py 装好的 venv 的 python 运行。"""
import argparse, json, os, site, sys, time
from pathlib import Path

CFG = Path.home() / ".transcribe-proofread" / "config.json"


def add_cuda_dlls():
    for sp in site.getsitepackages():
        for sub in ("cublas", "cudnn"):
            d = Path(sp) / "nvidia" / sub / "bin"
            if d.is_dir() and hasattr(os, "add_dll_directory"):
                os.add_dll_directory(str(d))
                os.environ["PATH"] = str(d) + os.pathsep + os.environ["PATH"]


def srt_time(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"


def load_model(cfg):
    from faster_whisper import WhisperModel
    if cfg["device"] == "cuda":
        try:
            m = WhisperModel(cfg["model"], device="cuda", compute_type=cfg["compute_type"])
            return m, "cuda"
        except Exception as e:
            print(f"GPU 不可用，改用 CPU：{e}", flush=True)
            cfg["compute_type"] = "int8"
    return WhisperModel(cfg["model"], device="cpu", compute_type="int8"), "cpu"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("media")
    ap.add_argument("-o", "--out", help="输出前缀，默认与媒体同名")
    ap.add_argument("--model"); ap.add_argument("--lang"); ap.add_argument("--hotwords")
    a = ap.parse_args()

    cfg = {"model": "small", "device": "cpu", "compute_type": "int8", "language": "zh", "hotwords": ""}
    if CFG.exists():
        cfg.update(json.loads(CFG.read_text(encoding="utf-8")))
    if a.model: cfg["model"] = a.model
    if a.lang: cfg["language"] = a.lang
    if a.hotwords is not None: cfg["hotwords"] = a.hotwords
    out = a.out or str(Path(a.media).with_suffix(""))
    if cfg.get("mirror"): os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

    add_cuda_dlls()
    t0 = time.time()
    model, dev = load_model(cfg)
    print(f"模型 {cfg['model']} ({dev}) 已加载，{time.time()-t0:.0f}s", flush=True)
    lang = cfg["language"]
    prompt = "以下是普通话的句子，使用简体中文。" if lang == "zh" else None
    hw = cfg["hotwords"] or None
    segs, info = model.transcribe(a.media, language=lang, initial_prompt=(prompt + (f"关键词：{hw}。" if hw else "")) if prompt else None,
                                  hotwords=hw, vad_filter=True)
    srt, txt = [], []
    for i, s in enumerate(segs, 1):
        text = s.text.strip()
        srt.append(f"{i}\n{srt_time(s.start)} --> {srt_time(s.end)}\n{text}\n")
        txt.append(f"[{s.start:7.1f}] {text}")
        if i % 50 == 0:
            print(f"  已转到 {s.end:.0f}s / {info.duration:.0f}s", flush=True)
    Path(f"{out}.srt").write_text("\n".join(srt), encoding="utf-8")
    Path(f"{out}.txt").write_text("\n".join(txt), encoding="utf-8")
    print(f"完成：{len(srt)} 句，音频 {info.duration:.0f}s，耗时 {time.time()-t0:.0f}s（机器转写，需人工核对）\n→ {out}.srt / {out}.txt", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
