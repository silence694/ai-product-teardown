# -*- coding: utf-8 -*-
"""
单篇 AI 产品拆解 → 图文并茂单文件 HTML

用法：
    python teardown_build.py spec/xxx.json          # 生成 HTML
    python teardown_build.py spec/xxx.json --check  # 只做体检，不生成
    python teardown_build.py --init 产品名 2026-10-21   # 生成空白 spec 脚手架

spec 里的图片路径相对于 spec 文件所在目录。输出 HTML 与 spec 同目录，
文件名 = spec 里的 out 字段（默认按标题+日期自动生成）。
"""
import os, sys, json, html, base64, io, re, datetime

try:
    from PIL import Image
except ImportError:
    Image = None

# ============ 图片 ============
MAX_W = 1600          # 单图最大宽度（2x 截图缩到此宽度仍清晰）
TARGET_KB = 420       # 单图压缩目标


def embed_image(path, warn):
    """读图 → 缩放 → webp 压缩 → data URI。失败则原样 base64。"""
    if not os.path.exists(path):
        warn.append(f"图片缺失：{path}")
        return ""
    raw = open(path, "rb").read()
    if Image is None:
        ext = os.path.splitext(path)[1].lstrip(".").lower() or "png"
        return f"data:image/{ext};base64," + base64.b64encode(raw).decode()
    try:
        im = Image.open(io.BytesIO(raw))
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        for q in (90, 82, 74, 66):
            buf = io.BytesIO()
            im.save(buf, "WEBP", quality=q, method=4)
            if len(buf.getvalue()) <= TARGET_KB * 1024 or q == 66:
                break
        return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        warn.append(f"图片处理失败 {os.path.basename(path)}：{e}")
        ext = os.path.splitext(path)[1].lstrip(".").lower() or "png"
        return f"data:image/{ext};base64," + base64.b64encode(raw).decode()


# ============ 文本 ============
def T(s):
    """允许内嵌 <mark class="key"> / <b> / <sup> 等少量标签，其余转义。"""
    s = s or ""
    keep = re.findall(r'<(?:mark|b|sup|a|br)\b.*?</(?:mark|b|sup|a)>|</?br\s*/?>', s)
    s = html.escape(s, quote=False)
    for k in keep:
        s = s.replace(html.escape(k, quote=False), k, 1)
    return s


def cite(ns):
    if not ns:
        return ""
    return "".join(f'<sup><a href="#cite-{n}">{n}</a></sup>' for n in ns)


def src_tag(s):
    return f'<span class="src-tag">{T(s)}</span>' if s else ""


# ============ 区块渲染 ============
def render_block(b, base_dir, warn, fig_no):
    t = b.get("t")
    ns = b.get("cite")

    if t == "lead":
        return f'<p class="lead">{T(b["text"])}{cite(ns)}</p>'
    if t == "p":
        return f'<p>{T(b["text"])}{cite(ns)}</p>'
    if t == "h3":
        return f'<h3>{T(b["text"])}</h3>'

    if t == "list":
        items = "".join(f"<li>{T(i)}</li>" for i in b["items"])
        return f'<ul class="bullet">{items}</ul>'

    if t == "metrics":
        cells = "".join(
            f'<div class="metric"><div class="m-val">{T(m["val"])}</div>'
            f'<div class="m-label">{T(m["label"])}</div></div>'
            for m in b["items"])
        return f'<div class="metrics">{cells}</div>'

    if t == "callout":
        color = " blue" if b.get("color") == "blue" else ""
        return (f'<div class="callout{color}"><div class="ct-title">{T(b["title"])}</div>'
                f'{T(b["text"])}{cite(ns)}</div>')

    if t == "flow":
        parts = []
        for i, s in enumerate(b["steps"]):
            if i:
                parts.append('<div class="arrow">→</div>')
            parts.append(
                f'<div class="step"><div class="step-idx">STEP {i+1}</div>'
                f'<div class="step-t">{T(s["t"])}</div>'
                f'<div class="step-d">{T(s.get("d",""))}</div></div>')
        return f'<div class="flow">{"".join(parts)}</div>'

    if t == "cards":
        items = "".join(
            f'<li class="feat-card"><div class="fc-t"><span class="ic">{T(c.get("ic","·"))}</span>'
            f'{T(c["t"])}</div><p>{T(c.get("p",""))}{cite(c.get("cite"))}</p></li>'
            for c in b["items"])
        return f'<ul class="feat-grid">{items}</ul>'

    if t == "table":
        head = "".join(f"<th>{T(h)}</th>" for h in b["head"])
        body = "".join(
            "<tr>" + "".join(f"<td>{T(c)}</td>" for c in row) + "</tr>"
            for row in b["rows"])
        return (f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
                f"<tbody>{body}</tbody></table></div>")

    if t == "takeaways":
        items = "".join(
            f'<div class="tk"><div class="tk-n">{i+1}</div>'
            f'<div class="tk-t">{T(k["t"])}</div><p>{T(k.get("p",""))}</p></div>'
            for i, k in enumerate(b["items"]))
        return f'<div class="takeaway">{items}</div>'

    if t in ("fig", "figs"):
        figs = [b] if t == "fig" else b["items"]
        cards = []
        for f in figs:
            fig_no[0] += 1
            n = fig_no[0]
            src = embed_image(os.path.join(base_dir, f["img"]), warn)
            cap = f.get("cap", "")
            cap = cap if cap else "界面截图"
            kind = f.get("kind", "ui")
            cards.append(
                f'<figure class="diagram{" shot-news" if kind == "news" else ""}">'
                f'<img src="{src}" alt="{T(f.get("alt", cap))}" loading="lazy">'
                f'<figcaption><span class="fig-no">图 {n}</span>{T(cap)}{cite(f.get("cite"))}{src_tag(f.get("src"))}</figcaption>'
                f"</figure>")
        if t == "fig" or len(cards) == 1:
            return "".join(cards)
        cols = b.get("cols", 2)
        cls = "figure-row" if cols == 2 else "figure-grid"
        return f'<div class="{cls}">{"".join(cards)}</div>'

    if t == "html":
        return b["raw"]

    warn.append(f"未知区块类型：{t}")
    return ""


# ============ 模板 ============
_HERE = os.path.dirname(os.path.abspath(__file__))
_CSS_CANDS = [
    os.path.join(_HERE, "..", "assets", "teardown.css"),   # skill 内标准位置
    os.path.join(_HERE, "teardown.css"),                   # 脚本同级
    os.path.join(_HERE, "_teardown.css"),                  # 旧命名
]
CSS = ""
for _p in _CSS_CANDS:
    if os.path.exists(_p):
        CSS = open(_p, encoding="utf-8").read()
        break
if not CSS:
    print("[警告] 未找到样式文件 teardown.css，输出的 HTML 会没有排版")

HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}｜{product}</title>
<style>{css}</style>
</head>
<body>

<header class="cover">
  <div class="container">
    <span class="badge"><span class="dot"></span>{badge}</span>
    <h1>{h1}</h1>
    <p class="sub">{sub}</p>
    <div class="meta">{meta}</div>
  </div>
</header>

<main class="container">
{pcard}
{narrative}
{sections}
</main>

<footer>
  <div class="container">
    <h2>数据来源</h2>
    <div class="sources"><ol>{sources}</ol></div>
    <p class="foot-note">{footnote}</p>
  </div>
</footer>

</body></html>
"""


def build(spec_path, check_only=False):
    spec_path = os.path.abspath(spec_path)
    base_dir = os.path.dirname(spec_path)
    spec = json.load(open(spec_path, encoding="utf-8"))
    warn = []
    fig_no = [0]

    title = spec.get("title", "AI产品拆解")
    product = spec.get("product", "")
    badge = spec.get("badge", "每日AI产品拆解 · 每日一更")

    grad = spec.get("title_grad", "")
    h1 = f'{T(title)} <span class="grad">{T(grad)}</span>' if grad else T(title)

    meta = "".join(f'<span>{T(m["k"])} <b>{T(m["v"])}</b></span>' for m in spec.get("meta", []))

    pcard = ""
    if spec.get("product_card"):
        cells = "".join(
            f'<div class="pc-item"><div class="pc-label">{T(c["label"])}</div>'
            f'<div class="pc-value{" small" if len(c.get("value","")) > 26 else ""}">'
            f'{T(c["value"])}{cite(c.get("cite"))}</div></div>'
            for c in spec["product_card"])
        pcard = f'<div class="product-card">{cells}</div>'

    narrative = ""
    if spec.get("narrative"):
        narrative = "".join(render_block(b, base_dir, warn, fig_no)
                            for b in spec["narrative"])

    secs = []
    for i, s in enumerate(spec.get("sections", []), 1):
        blocks = "".join(render_block(b, base_dir, warn, fig_no) for b in s.get("blocks", []))
        num = f'<span class="num">{s.get("num","")}</span>' if s.get("num") else ""
        secs.append(
            f'<section id="{s.get("id", f"sec{i}")}">'
            f'<div class="section-label">{T(s.get("label",""))}</div>'
            f'<h2>{num}{T(s.get("h2",""))}</h2>{blocks}</section>')

    sources = "".join(
        f'<li id="cite-{s["n"]}"><span class="src-title">{T(s["title"])}</span>'
        f'<span class="src-url"><a href="{html.escape(s["url"], quote=True)}" target="_blank" rel="noopener">'
        f'{html.escape(s["url"], quote=False)}</a></span></li>'
        for s in spec.get("sources", []))

    out_html = HTML_TPL.format(
        title=T(title), product=T(product), css=CSS, badge=T(badge), h1=h1,
        sub=T(spec.get("sub", "")), meta=meta, pcard=pcard, narrative=narrative,
        sections="".join(secs), sources=sources,
        footnote=T(spec.get("footnote", "")))

    # ---- 体检 ----
    n_news = len(re.findall(r'class="diagram shot-news"', out_html))
    print(f"[体检] 章节 {len(secs)} ｜ 图片 {fig_no[0]} 张 ｜ 其中资讯类 {n_news} 张")
    if fig_no[0] < 6:
        warn.append(f"图片只有 {fig_no[0]} 张，规范要求 ≥ 8 张产品界面截图")
    if n_news > max(1, fig_no[0] // 4):
        warn.append(f"资讯类截图 {n_news} 张偏多（应 ≤ 总数的 1/4），请换成产品功能界面截图")
    if not check_only:
        out = spec.get("out") or f"AI产品拆解_{product or title}_{spec.get('date','')}.html".replace(" ", "")
        out_path = os.path.join(base_dir, out)
        open(out_path, "w", encoding="utf-8").write(out_html)
        print(f"[完成] {out_path}  ({len(out_html)/1024/1024:.1f} MB)")
    for w in warn:
        print("[警告]", w)
    return 0 if not warn else 1


SCAFFOLD = {
    "title": "产品名", "title_grad": "本次重点", "product": "产品名",
    "date": "YYYY-MM-DD", "badge": "每日AI产品拆解 · 每日一更",
    "sub": "一句话说清这次拆什么、为什么值得拆（2-3 句）。",
    "meta": [{"k": "日期", "v": "YYYY-MM-DD"}, {"k": "产品", "v": ""},
             {"k": "厂商", "v": ""}, {"k": "类型", "v": "平台型 AI 产品"}],
    "product_card": [
        {"label": "产品定位", "value": ""},
        {"label": "本次更新", "value": ""},
        {"label": "上线时间", "value": ""},
        {"label": "用户规模", "value": ""},
        {"label": "核心模型", "value": ""},
        {"label": "分发渠道", "value": ""},
    ],
    "narrative": [
        {"t": "lead", "text": "为什么今天拆它：热点事件 + 为什么值得拆。", "cite": [1]},
        {"t": "metrics", "items": [{"val": "—", "label": "指标说明"}]},
        {"t": "fig", "img": "shots/01_home.png", "cap": "产品官网首屏", "src": "官方产品页"}
    ],
    "sections": [
        {"id": "f1", "num": "01", "label": "Core Feature 01 · 核心功能", "h2": "功能名",
         "blocks": [
             {"t": "h3", "text": "功能是什么"},
             {"t": "p", "text": "描述。", "cite": [1]},
             {"t": "figs", "cols": 2, "items": [
                 {"img": "shots/02.png", "cap": "功能界面 A", "src": "官方产品页"},
                 {"img": "shots/03.png", "cap": "功能界面 B", "src": "官方帮助文档"}]}
         ]}
    ],
    "sources": [{"n": 1, "title": "来源标题", "url": "https://"}],
    "footnote": "本拆解为公开信息整理，截图为公开发布会/官网/官方文档的产品界面图。"
}


def init_spec(name, date):
    """脚手架默认落在「当前工作目录/spec」，不污染 skill 目录。"""
    d = os.path.join(os.getcwd(), "spec")
    os.makedirs(os.path.join(d, "shots"), exist_ok=True)
    slug = re.sub(r"[^\w\u4e00-\u9fa5]+", "_", f"{name}_{date}")
    p = os.path.join(d, slug + ".json")
    s = json.loads(json.dumps(SCAFFOLD, ensure_ascii=False))
    s["title"] = s["product"] = name
    s["date"] = date
    s["meta"][0]["v"] = date
    s["meta"][1]["v"] = name
    json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("已生成脚手架：", p)
    print("截图目录：", os.path.join(d, "shots"))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--init":
        init_spec(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else str(datetime.date.today()))
    elif len(sys.argv) >= 2:
        sys.exit(build(sys.argv[1], "--check" in sys.argv))
    else:
        print(__doc__)
