from html.parser import HTMLParser
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
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

        prompt = (
            f"Analyze this broken link from a website scan.\n"
            f"URL: {url}\n"
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
        self.session.headers.update({"User-Agent": "LinkScannerCLI/2.0"})

    def extract_links(self) -> Set[str]:
        """Fetches the source page and resolves all absolute URLs."""
        res = self.session.get(self.base_url, timeout=self.timeout)
        res.raise_for_status()

        parser = HrefParser()
        parser.feed(res.text)

        resolved_links: Set[str] = set()
        for raw_link in parser.links:
            if raw_link.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            resolved_links.add(urljoin(self.base_url, raw_link))

        return resolved_links

    def check_url(self, url: str, retries: int = 0) -> Dict[str, Any]:
        """Pings a target URL, records latency, and captures body data if unreachable."""
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
    """Generates a standalone, interactive HTML report with filtering and diagnostic drawers."""

    @staticmethod
    def generate(results: List[Dict[str, Any]], base_url: str, output_path: str) -> None:
        total = len(results)
        broken = sum(1 for r in results if not r["ok"])
        alive = total - broken
        recovered = sum(1 for r in results if r.get("wayback_snapshot"))
        avg_latency = (
            round(sum(r.get("latency_ms", 0.0) for r in results) / total, 1) if total else 0.0
        )

        rows_html = []
        for idx, item in enumerate