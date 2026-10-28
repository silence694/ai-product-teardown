# -*- coding: utf-8 -*-
"""
产品界面图评分器 —— 用于筛掉营销插画/海报/资讯配图

原理：真实产品 UI 截图（后台、工作台、表单、列表、编辑器）有三个稳定特征
  1. 大面积浅色底（白/浅灰）        → light_ratio 高
  2. 低饱和度（灰阶为主，仅少量品牌色）→ sat_ratio 低
  3. 细线结构密集（分割线/边框/文字） → edge_density 中等偏高

营销插画、海报、资讯配图通常饱和色块大、白底占比低，会被判为 low。

用法：
  python pick_ui.py 目录              # 打分排序，输出表格
  python pick_ui.py 目录 --apply      # 把低分图移到 目录/_rejected/
  python pick_ui.py 目录 --min 55     # 自定义及格线（默认 55）
"""
import os, sys, shutil, warnings
from PIL import Image, ImageFilter

warnings.filterwarnings("ignore", category=DeprecationWarning)   # Pillow 11+ 对 getdata 的提示，不影响结果

def score_image(path):
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return None
    if im.width > 900:
        im = im.resize((900, round(im.height * 900 / im.width)))
    px = list(im.getdata())
    n = len(px)
    light = sum(1 for r, g, b in px if r > 228 and g > 228 and b > 228)
    sat_hi = sum(1 for r, g, b in px if max(r, g, b) - min(r, g, b) > 55)
    # 边缘密度：灰度图上求梯度幅度均值
    gray = im.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    ep = list(edges.getdata())
    edge_mean = sum(ep) / len(ep)

    light_ratio = light / n
    sat_ratio = sat_hi / n
    aspect = im.width / im.height

    s = 0
    s += min(light_ratio / 0.45, 1) * 45          # 白底：45 分
    s += max(0, 1 - sat_ratio / 0.30) * 25        # 低饱和：25 分
    s += min(edge_mean / 12, 1) * 20              # 结构密度：20 分
    if 1.1 <= aspect <= 2.4:
        s += 10                                    # 界面常见宽高比
    elif aspect > 2.4:
        s += 4
    return {
        "score": round(s, 1),
        "light": round(light_ratio, 2),
        "sat": round(sat_ratio, 2),
        "edge": round(edge_mean, 1),
        "size": f"{Image.open(path).width}x{Image.open(path).height}",
        "kb": round(os.path.getsize(path) / 1024),
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    d = sys.argv[1]
    apply_ = "--apply" in sys.argv
    thr = 55
    if "--min" in sys.argv:
        thr = float(sys.argv[sys.argv.index("--min") + 1])

    files = sorted(f for f in os.listdir(d)
                   if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))
    rows = []
    for f in files:
        r = score_image(os.path.join(d, f))
        if r:
            r["file"] = f
            rows.append(r)
    rows.sort(key=lambda x: -x["score"])

    print(f"{'文件':44s} {'分':>5s} {'白底':>5s} {'饱和':>5s} {'结构':>5s}  判定")
    print("-" * 86)
    n_ok = 0
    for r in rows:
        ok = r["score"] >= thr
        n_ok += ok
        print(f"{r['file'][:44]:44s} {r['score']:5.1f} {r['light']:5.2f} {r['sat']:5.2f} "
              f"{r['edge']:5.1f}  {'✅ 界面图' if ok else '❌ 非界面（插画/海报/资讯图）'}")

    if apply_:
        rej = os.path.join(d, "_rejected")
        os.makedirs(rej, exist_ok=True)
        moved = 0
        for r in rows:
            if r["score"] < thr:
                shutil.move(os.path.join(d, r["file"]), os.path.join(rej, r["file"]))
                moved += 1
        print(f"\n已移出 {moved} 张低分图 → {rej}")

    print(f"\n合格 {n_ok} / {len(rows)} 张（及格线 {thr}）")


if __name__ == "__main__":
    main()
