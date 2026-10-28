# spec.json 与抓图配置语法

## 一、文件分布

```
<工作目录>/
├── spec/
│   ├── <产品名>_<YYYY-MM-DD>.json      ← 内容结构（本文档主角）
│   ├── _capture.json                   ← 抓图配置
│   ├── shots/                          ← 截图，序号即出现顺序
│   │   ├── 01_资产市场.png
│   │   └── 02_创建单智能体.png
│   └── <产品名>_<YYYY-MM-DD>.html      ← 产物
```

`spec.json` 里的图片路径**相对于 spec 文件所在目录**，所以写 `shots/01_xxx.png`。
`--init` 会在当前工作目录创建 `spec/` 与 `spec/shots/`。

---

## 二、spec.json 顶层字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `title` | ✅ | 主标题，不含渐变部分 |
| `title_grad` | | 标题后半段，带渐变色（如「两条路径」） |
| `product` | ✅ | 产品名，用于 `<title>` 与默认输出文件名 |
| `date` | ✅ | `YYYY-MM-DD` |
| `badge` | | Cover 上的小徽标，默认「每日AI产品拆解 · 每日一更」 |
| `sub` | ✅ | 封面摘要，2-3 句，回答「拆什么、为什么值得拆」 |
| `meta` | | Cover 元信息 chips，`[{k, v}]`，建议 4-5 条 |
| `product_card` | | Product Card 六格，`[{label, value, cite?}]`，**固定 6 条** |
| `narrative` | ✅ | Overview 区块数组 |
| `sections` | ✅ | 正文章节数组，5-6 个 |
| `sources` | ✅ | 数据来源，`[{n, title, url}]`，`n` 从 1 连续编号 |
| `footnote` | | Footer 免责说明 |
| `out` | | 输出文件名；不写则自动 `AI产品拆解_<product>_<date>.html` |

`cite` 字段统一是**来源编号数组**，如 `[1, 3]`，渲染成上标链接指到 Footer。

---

## 三、区块类型（blocks）

`narrative` 与每个 section 的 `blocks` 都用同一套区块。

### 文本型

```json
{ "t": "lead",  "text": "开篇导语，字号更大", "cite": [1] }
{ "t": "p",     "text": "正文段落", "cite": [2, 3] }
{ "t": "h3",    "text": "小节标题" }
{ "t": "list",  "items": ["要点一", "要点二"] }
```

`text` 里可用 `<mark class="key">关键词</mark>` 做蓝色高亮、`<b>` 加粗、`<sup>` 上标。其余标签会被转义。
**每章 1-2 处高亮即可，满屏高亮等于没高亮。**

### 指标卡

```json
{ "t": "metrics", "items": [
  { "val": "4 类",  "label": "预置智能体模板" },
  { "val": "3 层",  "label": "记忆与上下文管理" },
  { "val": "1200+", "label": "插件市场工具数" },
  { "val": "GA",    "label": "2025 年商用状态" }
]}
```

固定 4 个，`val` 要短（≤8 字），`label` 说明这是什么。

### 提示框

```json
{ "t": "callout", "title": "值得注意的设计取舍", "color": "blue",
  "text": "正文，可用 <mark class=\"key\">高亮</mark>。", "cite": [4] }
```

`color` 省略为橙色（警示/强调），`"blue"` 为蓝色（洞察/解释）。

### 流程四步

```json
{ "t": "flow", "steps": [
  { "t": "输入", "d": "用户消息 + 会话上下文" },
  { "t": "规划", "d": "拆解为子任务并选工具" },
  { "t": "执行", "d": "调用插件，失败可重规划" },
  { "t": "回写", "d": "结果入记忆，返回用户" }
]}
```

3-4 步最佳，每步 `d` 不超过 20 字。

### 卡片网格

```json
{ "t": "cards", "items": [
  { "ic": "◈", "t": "可视化编排", "p": "拖拽节点，连线处映射变量", "cite": [2] },
  { "ic": "◇", "t": "代码模式",   "p": "导出 SDK，本地调试" }
]}
```

`ic` 建议用几何符号（◈ ◇ ○ ● ▣ ✦ →），不要用 emoji。

### 表格

```json
{ "t": "table",
  "head": ["能力", "本产品", "竞品 A", "竞品 B"],
  "rows": [
    ["可视化编排", "支持，节点级调试", "支持，无单节点调试", "不支持"],
    ["效果评估",   "一级导航，评测集", "二级菜单，仅回放",  "无"]
  ]}
```

单元格里**不要只写「支持/不支持」**，要带一句差异说明。

### 方法论（Takeaways 专用）

```json
{ "t": "takeaways", "items": [
  { "t": "评估能力是 Agent 平台的分水岭",
    "p": "证据 + 可迁移条件，100-150 字。" },
  { "t": "把插件当软件包管，而不是一段配置", "p": "…" },
  { "t": "抽象层级越高，调试能力越不能省", "p": "…" }
]}
```

固定 3 条，标题即主张，`p` 里给证据。

### 图片

单张：

```json
{ "t": "fig", "img": "shots/01_资产市场.png",
  "cap": "资产市场 · 卡片流：每张卡标付费/鉴权/工具数三个状态",
  "src": "华为云官方文档 · 用户指南", "cite": [5] }
```

多张并排：

```json
{ "t": "figs", "cols": 2, "items": [
  { "img": "shots/02_创建.png", "cap": "创建页：左栏四个必填项，右栏实时预览",
    "src": "华为云官方文档", "cite": [5] },
  { "img": "shots/03_对话创建.png", "cap": "对话式创建：一句描述自动生成配置项",
    "src": "华为云官方文档", "cite": [6] }
]}
```

| 字段 | 说明 |
|---|---|
| `img` | 相对 spec 目录的路径 |
| `cap` | 图注，按「页面 + 控件 + 含义」三段式写，≤60 字 |
| `src` | 来源标签（显示在图注右侧），如「华为云官方文档 · 用户指南」 |
| `kind` | `ui`（默认）/ `news`。标 `news` 会被计入体检的「资讯类」统计 |
| `alt` | 无障碍文本，省略则用 `cap` |

`cols: 2` 渲染成左右两栏（适合对比图），`cols: 3` 渲染成三宫格（适合功能集合）。

### 原生 HTML 兜底

```json
{ "t": "html", "raw": "<div class=\"whatever\">…</div>" }
```

仅用于现有区块类型表达不了的版式。用了它意味着样式要自己保证，慎用。

---

## 四、完整骨架

```json
{
  "title": "智果 AgentArts",
  "title_grad": "两条建智能体的路",
  "product": "智果 AgentArts",
  "date": "2026-10-20",
  "sub": "华为云把 Agent 开发拆成了两条路——填表式配置和对话式生成……",
  "meta": [
    { "k": "日期", "v": "2026-10-20" },
    { "k": "产品", "v": "智果 AgentArts" },
    { "k": "厂商", "v": "华为云" },
    { "k": "类型", "v": "企业级 Agent 平台" }
  ],
  "product_card": [
    { "label": "产品定位", "value": "企业级智能体开发与运行平台" },
    { "label": "本次更新", "value": "新增对话式创建 + 评估任务" },
    { "label": "上线时间", "value": "2025 年公测" },
    { "label": "用户规模", "value": "未披露", "cite": [1] },
    { "label": "核心模型", "value": "盘古 + 第三方模型" },
    { "label": "分发渠道", "value": "华为云控制台" }
  ],
  "narrative": [
    { "t": "lead", "text": "为什么今天拆它：……", "cite": [1] },
    { "t": "metrics", "items": [{ "val": "4 类", "label": "预置模板" }] },
    { "t": "fig", "img": "shots/01_资产市场.png", "cap": "……", "src": "官方文档" }
  ],
  "sections": [
    {
      "id": "f1", "num": "01", "label": "Core Feature 01 · 创建",
      "h2": "两条建智能体的路：填表 or 对话",
      "blocks": [
        { "t": "h3", "text": "功能是什么" },
        { "t": "p", "text": "……", "cite": [2] },
        { "t": "figs", "cols": 2, "items": [
          { "img": "shots/02_创建.png", "cap": "……", "src": "官方文档" },
          { "img": "shots/03_对话创建.png", "cap": "……", "src": "官方文档" }
        ]}
      ]
    }
  ],
  "sources": [
    { "n": 1, "title": "华为云 AgentArts 产品页", "url": "https://www.huaweicloud.com/product/agentarts.html" }
  ],
  "footnote": "本拆解为公开信息整理，截图为官方文档公开的产品界面图。"
}
```

`sections[].label` 的命名惯例：`Core Feature 0N · <动词>`、`Architecture · 架构`、`Takeaways · 可复用方法论`。

---

## 五、抓图配置（_capture.json）

```json
{
  "out": "shots",
  "targets": [
    { "name": "01_资产市场", "url": "https://support.huaweicloud.com/usermanual-x/x_05_0016.html",
      "mode": "imgs", "minW": 480, "minH": 250, "max": 8, "wait": 7000 },

    { "name": "02_商店", "url": "https://yuanqi.tencent.com/agent-shop",
      "mode": "page", "wait": 6000 },

    { "name": "03_功能模块", "url": "https://x.com/product",
      "mode": "page", "selector": ".feature-section", "wait": 6000 },

    { "name": "04_架构图", "url": "https://x.com/product",
      "mode": "page", "selector": "#architecture", "wait": 6000, "fullPage": true }
  ]
}
```

| 字段 | 模式 | 说明 |
|---|---|---|
| `name` | 通用 | 输出文件名前缀，多张图会自动加 `_01`、`_02` |
| `url` | 通用 | 目标页 |
| `mode` | 通用 | `imgs`（提原图）/ `page`（截页面） |
| `wait` | 通用 | 额外等待毫秒数，懒加载站给 6000-8000 |
| `minW` / `minH` | imgs | 尺寸下限，低于则丢弃。默认 480×250 |
| `max` | imgs | 最多取几张，设成需要数的 1.5 倍 |
| `fullPage` | page | 是否截整页，默认 false（只截首屏） |
| `selector` | page | CSS 选择器，只截该元素 |
| `referer` | imgs | 遇到 CDN 防盗链时补 |

`out` 相对于配置文件所在目录。建议就写 `shots`，让图和 spec.json 同层。

⚠️ `name` 用「序号_含义」格式，序号直接对应报告里的出现顺序——整理目录时就完成了内容编排。
