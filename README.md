# D&D Rule Wiki

龙与地下城 5e 规则 Wiki，包含 2024 和 2014 两版规则集，总计 6,500+ 页面。部署在 GitHub Pages。

**线上地址：** https://hcc06.github.io/dnd-rule-wiki/

## 目录结构

```
rulebook-clean/
├── DND五版不全书v2026.02.12.chm   # 源文件（未跟踪，在 .gitignore）
├── _extracted_html/               # 从 CHM 提取的原始 GBK HTML（临时，已忽略）
├── books/                         # 转换后的 UTF-8 Markdown 规则页
│   ├── 2024-core/                 #  玩家手册2024 + 城主指南2024 + 怪物图鉴2025
│   ├── legacy-core/               #  玩家手册 + 城主指南 + 怪物图鉴（2014 版）
│   ├── legacy-supplements/        #  扩展书（塔莎、珊娜萨、费资本等）
│   ├── modules/                   #  冒险模组
│   ├── third-party/               #  第三方内容
│   ├── quick-reference/           #  速查表
│   ├── faq/                       #  贤者谏言 2025
│   └── unclassified/              #  未分类
├── docs/                          # 生成的静态 Wiki 网站（GitHub Pages 源）
│   ├── index.html                 #  首页
│   ├── assets/                    #  CSS, JS（搜索、侧边栏）
│   ├── search-index.json          #  客户端搜索索引
│   └── 2024-core/ ...             #  按规则集/书/章 组织的 HTML 页面
├── scripts/
│   ├── rulebook-rebuild/          # CHM → MD 转换脚本
│   │   └── extract_chm.sh         #  用 7z 提取 CHM → _extracted_html/
│   │   └── convert_html_to_markdown.py  #  GBK HTML → UTF-8 MD (pandoc)
│   └── build-wiki.py              # MD → 静态 HTML Wiki（主构建脚本）
├── DND-2024-vs-2014-简明对比-附原文.html
├── DND-2024-vs-2014-详细对比-附原文.html
└── README.md
```

## 从零重建流程

### 1. 准备 CHM 文件

将 `DND五版不全书v2026.02.12.chm` 放到 `rulebook-clean/` 目录下。
SHA-256: `2b54d4c86439b25c0595aa728bfca69f14f1f0e482951bd53d573b05821b3894`

### 2. 提取 CHM

```bash
cd rulebook-clean
bash scripts/rulebook-rebuild/extract_chm.sh
# 输出 → _extracted_html/ (6,573 个 GBK 编码的 HTML 文件)
```

### 3. 转换为 Markdown

```bash
python3 scripts/rulebook-rebuild/convert_html_to_markdown.py
# 输出 → books/ (6,566 个 UTF-8 MD 文件，含 YAML frontmatter)
```

依赖：`pip install markdown pyyaml python-frontmatter --break-system-packages`
系统需要安装 `pandoc` 和 `7z`。

### 4. 构建 Wiki

```bash
python3 scripts/build-wiki.py
# 输出 → docs/ (6,566 个 HTML + 671 个章节索引 + 搜索 + 侧边栏)
```

构建脚本会：
- 把 MD → HTML（markdown 库，tables/fenced_code/toc/nl2br/sane_lists 扩展）
- 清理 CHM 残留的 Word 内联样式（span/div/o:p 标签）
- 生成书级和章级 index.html
- 生成搜索索引 JSON
- 生成侧边栏导航 JS
- 重写内部 `.md` 链接为 `.html`

### 5. 部署

```bash
cp DND-2024-vs-2014-*.html docs/   # 对比报告
touch docs/.nojekyll
git add docs/ scripts/ .nojekyll
git commit -m "rebuild wiki"
git push origin master
```

GitHub Pages 配置：Settings → Pages → Source: `master` 分支, `/docs` 目录。

## 关键设计决策

- **不用 Jekyll** — `.nojekyll` 告诉 GitHub Pages 绕过 Jekyll 直接提供静态文件。Jekyll 处理不了 6,500+ 中文文件名页面。
- **绝对路径含 BASE_PATH** — 所有内部链接前缀 `/dnd-rule-wiki`（通过环境变量 `WIKI_BASE_PATH` 控制，默认值在 `build-wiki.py` 第 14 行）。部署到用户站点根目录时改为空字符串。
- **章节目录索引** — 构建时自动为每个章节目录生成 `index.html`，列出该章所有页面。否则侧边栏点击章节名会 404。
- **CHM HTML 清理** — 源 CHM 是 MS Word 导出的 GBK HTML，含大量 `<span style="...">`、`<div class="WordSection2">`、`<o:p>` 等垃圾标签。构建时用正则剥离。

## 搜索与导航

- **搜索**：客户端实现，索引文件 `search-index.json`（~1MB，6,500 条目）。6 行 JS 获取索引 + 本地过滤，无需服务器。
- **侧边栏**：三层结构（规则集 → 书 → 章 → 页面），可折叠。当前页面自动展开并高亮。

## 对比报告

两份独立的 HTML 文件，不在 Wiki 构建流程中：

| 文件 | 内容 |
|------|------|
| `DND-2024-vs-2014-简明对比-附原文.html` | 10 大核心变化 + 规则书原文对照 |
| `DND-2024-vs-2014-详细对比-附原文.html` | 8 章完整对比 + 固定侧边栏 + 原文链接到 Wiki |

每个原文引用都是可点击的超链接（📁 查看原文 →），指向 Wiki 对应页面。

## 常见问题

**页面排版混乱？** 通常是 CHM 残留 HTML 标签没清干净。检查 `books/` 下对应 MD 文件，看是否有多余的 `<span style="...">` 或 `<div>` 标签。在 `build-wiki.py` 的清理正则中追加匹配规则即可。

**链接 404？** 检查是否缺少 `BASE_PATH` 前缀（适用于 `hcc06.github.io/dnd-rule-wiki/` 而非 `hcc06.github.io/`）。也可能是目录缺少 `index.html`。

**新 CHM 版本？** 替换 CHM 文件后，从步骤 2 开始重新跑。
