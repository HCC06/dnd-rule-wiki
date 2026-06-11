#!/usr/bin/env python3
"""Build the D&D Rule Wiki from rulebook-clean markdown files."""

import frontmatter, markdown, json, os, re, shutil, urllib.parse
from pathlib import Path
from collections import defaultdict

ROOT = Path("/home/hcc/projects/dnd-combat-sim/rulebook-clean")
BOOKS_DIR = ROOT / "books"
OUT_DIR = ROOT / "docs"
ASSETS_DIR = OUT_DIR / "assets"

# Deployment base path — set to "/repo-name" for project sites, "" for user sites
BASE_PATH = os.environ.get("WIKI_BASE_PATH", "/dnd-rule-wiki")

BOOK_LABELS = {
    "玩家手册2024": "📖 玩家手册 2024", "城主指南2024": "📖 城主指南 2024",
    "怪物图鉴2025": "👹 怪物图鉴 2025", "玩家手册": "📖 玩家手册 2014",
    "城主指南": "📖 城主指南 2014", "怪物图鉴": "👹 怪物图鉴 2014",
    "贤者谏言2025": "📋 贤者谏言 2025", "速查": "⚡ 速查",
}

def resolve_link(href, current_dir, book_dir):
    if href.startswith("http://") or href.startswith("https://") or href.startswith("#"):
        return href
    current_abs = (book_dir / current_dir).resolve()
    target = (current_abs / href).resolve()
    try:
        rel = target.relative_to(book_dir.resolve())
    except ValueError:
        return href.replace(".htm", ".html").replace(".md", ".html")
    parts = []
    for seg in str(rel).split("/"):
        parts.append(seg[:-3] + ".html" if seg.endswith(".md") else seg)
        parts[-1] = parts[-1][:-4] + ".html" if parts[-1].endswith(".htm") else parts[-1]
    return "/" + "/".join(parts)

def build():
    print("🔨 Building D&D Rule Wiki...")
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)
    ASSETS_DIR.mkdir(parents=True)

    all_pages = []
    sidebar_tree = {}
    processed = 0

    for ruleset_dir in sorted(BOOKS_DIR.iterdir()):
        if not ruleset_dir.is_dir(): continue
        for book_dir in sorted(ruleset_dir.iterdir()):
            if not book_dir.is_dir(): continue
            book_name = book_dir.name
            ruleset = ruleset_dir.name
            book_label = BOOK_LABELS.get(book_name, book_name)
            if ruleset not in sidebar_tree:
                sidebar_tree[ruleset] = {}
            if book_name not in sidebar_tree[ruleset]:
                sidebar_tree[ruleset][book_name] = {"_label": book_label, "_chapters": {}}

            for md_file in sorted(book_dir.rglob("*.md")):
                rel = md_file.relative_to(book_dir)
                chapter = str(rel.parent) if str(rel.parent) != "." else ""
                out_rel = Path(ruleset) / book_name / rel.with_suffix(".html")
                out_file = OUT_DIR / out_rel
                out_file.parent.mkdir(parents=True, exist_ok=True)

                try:
                    post = frontmatter.load(str(md_file))
                except:
                    continue

                title = post.get("title", md_file.stem)
                fm_ruleset = post.get("ruleset", "")

                md_body = post.content
                # Strip first h1 heading (template already provides title)
                md_body = re.sub(r'^#\s+.+?\n', '', md_body, count=1)
                # Rewrite internal links
                md_body = re.sub(
                    r'\[([^\]]*)\]\(([^)]+)\)',
                    lambda m: f'[{m.group(1)}]({resolve_link(m.group(2), rel.parent, book_dir)})',
                    md_body
                )
                html_body = markdown.markdown(md_body, extensions=["tables", "fenced_code", "toc", "nl2br", "sane_lists"])

                url = BASE_PATH + "/" + str(out_rel).replace("\\", "/")
                page = {
                    "title": title, "url": url, "book": book_name,
                    "book_label": book_label, "ruleset": fm_ruleset, "chapter": chapter,
                    "breadcrumbs": [{"label": book_label, "url": f"{BASE_PATH}/{ruleset}/{book_name}/"}],
                }
                if chapter:
                    page["breadcrumbs"].append({
                        "label": chapter.split("/")[-1],
                        "url": f"{BASE_PATH}/{ruleset}/{book_name}/{chapter}/",
                    })

                ch_key = chapter if chapter else "__root__"
                if ch_key not in sidebar_tree[ruleset][book_name]["_chapters"]:
                    sidebar_tree[ruleset][book_name]["_chapters"][ch_key] = []
                sidebar_tree[ruleset][book_name]["_chapters"][ch_key].append({"name": title, "url": url})

                all_pages.append({"title": title, "url": url, "book": book_label,
                                  "ruleset": fm_ruleset,
                                  "chapter": chapter.split("/")[-1] if "/" in chapter else chapter})

                html = render_page(page, html_body)
                out_file.write_text(html, encoding="utf-8")
                processed += 1
                if processed % 500 == 0:
                    print(f"   ... {processed} pages")

    # Generate chapter index pages
    chapter_count = 0
    for ruleset, books in sidebar_tree.items():
        for book_name, book_data in books.items():
            if book_name.startswith("_"): continue
            for ch_name, ch_pages in book_data.get("_chapters", {}).items():
                if ch_name == "__root__": continue
                # Create index page for this chapter
                out_dir = OUT_DIR / ruleset / book_name / ch_name
                out_dir.mkdir(parents=True, exist_ok=True)
                idx = out_dir / "index.html"
                display_name = ch_name.split("/")[-1] if "/" in ch_name else ch_name
                pg_links = "".join(
                    f'<li><a href="{p["url"]}">{p["name"]}</a></li>'
                    for p in sorted(ch_pages, key=lambda x: x["name"])
                )
                bc = f'<a href="{BASE_PATH}/{ruleset}/{book_name}/">{BOOK_LABELS.get(book_name, book_name)}</a> <span class="sep">›</span> <span class="current">{display_name}</span>'
                html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{display_name} — D&D Rule Wiki</title><link rel="stylesheet" href="{BASE_PATH}/assets/style.css"></head><body><div class="layout"><aside class="sidebar" id="sidebar"><div class="sidebar-head"><a href="{BASE_PATH}/" class="home-link">🐉 D&D Rule Wiki</a><input type="text" id="search-input" class="search-box" placeholder="搜索规则、法术、怪物…" autocomplete="off"><div id="search-results" class="search-results"></div></div><nav class="tree" id="tree"></nav></aside><main class="content"><nav class="breadcrumbs">{bc}</nav><article class="rule-content"><h1>{display_name}</h1><ul style="font-size:1.1em;line-height:2.2">{pg_links}</ul></article></main></div><script src="{BASE_PATH}/assets/search.js"></script><script src="{BASE_PATH}/assets/sidebar.js"></script></body></html>"""
                idx.write_text(html, encoding="utf-8")
                chapter_count += 1

    # Generate book-level index pages
    for ruleset, books in sidebar_tree.items():
        for book_name, book_data in books.items():
            if book_name.startswith("_"): continue
            out_dir = OUT_DIR / ruleset / book_name
            out_dir.mkdir(parents=True, exist_ok=True)
            idx = out_dir / "index.html"
            book_label = book_data.get("_label", book_name)
            ch_list = ""
            for ch_name in sorted(book_data.get("_chapters", {}).keys()):
                ch_display = ch_name if ch_name != "__root__" else ""
                ch_url = f"{BASE_PATH}/{ruleset}/{book_name}/{ch_name}/" if ch_name != "__root__" else ""
                if ch_name == "__root__":
                    # List root pages directly
                    for p in book_data["_chapters"]["__root__"]:
                        ch_list += f'<li><a href="{p["url"]}">{p["name"]}</a></li>\n'
                else:
                    display = ch_name.split("/")[-1] if "/" in ch_name else ch_name
                    ch_list += f'<li><a href="{ch_url}">{display}</a></li>\n'
            bc = f'<span class="current">{book_label}</span>'
            html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{book_label} — D&D Rule Wiki</title><link rel="stylesheet" href="{BASE_PATH}/assets/style.css"></head><body><div class="layout"><aside class="sidebar" id="sidebar"><div class="sidebar-head"><a href="{BASE_PATH}/" class="home-link">🐉 D&D Rule Wiki</a><input type="text" id="search-input" class="search-box" placeholder="搜索规则、法术、怪物…" autocomplete="off"><div id="search-results" class="search-results"></div></div><nav class="tree" id="tree"></nav></aside><main class="content"><nav class="breadcrumbs">{bc}</nav><article class="rule-content"><h1>{book_label}</h1><ul style="font-size:1.1em;line-height:2.2">{ch_list}</ul></article></main></div><script src="{BASE_PATH}/assets/search.js"></script><script src="{BASE_PATH}/assets/sidebar.js"></script></body></html>"""
            idx.write_text(html, encoding="utf-8")

    write_assets(sidebar_tree, all_pages)
    print(f"\n✅ Done! {processed} pages, {chapter_count} chapter indexes, {len(all_pages)} search entries")
    print(f"📁 Output: {OUT_DIR}")

def render_page(page, body_html):
    bc = ""
    for i, b in enumerate(page["breadcrumbs"]):
        if i > 0: bc += ' <span class="sep">›</span> '
        bc += f'<a href="{b["url"]}">{b["label"]}</a>'
    bc += f' <span class="sep">›</span> <span class="current">{page["title"]}</span>'
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{page['title']} — D&D Rule Wiki</title><link rel="stylesheet" href="{BASE_PATH}/assets/style.css"></head><body><div class="layout"><aside class="sidebar" id="sidebar"><div class="sidebar-head"><a href="{BASE_PATH}/" class="home-link">🐉 D&D Rule Wiki</a><input type="text" id="search-input" class="search-box" placeholder="搜索规则、法术、怪物…" autocomplete="off"><div id="search-results" class="search-results"></div></div><nav class="tree" id="tree"></nav></aside><main class="content"><nav class="breadcrumbs">{bc}</nav><article class="rule-content"><h1>{page['title']}</h1>{body_html}</article><footer class="page-footer"><p>📚 {page['book_label']} · 规则集 {page['ruleset']}</p></footer></main></div><script src="{BASE_PATH}/assets/search.js"></script><script src="{BASE_PATH}/assets/sidebar.js"></script></body></html>"""

def write_assets(tree_data, all_pages):
    # CSS
    css = """:root{--bg:#fdfcf9;--card:#fff;--text:#2b2b2b;--muted:#777;--red:#b22222;--blue:#2563eb;--gold:#8b6914;--border:#e5dfd5;--sidebar-w:280px;--sidebar-bg:#f8f5f0}*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Noto Serif SC','Source Han Serif SC','Songti SC',Georgia,serif;background:var(--bg);color:var(--text);line-height:1.85;font-size:16px}.layout{display:flex}.sidebar{width:var(--sidebar-w);min-width:var(--sidebar-w);height:100vh;position:sticky;top:0;overflow-y:auto;background:var(--sidebar-bg);border-right:1px solid var(--border);font-size:.84em}.sidebar-head{position:sticky;top:0;background:var(--sidebar-bg);z-index:5;padding:14px 14px 10px}.home-link{display:block;font-size:1.1em;font-weight:800;color:var(--red);text-decoration:none;margin-bottom:10px}.search-box{width:100%;padding:7px 10px;border:1px solid var(--border);border-radius:6px;font-size:.9em;font-family:inherit;background:#fff}.search-results{display:none;background:#fff;border:1px solid var(--border);border-radius:0 0 6px 6px;max-height:300px;overflow-y:auto;box-shadow:0 4px 12px rgba(0,0,0,.1)}.search-results.active{display:block}.search-results a{display:block;padding:6px 10px;text-decoration:none;color:var(--text);border-bottom:1px solid var(--border);font-size:.9em}.search-results a:hover{background:#fef0f0}.search-results .book-tag{font-size:.75em;color:var(--muted);margin-left:6px}.search-results .no-results{padding:12px;color:var(--muted);text-align:center}.tree{padding:8px 14px 40px}.tree ul{list-style:none;padding:0}.tree li{margin-bottom:1px}.tree a{color:var(--muted);text-decoration:none;display:block;padding:3px 8px;border-radius:4px;font-size:.9em}.tree a:hover{color:var(--red);background:#fdf0f0}.tree .folder>.folder-label{cursor:pointer;padding:3px 8px;border-radius:4px;font-weight:600;color:#666;font-size:.88em}.tree .folder>.folder-label:hover{color:var(--red)}.tree .folder>ul{padding-left:14px;display:none}.tree .folder.open>ul{display:block}.tree .ruleset-label{font-size:.75em;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#999;padding:10px 8px 4px;border-top:1px solid var(--border);margin-top:4px}.content{flex:1;min-width:0;max-width:860px;margin:0 auto;padding:24px 32px 0}.breadcrumbs{font-size:.82em;color:var(--muted);margin-bottom:20px}.breadcrumbs a{color:var(--blue);text-decoration:none}.breadcrumbs a:hover{text-decoration:underline}.breadcrumbs .sep{margin:0 6px;color:#ccc}.breadcrumbs .current{color:var(--text)}.rule-content{background:var(--card);padding:28px 32px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.06)}.rule-content h1{font-size:1.6em;margin-bottom:20px;padding-bottom:10px;border-bottom:2px solid var(--red)}.rule-content h2{font-size:1.25em;margin:28px 0 10px;color:var(--red)}.rule-content h3{font-size:1.1em;margin:20px 0 8px}.rule-content h4{font-size:1em;margin:16px 0 6px}.rule-content p{margin-bottom:10px}.rule-content ul,.rule-content ol{padding-left:22px;margin-bottom:12px}.rule-content li{margin-bottom:4px}.rule-content table{width:100%;border-collapse:collapse;margin:14px 0;font-size:.9em}.rule-content th{background:#f5f0e8;padding:8px 12px;text-align:left;font-weight:700;font-size:.85em}.rule-content td{padding:7px 12px;border-top:1px solid var(--border)}.rule-content tr:hover td{background:#fdfaf5}.rule-content blockquote{border-left:3px solid var(--red);margin:12px 0;padding:8px 16px;background:#fef9f0;border-radius:0 6px 6px 0;font-size:.93em}.rule-content code{background:#f5f0e8;padding:1px 5px;border-radius:3px;font-size:.9em}.rule-content pre{background:#f5f0e8;padding:12px 16px;border-radius:6px;overflow-x:auto;font-size:.85em;margin:12px 0}.rule-content table td:first-child,.rule-content table th:first-child:not(:empty){font-weight:600}.rule-content .HT{background:#f5f0e8;padding:6px 14px;border-radius:6px;margin:8px 0;font-size:.9em}.rule-content a{color:var(--blue)}.page-footer{margin-top:32px;padding-top:14px;border-top:1px solid var(--border);font-size:.8em;color:var(--muted);text-align:center}.home-hero{background:linear-gradient(170deg,#1a1a2e,#16213e);color:#f5e6c8;text-align:center;padding:48px 0 32px;margin-bottom:32px;border-radius:10px}.home-hero h1{font-size:1.8em;color:#f5c842}.home-hero p{color:#c8b88a;margin-top:4px}.home-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;margin:20px 0}.home-card{background:var(--card);border-radius:10px;padding:18px 20px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-top:3px solid var(--red);text-decoration:none;color:var(--text);transition:box-shadow .2s}.home-card:hover{box-shadow:0 4px 12px rgba(0,0,0,.1)}.home-card:nth-child(2){border-top-color:var(--blue)}.home-card:nth-child(3){border-top-color:var(--gold)}.home-card:nth-child(4){border-top-color:#0d7c4d}.home-card h3{font-size:1.05em;margin-bottom:4px}.home-card .cnt{font-size:.82em;color:var(--muted)}.sidebar::-webkit-scrollbar{width:4px}.sidebar::-webkit-scrollbar-track{background:transparent}.sidebar::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}@media(max-width:800px){.layout{flex-direction:column}.sidebar{width:100%;min-width:auto;height:auto;max-height:45vh;position:relative}.content{padding:16px}.rule-content{padding:16px}.home-grid{grid-template-columns:1fr 1fr}}"""
    (ASSETS_DIR / "style.css").write_text(css, encoding="utf-8")

    # Search JS
    search_js = f"""(async function(){{let pages=[];try{{const r=await fetch('{BASE_PATH}/search-index.json');pages=await r.json()}}catch(e){{return}}const input=document.getElementById('search-input');const results=document.getElementById('search-results');if(!input||!results)return;function search(query){{results.innerHTML='';if(!query||query.length<1){{results.classList.remove('active');return}}const q=query.toLowerCase();const matched=[];for(const p of pages){{const score=(p.title.includes(query)?100:0)+(p.title.toLowerCase().includes(q)?50:0)+(p.book.toLowerCase().includes(q)?10:0);if(score>0)matched.push({{...p,score}})}}matched.sort((a,b)=>b.score-a.score);const top=matched.slice(0,30);if(top.length===0){{results.innerHTML='<div class=no-results>没有找到结果</div>'}}else{{for(const p of top){{const a=document.createElement('a');a.href=p.url;a.innerHTML=p.title+' <span class=book-tag>'+p.book+'</span>';results.appendChild(a)}}}}results.classList.add('active')}}input.addEventListener('input',()=>search(input.value.trim()));input.addEventListener('focus',()=>{{if(input.value.trim())search(input.value.trim())}});document.addEventListener('click',(e)=>{{if(!results.contains(e.target)&&e.target!==input)results.classList.remove('active')}});input.addEventListener('keydown',(e)=>{{if(e.key==='Escape'){{results.classList.remove('active');input.blur()}}if(e.key==='Enter'){{const first=results.querySelector('a');if(first)window.location=first.href}}}}}})()"""
    (ASSETS_DIR / "search.js").write_text(search_js, encoding="utf-8")

    # Sidebar JS
    rulesets = []
    for rs_key, rs_label in [("2024-core","2024 规则"),("legacy-core","2014 规则"),("faq","FAQ"),("quick-reference","速查"),("legacy-supplements","扩展书"),("modules","模组"),("third-party","第三方"),("unclassified","未分类")]:
        if rs_key not in tree_data: continue
        books = []
        for bn, bd in sorted(tree_data[rs_key].items()):
            if bn.startswith("_"): continue
            chapters = []
            for cn, cp in sorted(bd.get("_chapters",{}).items()):
                if cn == "__root__":
                    for p in cp: chapters.append({"name":p["name"],"url":p["url"]})
                else:
                    chapters.append({"name":cn.split("/")[-1],"pages":[{"name":p["name"],"url":p["url"]}for p in cp]})
            books.append({"name":bd.get("_label",bn),"chapters":chapters})
        rulesets.append({"label":rs_label,"books":books})

    tree_json = json.dumps(rulesets, ensure_ascii=False)
    sidebar_js = f"""(function(){{const tree={tree_json};const container=document.getElementById('tree');if(!container)return;function buildNode(node){{if(node.url){{const a=document.createElement('a');a.href=node.url;a.textContent=node.name;return a}}const li=document.createElement('li');if(node.pages){{const span=document.createElement('span');span.className='folder-label';span.textContent='▸ '+node.name;const ul=document.createElement('ul');node.pages.forEach(p=>{{const pli=document.createElement('li');const a=document.createElement('a');a.href=p.url;a.textContent=p.name;pli.appendChild(a);ul.appendChild(pli)}});li.className='folder';li.appendChild(span);li.appendChild(ul);span.addEventListener('click',()=>li.classList.toggle('open'));const cp=window.location.pathname;if(node.pages.some(p=>cp.endsWith(p.url)))li.classList.add('open')}}return li}}for(const rs of tree){{const rsDiv=document.createElement('div');rsDiv.className='ruleset-label';rsDiv.textContent=rs.label;container.appendChild(rsDiv);for(const book of rs.books){{const details=document.createElement('li');details.className='folder open';const summary=document.createElement('span');summary.className='folder-label';summary.textContent='📁 '+book.name;const ul=document.createElement('ul');book.chapters.forEach(ch=>{{const li=buildNode(ch);if(li)ul.appendChild(li)}});details.appendChild(summary);details.appendChild(ul);container.appendChild(details)}}}}const cp=window.location.pathname;container.querySelectorAll('a').forEach(a=>{{if(cp.endsWith(a.getAttribute('href'))){{a.style.color='var(--red)';a.style.fontWeight='700';let p=a.parentElement;while(p){{if(p.classList.contains('folder'))p.classList.add('open');p=p.parentElement}}}}}})}})()"""
    (ASSETS_DIR / "sidebar.js").write_text(sidebar_js, encoding="utf-8")

    # Search index
    (OUT_DIR / "search-index.json").write_text(json.dumps(all_pages, ensure_ascii=False, indent=2), encoding="utf-8")

    # Homepage
    book_info = defaultdict(lambda: {"count":0,"url":""})
    for p in all_pages:
        k = p["book"]; book_info[k]["count"]+=1
        if not book_info[k]["url"]: book_info[k]["url"] = p["url"].rsplit("/",1)[0]+"/"

    book_cards = ""
    for label, info in sorted(book_info.items(), key=lambda x:-x[1]["count"]):
        book_cards += f'<a class="home-card" href="{info["url"]}"><h3>{label}</h3><span class="cnt">{info["count"]} 页</span></a>\n'

    BP = BASE_PATH
    quick = [(f"⚔️ 战斗规则",f"{BP}/2024-core/玩家手册2024/进行游戏/战斗流程.html"),(f"✨ 法术详述",f"{BP}/2024-core/玩家手册2024/法术详述/"),(f"👹 怪物图鉴",f"{BP}/2024-core/怪物图鉴2025/"),(f"📋 状态列表",f"{BP}/2024-core/玩家手册2024/术语汇编/状态.html"),(f"🛡️ 职业",f"{BP}/2024-core/玩家手册2024/角色职业/"),(f"🌿 种族/物种",f"{BP}/2024-core/玩家手册2024/角色起源/种族详述.html"),(f"⚡ 速查",f"{BP}/quick-reference/速查/")]
    quick_html = "".join(f'<a class="home-card" href="{u}"><h3>{l}</h3></a>' for l,u in quick)
    comp = f"""<div style="margin-top:32px"><h2 style="color:var(--red);border-bottom:2px solid var(--red);padding-bottom:8px">📋 2024 vs 2014 核心变化</h2><div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px"><div style="background:var(--card);padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid var(--red)"><strong>⚡ 突袭</strong>：被突袭不再失去回合，改为先攻劣势</div><div style="background:var(--card);padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid var(--red)"><strong>🔪 武器精通</strong>：全新系统，8种精通属性</div><div style="background:var(--card);padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid var(--blue)"><strong>🛡️ 至圣斩</strong>：变为法术，每回合一次</div><div style="background:var(--card);padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid var(--blue)"><strong>💪 属性值来源</strong>：从种族移至背景</div><div style="background:var(--card);padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid var(--gold)"><strong>🎯 巨武/神射</strong>：-5/+10 移除</div><div style="background:var(--card);padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid var(--gold)"><strong>✨ 法术反制</strong>：体质豁免，不消耗法术位</div><div style="background:var(--card);padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid #0d7c4d"><strong>💚 治疗翻倍</strong>：治疗伤口2d8，治愈真言2d4</div><div style="background:var(--card);padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid #0d7c4d"><strong>🧪 药水BA</strong>：所有药水饮用改为附赠动作</div><div style="background:var(--card);padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid var(--red)"><strong>📊 力竭线性化</strong>：-2/级d20，-5尺/级速度</div><div style="background:var(--card);padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid var(--blue)"><strong>🎓 子职业统一3级</strong>：所有职业统一在3级选择</div></div></div>"""

    homepage = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>D&D Rule Wiki</title><link rel="stylesheet" href="{BASE_PATH}/assets/style.css"></head><body><div class="layout"><aside class="sidebar" id="sidebar"><div class="sidebar-head"><a href="{BASE_PATH}/" class="home-link">🐉 D&D Rule Wiki</a><input type="text" id="search-input" class="search-box" placeholder="搜索规则、法术、怪物…" autocomplete="off"><div id="search-results" class="search-results"></div></div><nav class="tree" id="tree"></nav></aside><main class="content"><div class="home-hero"><h1>🐉 D&D Rule Wiki</h1><p>龙与地下城规则维基 · {len(all_pages)} 个页面 · 2024 & 2014 规则集</p></div><h2 style="margin-bottom:12px">📚 规则书</h2><div class="home-grid">{book_cards}</div><h2 style="margin:28px 0 12px">⚡ 快速导航</h2><div class="home-grid">{quick_html}</div>{comp}</main></div><script src="{BASE_PATH}/assets/search.js"></script><script src="{BASE_PATH}/assets/sidebar.js"></script></body></html>"""
    (OUT_DIR / "index.html").write_text(homepage, encoding="utf-8")

if __name__ == "__main__":
    build()
