from collections import deque
from html.parser import HTMLParser
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urldefrag, urljoin, urlparse
import xml.etree.ElementTree as ET
import requests


class HrefParser(HTMLParser):
    """Extracts href values from <a> and <link> tags."""

    def __init__(self):
        super().__init__()
        self.links: Set[str] = set()

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]):
        if tag in ("a", "link"):
            for attr, val in attrs:
                if attr == "href" and val:
                    self.links.add(val.strip())


class WaybackRecovery:
    """Queries the Internet Archive to find working historical snapshots for broken URLs."""

    API_URL = "https://archive.org/wayback/available"

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "WaybackRecoveryCLI/1.0"})

    def find_snapshot(self, target_url: str) -> Optional[Dict[str, str]]:
        """Checks for the closest available snapshot of a broken URL."""
        try:
            res = self.session.get(
                self.API_URL,
                params={"url": target_url},
                timeout=6.0,
            )
            if res.status_code == 200:
                data = res.json()
                closest = data.get("archived_snapshots", {}).get("closest")
                if closest and closest.get("available"):
                    raw_time = closest.get("timestamp", "")
                    formatted_date = (
                        f"{raw_time[:4]}-{raw_time[4:6]}-{raw_time[6:8]}"
                        if len(raw_time) >= 8
                        else raw_time
                    )
                    return {
                        "archive_url": closest.get("url"),
                        "timestamp": formatted_date,
                    }
        except requests.RequestException:
            pass
        return None


class AIAuditor:
    """Diagnoses broken endpoints using an OpenAI-compatible LLM endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.session = requests.Session()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def diagnose_failure(
        self,
        url: str,
        status: Optional[int],
        error: Optional[str],
        raw_body: str,
        archive_info: Optional[Dict[str, str]] = None,
        referrers: Optional[List[str]] = None,
    ) -> str:
        """Sends failure context, body snippet, and archive availability to the LLM."""
        if not self.is_configured():
            return "Skipped: OPENAI_API_KEY environment variable or --api-key not set."

        clean_snippet = re.sub(r"<[^>]+>", " ", raw_body[:2000]).strip()
        clean_snippet = re.sub(r"\s+", " ", clean_snippet)

        archive_note = (
            f"Wayback snapshot found: {archive_info['archive_url']} ({archive_info['timestamp']})"
            if archive_info
            else "No Wayback snapshot found."
        )
        referrer_note = (
            f"Found on page(s): {', '.join(referrers[:3])}"
            if referrers
            else "Source page unknown."
        )

        prompt = (
            f"Analyze this broken link found during a recursive site crawl.\n"
            f"URL: {url}\n"
            f"{referrer_note}\n"
            f"HTTP Status: {status or 'Connection Failed'}\n"
            f"Network Error: {error or 'None'}\n"
            f"Archive Status: {archive_note}\n"
            f"Page Snippet/Body: {clean_snippet or 'Empty response'}\n\n"
            f"Provide a 2-sentence diagnosis:\n"
            f"1. Most probable root cause.\n"
            f"2. Suggested webmaster remediation or redirect fix."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a web infrastructure and SEO reliability engineer.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 120,
            "temperature": 0.2,
        }

        try:
            res = self.session.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=12.0,
            )
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.RequestException as exc:
            return f"AI audit failed: {exc}"


class LinkScanner:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = (
            base_url
            if base_url.startswith(("http://", "https://"))
            else f"https://{base_url}"
        )
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "LinkScannerCLI/3.1"})
        parsed = urlparse(self.base_url)
        self.base_scheme = parsed.scheme
        self.base_domain = parsed.netloc

    def fetch_sitemap_urls(
        self, sitemap_url: Optional[str] = None, _depth: int = 0
    ) -> Set[str]:
        """Fetches and parses URLs from an XML sitemap or sitemap index."""
        if _depth > 1:
            return set()

        target = (
            sitemap_url
            if sitemap_url and sitemap_url != "auto"
            else f"{self.base_scheme}://{self.base_domain}/sitemap.xml"
        )
        if not target.startswith(("http://", "https://")):
            target = f"https://{target}"

        discovered: Set[str] = set()
        try:
            res = self.session.get(target, timeout=self.timeout)
            res.raise_for_status()
            root = ET.fromstring(res.content)
        except (requests.RequestException, ET.ParseError):
            return discovered

        root_tag = root.tag.lower()
        if root_tag.endswith("sitemapindex"):
            for elem in root.iter():
                if elem.tag.lower().endswith("loc") and elem.text:
                    discovered.update(
                        self.fetch_sitemap_urls(elem.text.strip(), _depth=_depth + 1)
                    )
        else:
            for elem in root.iter():
                if elem.tag.lower().endswith("loc") and elem.text:
                    clean_url, _ = urldefrag(elem.text.strip())
                    discovered.add(clean_url)

        return discovered

    def extract_links_from_url(self, page_url: str) -> Set[str]:
        """Fetches a single page and extracts normalized absolute links."""
        res = self.session.get(page_url, timeout=self.timeout)
        content_type = res.headers.get("content-type", "").lower()
        if "text/html" not in content_type:
            return set()

        parser = HrefParser()
        parser.feed(res.text)

        resolved_links: Set[str] = set()
        for raw_link in parser.links:
            if raw_link.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full_url = urljoin(page_url, raw_link)
            clean_url, _ = urldefrag(full_url)
            resolved_links.add(clean_url)

        return resolved_links

    def crawl(
        self,
        max_depth: int = 1,
        max_pages: int = 40,
        seed_urls: Optional[Set[str]] = None,
        sitemap_source: Optional[str] = None,
    ) -> Tuple[Dict[str, List[str]], int]:
        """Performs a BFS crawl to discover URLs and map each link to its referring page(s)."""
        queue = deque([(self.base_url, 1)])
        visited_pages: Set[str] = set()
        link_referrers: Dict[str, Set[str]] = {}

        if seed_urls:
            for url in sorted(seed_urls):
                link_referrers.setdefault(url, set()).add(
                    sitemap_source or "sitemap.xml"
                )
                if urlparse(url).netloc == self.base_domain and url != self.base_url:
                    queue.append((url, 1))

        while queue and len(visited_pages) < max_pages:
            current_url, depth = queue.popleft()
            if current_url in visited_pages:
                continue

            visited_pages.add(current_url)
            try:
                page_links = self.extract_links_from_url(current_url)
            except Exception:
                continue

            for link in page_links:
                if link not in link_referrers:
                    link_referrers[link] = set()
                link_referrers[link].add(current_url)

                if depth < max_depth and urlparse(link).netloc == self.base_domain:
                    if link not in visited_pages:
                        queue.append((link, depth + 1))

        normalized_referrers = {
            link: sorted(refs) for link, refs in link_referrers.items()
        }
        return normalized_referrers, len(visited_pages)

    def check_url(self, url: str, retries: int = 0) -> Dict[str, Any]:
        """Pings a target URL, records latency, and captures body snippet if unreachable."""
        attempts = 0
        max_attempts = 1 + max(0, retries)
        last_error = None
        latency_ms = 0.0
        raw_body = ""

        while attempts < max_attempts:
            attempts += 1
            start_time = time.perf_counter()
            try:
                res = self.session.head(url, timeout=self.timeout, allow_redirects=True)
                if res.status_code in (403, 404, 405, 500, 502, 503):
                    res = self.session.get(
                        url, timeout=self.timeout, stream=False, allow_redirects=True
                    )
                    raw_body = res.text[:2048]

                latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
                return {
                    "url": url,
                    "status": res.status_code,
                    "latency_ms": latency_ms,
                    "ok": 200 <= res.status_code < 400,
                    "error": None,
                    "raw_body": raw_body,
                }
            except requests.RequestException as err:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
                last_error = type(err).__name__

        return {
            "url": url,
            "status": None,
            "latency_ms": latency_ms,
            "ok": False,
            "error": last_error,
            "raw_body": raw_body,
        }


class HTMLReporter:
    """Generates an interactive HTML dashboard with referrer links and diagnostic drawers."""

    @staticmethod
    def generate(
        results: List[Dict[str, Any]],
        base_url: str,
        output_path: str,
        pages_crawled: int = 1,
    ) -> None:
        total = len(results)
        broken = sum(1 for r in results if not r["ok"])
        alive = total - broken
        avg_latency = (
            round(sum(r.get("latency_ms", 0.0) for r in results) / total, 1) if total else 0.0
        )

        rows_html = []
        for idx, item in enumerate(results):
            status_text = str(item["status"]) if item["status"] else "ERR"
            status_class = "badge-ok" if item["ok"] else "badge-fail"
            latency = f"{item.get('latency_ms', 0)} ms"
            url = item["url"]

            details_html = []
            if item.get("referrers"):
                refs_li = "".join(
                    f"<li><a href='{r}' target='_blank' rel='noreferrer'>{r}</a></li>"
                    for r in item["referrers"]
                )
                details_html.append(
                    f"<p><strong>Referenced on ({len(item['referrers'])} source/s):</strong></p>"
                    f"<ul class='ref-list'>{refs_li}</ul>"
                )
            if item.get("error"):
                details_html.append(f"<p><strong>Error:</strong> {item['error']}</p>")
            if item.get("wayback_snapshot"):
                wb = item["wayback_snapshot"]
                details_html.append(
                    f"<p><strong>Wayback Snapshot ({wb.get('timestamp')}):</strong> "
                    f"<a href='{wb.get('archive_url')}' target='_blank' rel='noreferrer'>"
                    f"{wb.get('archive_url')}</a></p>"
                )
            if item.get("ai_diagnosis"):
                details_html.append(
                    f"<div class='ai-box'><strong>🤖 AI Diagnosis:</strong> "
                    f"<div>{item['ai_diagnosis']}</div></div>"
                )

            details_block = (
                f"<div class='drawer' id='drawer-{idx}'>{''.join(details_html)}</div>"
                if details_html
                else ""
            )
            toggle_btn = (
                f"<button class='btn-toggle' onclick='toggleDrawer(\"drawer-{idx}\")'>Details</button>"
                if details_html
                else "-"
            )

            filter_tag = "broken" if not item["ok"] else "ok"
            if item.get("wayback_snapshot"):
                filter_tag += " archived"

            rows_html.append(
                f"<tr class='data-row' data-status='{filter_tag}'>"
                f"<td><span class='badge {status_class}'>{status_text}</span></td>"
                f"<td class='url-cell'><a href='{url}' target='_blank' rel='noreferrer'>{url}</a></td>"
                f"<td><code>{latency}</code></td>"
                f"<td>{toggle_btn}</td>"
                f"</tr>"
                f"{f'<tr class=\"drawer-row\"><td colspan=\"4\">{details_block}</td></tr>' if details_block else ''}"
            )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Link Audit Dashboard - {base_url}</title>
<style>
  :root {{
    --bg: #0f172a; --surface: #1e293b; --border: #334155; --text: #f8fafc;
    --text-muted: #94a3b8; --primary: #38bdf8; --success: #22c55e; --danger: #ef4444;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 32px 20px; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  header {{ margin-bottom: 28px; }}
  header h1 {{ font-size: 26px; font-weight: 700; color: #fff; }}
  header p {{ color: var(--text-muted); font-size: 14px; margin-top: 4px; }}
  .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 28px; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 18px; }}
  .card-label {{ font-size: 12px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; letter-spacing: 0.5px; }}
  .card-val {{ font-size: 28px; font-weight: 700; margin-top: 8px; }}
  .controls {{ display: flex; flex-wrap: wrap; gap: 12px; justify-content: space-between; margin-bottom: 20px; }}
  .search-input {{ background: var(--surface); border: 1px solid var(--border); color: #fff; padding: 10px 14px; border-radius: 8px; width: 320px; outline: none; }}
  .filters {{ display: flex; gap: 8px; }}
  .btn-filter {{ background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; }}
  .btn-filter.active {{ background: var(--primary); color: #000; border-color: var(--primary); }}
  table {{ width: 100%; border-collapse: collapse; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }}
  th, td {{ padding: 12px 16px; text-align: left; font-size: 14px; border-bottom: 1px solid var(--border); }}
  th {{ background: #131d31; color: var(--text-muted); font-weight: 600; font-size: 12px; text-transform: uppercase; }}
  .url-cell a {{ color: var(--primary); text-decoration: none; word-break: break-all; }}
  .url-cell a:hover {{ text-decoration: underline; }}
  .badge {{ display: inline-block; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 700; font-family: monospace; }}
  .badge-ok {{ background: rgba(34, 197, 94, 0.15); color: var(--success); }}
  .badge-fail {{ background: rgba(239, 68, 68, 0.15); color: var(--danger); }}
  .btn-toggle {{ background: transparent; border: 1px solid var(--border); color: var(--text-muted); padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; }}
  .btn-toggle:hover {{ color: var(--text); border-color: var(--text-muted); }}
  .drawer {{ display: none; background: #0b1120; border-radius: 8px; padding: 14px; margin: 6px 0; border-left: 3px solid var(--danger); }}
  .drawer.open {{ display: block; }}
  .drawer p {{ font-size: 13px; margin-bottom: 6px; }}
  .ref-list {{ margin: 6px 0 10px 20px; font-size: 12px; color: var(--text-muted); }}
  .ref-list a {{ color: var(--text-muted); word-break: break-all; }}
  .ref-list a:hover {{ color: var(--primary); }}
  .ai-box {{ margin-top: 10px; background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.2); padding: 10px; border-radius: 6px; font-size: 13px; }}
  .drawer-row td {{ padding: 0 16px; border-bottom: 1px solid var(--border); }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>Link Health & Diagnostic Dashboard</h1>
    <p>Target: <strong>{base_url}</strong></p>
  </header>
  <div class="metrics-grid">
    <div class="card"><div class="card-label">Pages Crawled</div><div class="card-val">{pages_crawled}</div></div>
    <div class="card"><div class="card-label">Unique Links</div><div class="card-val">{total}</div></div>
    <div class="card"><div class="card-label">Healthy</div><div class="card-val" style="color:var(--success)">{alive}</div></div>
    <div class="card"><div class="card-label">Broken</div><div class="card-val" style="color:var(--danger)">{broken}</div></div>
    <div class="card"><div class="card-label">Avg Latency</div><div class="card-val">{avg_latency} ms</div></div>
  </div>
  <div class="controls">
    <input type="text" id="searchInput" class="search-input" placeholder="Filter by URL..." onkeyup="filterTable()">
    <div class="filters">
      <button class="btn-filter active" onclick="setFilter('all', this)">All</button>
      <button class="btn-filter" onclick="setFilter('broken', this)">Broken Only</button>
      <button class="btn-filter" onclick="setFilter('archived', this)">Archived</button>
    </div>
  </div>
  <table>
    <thead><tr><th style="width:100px;">Status</th><th>Endpoint URL</th><th style="width:120px;">Latency</th><th style="width:100px;">Actions</th></tr></thead>
    <tbody id="tableBody">{''.join(rows_html)}</tbody>
  </table>
</div>
<script>
  let activeFilter = 'all';
  function setFilter(type, btn) {{
    activeFilter = type;
    document.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    filterTable();
  }}
  function filterTable() {{
    const query = document.getElementById('searchInput').value.toLowerCase();
    const rows = document.querySelectorAll('.data-row');
    rows.forEach(row => {{
      const text = row.querySelector('.url-cell').textContent.toLowerCase();
      const statusTag = row.getAttribute('data-status');
      const matchesSearch = text.includes(query);
      const matchesFilter = (activeFilter === 'all') || (statusTag.includes(activeFilter));
      const nextDrawerRow = row.nextElementSibling;
      const isVisible = matchesSearch && matchesFilter;
      row.style.display = isVisible ? '' : 'none';
      if (nextDrawerRow && nextDrawerRow.classList.contains('drawer-row')) {{
        if (!isVisible) nextDrawerRow.style.display = 'none';
      }}
    }});
  }}
  function toggleDrawer(id) {{
    const el = document.getElementById(id);
    if (el) {{
      el.classList.toggle('open');
      const parentRow = el.closest('.drawer-row');
      if (parentRow) {{
        parentRow.style.display = el.classList.contains('open') ? '' : 'none';
      }}
    }}
  }}
</script>
</body>
</html>"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)