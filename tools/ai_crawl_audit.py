#!/usr/bin/env python3
"""AI 抓取技术检查脚本 — 智海科技官网 (zhihaigeo.com)

部署后运行，检查网站是否对搜索引擎和 AI 搜索系统友好。
只使用 Python 标准库，只读不写，不修改线上网站。

用法：python3 tools/ai_crawl_audit.py
"""

import json
import sys
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import re
import urllib.robotparser
from collections import Counter
from urllib.parse import urljoin, urlparse

BASE = "https://www.zhihaigeo.com"
EXPECTED_HOST = "www.zhihaigeo.com"
TIMEOUT = 15

PASS = 0
WARN = 0
FAIL = 0


def check(name, passed, detail="", level=None):
    global PASS, WARN, FAIL
    if level is None:
        level = "pass" if passed else "fail"
    marks = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
    print(f"{marks[level]} [{level.upper()}] {name}")
    if detail:
        print(f"   {detail}")
    if level == "pass":
        PASS += 1
    elif level == "warn":
        WARN += 1
    else:
        FAIL += 1


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AI-Crawl-Audit/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)


def fetch_status(url):
    status, _ = fetch(url)
    return status


def parse_sitemap(raw_xml):
    """兼容有无命名空间的 sitemap 解析，返回 URL 列表"""
    urls = []
    if not raw_xml:
        return urls
    try:
        root = ET.fromstring(raw_xml)
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0].strip("{")
        for url_el in root:
            loc_el = None
            if ns:
                loc_el = url_el.find(f"{{{ns}}}loc")
            if loc_el is None:
                loc_el = url_el.find("loc")
            if loc_el is not None and loc_el.text:
                urls.append(loc_el.text.strip())
    except ET.ParseError:
        pass
    return urls


def extract_internal_links(html):
    """从 HTML 中提取所有内部链接（同时识别单引号、双引号和本站绝对地址）"""
    links = set()
    for m in re.finditer(r"""href\s*=\s*["']([^"'#]+)["']""", html, re.IGNORECASE):
        href = m.group(1).strip()
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        full_url = urljoin(BASE + "/", href)
        parsed = urlparse(full_url)
        if parsed.hostname == EXPECTED_HOST:
            links.add(full_url.split("#")[0].split("?")[0])
    return links


# ═══════════════════════════════════════════════════
# 1. 基础可达性
# ═══════════════════════════════════════════════════
print("=" * 60)
print("1. 基础可达性")
print("=" * 60)

status, home_html = fetch(BASE + "/")
check("首页返回 HTTP 200", status == 200,
      f"状态码: {status}" if status != 200 else "")

for name, path in [
    ("robots.txt", "/robots.txt"),
    ("sitemap.xml", "/sitemap.xml"),
    ("llms.txt", "/llms.txt"),
]:
    status = fetch_status(BASE + path)
    check(f"{name} 返回 HTTP 200", status == 200,
          f"状态码: {status}" if status != 200 else "")

# ═══════════════════════════════════════════════════
# 2. robots.txt 检查（修复大小写 bug）
# ═══════════════════════════════════════════════════
print("\n" + "=" * 60)
print("2. robots.txt 检查")
print("=" * 60)

_, robots_raw = fetch(BASE + "/robots.txt")
if robots_raw:
    check("robots.txt 可读取", True)

    # 用标准库 robotparser 判断 OAI-SearchBot（直接解析已获取内容，避免重复联网）
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(BASE + "/robots.txt")
    rp.parse(robots_raw.splitlines())

    oai_can_fetch = rp.can_fetch("OAI-SearchBot", BASE + "/")
    check(f"OAI-SearchBot 允许抓取首页", oai_can_fetch,
          "OAI-SearchBot 被 robots.txt 禁止访问" if not oai_can_fetch else "OAI-SearchBot 可以正常抓取")

    # 全站 Disallow 检查
    lines_lower = robots_raw.lower()
    has_disallow_all = "disallow: /" in lines_lower
    has_allow_all = "allow: /" in lines_lower
    if has_disallow_all and not has_allow_all:
        check("无全站 Disallow: /", False, "存在 Disallow: / 可能屏蔽所有爬虫", "fail")
    else:
        check("无全站 Disallow: /", True)

    # sitemap 地址
    sitemap_ok = "zhihaigeo.com/sitemap.xml" in robots_raw
    sitemap_line = ""
    for line in robots_raw.split("\n"):
        if "sitemap" in line.lower():
            sitemap_line = line.strip()
            break
    check("sitemap 地址正确", sitemap_ok,
          f"当前: {sitemap_line}" if not sitemap_ok else sitemap_line)
else:
    check("robots.txt 可读取", False, "无法获取内容", "fail")

# ═══════════════════════════════════════════════════
# 3. sitemap.xml 检查
# ═══════════════════════════════════════════════════
print("\n" + "=" * 60)
print("3. sitemap.xml 检查")
print("=" * 60)

_, sitemap_raw = fetch(BASE + "/sitemap.xml")
sitemap_urls = parse_sitemap(sitemap_raw)
check("sitemap 为合法 XML", sitemap_raw != "" and sitemap_urls != [] if sitemap_raw else False,
      "" if sitemap_urls else "sitemap 为空或无法解析")

if not sitemap_urls:
    check("sitemap 包含 URL", False, "没有读取到正式 URL，停止后续检查", "fail")
    print("\n❌ sitemap 中没有 URL，无法继续全站检查。请检查 sitemap.xml 内容。")
    sys.exit(1)

check(f"sitemap 包含 URL", True, f"共 {len(sitemap_urls)} 个")

# 域名一致性
wrong_host = [u for u in sitemap_urls if urlparse(u).hostname != EXPECTED_HOST]
non_https = [u for u in sitemap_urls if not u.startswith("https://")]
check("所有 URL 使用 https://www.zhihaigeo.com", len(wrong_host) == 0 and len(non_https) == 0,
      f"{len(wrong_host)} 个域名不匹配, {len(non_https)} 个非 HTTPS" if wrong_host or non_https else "")

# 重复 URL
dup_urls = [u for u, c in Counter(sitemap_urls).items() if c > 1]
check("sitemap 无重复 URL", len(dup_urls) == 0,
      f"重复 {len(dup_urls)} 组: {dup_urls[:3]}" if dup_urls else "")

# 验证文件检查
bad_patterns = ["ByteDance", "google360", "shenma", ".md", ".txt"]
bad_urls = [u for u in sitemap_urls if any(p.lower() in u.lower() for p in bad_patterns)]
check("sitemap 不含验证文件或内部文件", len(bad_urls) == 0,
      f"可疑: {bad_urls}" if bad_urls else "")

# 全 URL 可达性
print(f"\n  检查 {len(sitemap_urls)} 个 URL 可达性...")
dead_urls = []
for url in sitemap_urls:
    s = fetch_status(url)
    if s != 200:
        dead_urls.append((url, s))
if dead_urls:
    for url, s in dead_urls:
        check(f"可达: {url}", False, f"返回 {s}", "fail")
else:
    check(f"全部 {len(sitemap_urls)} 个 URL 返回 200", True)

# ═══════════════════════════════════════════════════
# 4. 逐页 HTML 元数据检查（修复 canonical 匹配）
# ═══════════════════════════════════════════════════
print("\n" + "=" * 60)
print("4. 逐页 HTML 元数据检查")
print("=" * 60)

html_urls = [u for u in sitemap_urls if u.endswith(".html") or u.endswith("/")]
page_no_title = []
page_no_h1 = []
page_multi_h1 = []
page_noindex = []
page_no_canonical = []
page_canonical_mismatch = []
page_jsonld_bad = []

for url in html_urls:
    name = url.replace(BASE, "") or "/"
    status, body = fetch(url)
    if status != 200:
        continue

    # title
    t_match = re.search(r'<title>(.*?)</title>', body, re.IGNORECASE)
    if not t_match or not t_match.group(1).strip():
        page_no_title.append(name)

    # H1
    h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', body, re.IGNORECASE)
    if not h1_matches:
        page_no_h1.append(name)
    elif len(h1_matches) > 1:
        page_multi_h1.append((name, len(h1_matches)))

    # noindex
    if re.search(r'<meta[^>]+content="[^"]*noindex[^"]*"', body, re.IGNORECASE):
        page_noindex.append(name)

    # canonical → 必须对应当前页面 URL
    c_match = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', body)
    if not c_match:
        page_no_canonical.append(name)
    else:
        canonical_url = c_match.group(1).rstrip("/")
        expected_url = url.rstrip("/")
        if canonical_url != expected_url:
            page_canonical_mismatch.append((name, canonical_url, expected_url))

    # JSON-LD
    ld_scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, re.DOTALL)
    for s in ld_scripts:
        try:
            json.loads(s)
        except json.JSONDecodeError:
            page_jsonld_bad.append(name)
            break

# 输出逐页结果
check("所有页面有 title", len(page_no_title) == 0,
      f"{len(page_no_title)} 个缺失: {page_no_title}" if page_no_title else "")

check("所有页面有且仅有一个 H1", len(page_no_h1) == 0 and len(page_multi_h1) == 0,
      f"缺 H1: {page_no_h1}, 多 H1: {page_multi_h1}" if (page_no_h1 or page_multi_h1) else "")

check("所有页面无 noindex", len(page_noindex) == 0,
      f"{len(page_noindex)} 个: {page_noindex}" if page_noindex else "")

check("所有页面有 canonical", len(page_no_canonical) == 0,
      f"{len(page_no_canonical)} 个缺失: {page_no_canonical}" if page_no_canonical else "")

check("canonical 与当前页面对应", len(page_canonical_mismatch) == 0,
      f"{len(page_canonical_mismatch)} 个不匹配: {page_canonical_mismatch[:5]}" if page_canonical_mismatch else "")

check("所有页面 JSON-LD 语法正确", len(page_jsonld_bad) == 0,
      f"{len(page_jsonld_bad)} 个失败: {page_jsonld_bad}" if page_jsonld_bad else "")

# ═══════════════════════════════════════════════════
# 5. 全站内部链接检查
# ═══════════════════════════════════════════════════
print("\n" + "=" * 60)
print("5. 全站内部链接检查")
print("=" * 60)

all_internal = set()
for url in html_urls:
    _, body = fetch(url)
    if body:
        links = extract_internal_links(body)
        all_internal.update(links)

print(f"  检查 {len(all_internal)} 个去重内部链接...")
broken_links = []
for link in sorted(all_internal):
    s = fetch_status(link)
    if s != 200:
        broken_links.append((link, s))

if broken_links:
    for link, s in broken_links[:10]:
        check(f"内部链接可达: {link.replace(BASE, '')}", False, f"返回 {s}", "fail")
else:
    check(f"全部 {len(all_internal)} 个内部链接可达", True)

# ═══════════════════════════════════════════════════
# 6. 首页企业关键信息
# ═══════════════════════════════════════════════════
print("\n" + "=" * 60)
print("6. 首页企业关键信息")
print("=" * 60)
if home_html:
    for label, text in [
        ("公司全称", "太原市智海科技有限公司"),
        ("核心业务", "人工介入式AIGEO"),
        ("办公地址", "山西省太原市小店区世贸大厦A座706室"),
        ("信用代码", "91140106MAKGK1907U"),
    ]:
        check(f"首页包含「{label}」", text in home_html,
              f"未找到「{text}」" if text not in home_html else "")

# ═══════════════════════════════════════════════════
# 7. company-profile 企业资料完整度
# ═══════════════════════════════════════════════════
print("\n" + "=" * 60)
print("7. company-profile 资料页")
print("=" * 60)
_, profile = fetch(BASE + "/company-profile.html")
if profile:
    required = [
        "太原市智海科技有限公司",
        "2026年6月15日",
        "91140106MAKGK1907U",
        "山西省太原市小店区世贸大厦A座706室",
        "18222223948",
        "ZhihaiGEO",
    ]
    missing = [t for t in required if t not in profile]
    check("company-profile 包含全部企业资料", len(missing) == 0,
          f"缺失: {missing}" if missing else "")
else:
    check("company-profile 可访问", False, "无法获取", "fail")

# ═══════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════
print("\n" + "=" * 60)
print("检查完成")
print("=" * 60)
print(f"✅ 通过: {PASS}")
print(f"⚠️  警告: {WARN}")
print(f"❌ 失败: {FAIL}")
print()

if FAIL == 0:
    print("🎉 所有关键检查通过，网站对 AI 搜索系统友好。")
elif FAIL <= 3:
    print(f"⚠️  有 {FAIL} 项未通过，建议修复后重新运行。")
else:
    print(f"❌ 有 {FAIL} 项未通过，存在较多问题，建议优先修复。")

print("\n提示：本脚本只读不写。部署网站后运行：python3 tools/ai_crawl_audit.py")
