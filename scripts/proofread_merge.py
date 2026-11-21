"""校对辅助：split 把 txt 切成分段供逐行校对；merge 把校对后的文字按原 srt 时间戳合并回去并校验。

  python proofread_merge.py split 原.txt [每段行数=150] [输出目录=原名_分段]
      → 输出目录/part_001.txt …（每行格式不变：[秒数] 文字）。校对时每个文件逐行改字，行数必须不变。
  python proofread_merge.py merge 原.srt 校对后分段目录 输出前缀
      → 输出前缀.srt / 输出前缀.txt（时间戳沿用原 srt）。
"""
import difflib, re, sys
from pathlib import Path

PREFIX = re.compile(r"^\[\s*[\d.]+\]\s?")


def read_lines(p):
    return [l for l in Path(p).read_text(encoding="utf-8").split("\n") if l.strip()]


def split(txt, n=150, outdir=None):
    lines = read_lines(txt)
    outdir = Path(outdir or str(Path(txt).with_suffix("")) + "_分段")
    outdir.mkdir(parents=True, exist_ok=True)
    for k in range(0, len(lines), n):
        (outdir / f"part_{k//n+1:03d}.txt").write_text("\n".join(lines[k:k + n]), encoding="utf-8")
    print(f"共 {len(lines)} 行，切成 {-(-len(lines)//n)} 段 → {outdir}")


def merge(srt, partdir, out):
    blocks = [b for b in re.split(r"\n\s*\n", Path(srt).read_text(encoding="utf-8").strip()) if b.strip()]
    orig = []
    for b in blocks:
        ls = b.split("\n")
        orig.append((ls[0], ls[1], "\n".join(ls[2:]).strip()))
    fixed = []
    for f in sorted(Path(partdir).glob("part_*.txt")):
        fixed += read_lines(f)
    if len(fixed) != len(orig):
        sys.exit(f"行数不一致：原 {len(orig)} 行，校对后 {len(fixed)} 行。不能合并——请找出被合并/拆分/漏掉的行。")
    out_srt, out_txt, low = [], [], []
    for i, ((idx, tm, old), new) in enumerate(zip(orig, fixed), 1):
        new = PREFIX.sub("", new).strip()
        sim = difflib.SequenceMatcher(None, old.replace("[?]", ""), new.replace("[?]", "")).ratio()
        if sim < 0.5: low.append((i, old, new, sim))
        out_srt.append(f"{idx}\n{tm}\n{new}\n")
        start = float(tm.split(" --> ")[0].replace(",", ".").split(":")[0]) * 3600 + float(tm.split(" --> ")[0].replace(",", ".").split(":")[1]) * 60 + float(tm.split(" --> ")[0].replace(",", ".").split(":")[2])
        out_txt.append(f"[{start:7.1f}] {new}")
    Path(f"{out}.srt").write_text("\n".join(out_srt), encoding="utf-8")
    Path(f"{out}.txt").write_text("\n".join(out_txt), encoding="utf-8")
    print(f"已合并 {len(orig)} 行 → {out}.srt / {out}.txt；标 [?] 的行 {sum('[?]' in l for l in out_txt)}")
    if low:
        print(f"⚠ {len(low)} 行与原文相似度<0.5，请确认没有错位：")
        for i, o, n, s in low[:20]: print(f"  #{i} ({s:.2f}) {o}  →  {n}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "split": split(a[1], int(a[2]) if len(a) > 2 else 150, a[3] if len(a) > 3 else None)
    elif len(a) == 4 and a[0] == "merge": merge(a[1], a[2], a[3])
    else: sys.exit(__doc__)
