"""检测配置 → 选默认模型 → 建 venv 装 faster-whisper → 写配置。用法见 SKILL.md。"""
import argparse, ctypes, json, os, platform, shutil, subprocess, sys
from pathlib import Path

HOME = Path.home() / ".transcribe-proofread"
VENV = HOME / "venv"
CFG = HOME / "config.json"
MODELS = ["tiny", "base", "small", "medium", "large-v3"]


def ram_gb():
    try:
        if os.name == "nt":
            class M(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("p", ctypes.c_ulong)] + [(n, ctypes.c_ulonglong) for n in ("tp", "ap", "tpf", "apf", "tv", "av", "ae")]
            m = M(); m.l = ctypes.sizeof(M)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.tp / 2**30
        if platform.system() == "Darwin":
            return int(subprocess.check_output(["sysctl", "-n", "hw.memsize"])) / 2**30
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
    except Exception:
        return 8.0


def gpu():
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], text=True, timeout=15)
        name, mem = out.strip().splitlines()[0].rsplit(",", 1)
        return name.strip(), float(mem) / 1024
    except Exception:
        return None, 0.0


def recommend(vram, ram):
    if vram >= 8: return "large-v3", "cuda", "int8_float16"
    if vram >= 4: return "medium", "cuda", "int8_float16"
    if ram >= 16: return "medium", "cpu", "int8"
    if ram >= 8: return "small", "cpu", "int8"
    return "base", "cpu", "int8"


def run(cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    return subprocess.call(cmd)


def pip_install(py, pkgs, mirror):
    base = [str(py), "-m", "pip", "install", "--no-cache-dir", "--default-timeout=300", "--retries", "10"]
    if mirror: base += ["-i", "https://pypi.tuna.tsinghua.edu.cn/simple"]
    for p in pkgs:  # 一个一个装，大包失败不连累其他
        for attempt in range(3):
            if run(base + [p]) == 0: break
            print(f"  {p} 第 {attempt+1} 次失败，重试", flush=True)
        else:
            sys.exit(f"安装 {p} 失败，请检查网络后重跑 setup.py（已装的会跳过）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=MODELS)
    ap.add_argument("--device", choices=["cuda", "cpu"])
    ap.add_argument("--language", default="zh")
    ap.add_argument("--mirror", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    name, vram = gpu(); ram = ram_gb()
    model, device, ctype = recommend(vram, ram)
    print(f"显卡: {name or '无 NVIDIA'} {vram:.0f}GB | 内存: {ram:.0f}GB | 系统: {platform.system()}")
    if a.model: model = a.model
    if a.device:
        device = a.device; ctype = "int8_float16" if device == "cuda" else "int8"
    print(f"选用: model={model} device={device} compute_type={ctype}")
    if a.dry_run: return

    if not shutil.which("ffmpeg"):
        print("⚠ 没找到 ffmpeg（视频转音频需要）。Windows: winget install ffmpeg；mac: brew install ffmpeg；Linux: apt install ffmpeg")
    HOME.mkdir(parents=True, exist_ok=True)
    if not VENV.exists() and run([sys.executable, "-m", "venv", str(VENV)]) != 0:
        sys.exit("创建虚拟环境失败")
    py = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    pkgs = ["av>=15,<16", "faster-whisper"]  # av 新版移除了 faster-whisper 用到的参数，必须限版本
    if device == "cuda": pkgs += ["nvidia-cublas-cu12", "nvidia-cudnn-cu12"]
    pip_install(py, pkgs, a.mirror)

    cfg = {"model": model, "device": device, "compute_type": ctype, "language": a.language,
           "hotwords": "", "mirror": a.mirror}
    CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n安装完成。配置: {CFG}\n转录用的 python: {py}")
    print("首次转录会自动下载模型。想换模型：改配置文件里的 model，或重跑 setup.py --model 名称")


if __name__ == "__main__":
    main()

