from html.parser import HTMLParser
from typing import Any, Dict, List, Set, Tuple
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


class LinkScanner:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = (
            base_url
            if base_url.startswith(("http://", "https://"))
            else f"https://{base_url}"
        )
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "LinkScannerCLI/1.0"})

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

    def check_url(self, url: str) -> Dict[str, Any]:
        """Pings a target URL using HEAD, falling back to GET if HEAD is rejected."""
        try:
            res = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            # Some servers block or return 405 on HEAD requests
            if res.status_code in (403, 405):
                res = self.session.get(
                    url, timeout=self.timeout, stream=True, allow_redirects=True
                )

            return {
                "url": url,
                "status": res.status_code,
                "ok": 200 <= res.status_code < 400,
                "error": None,
            }
        except requests.RequestException as err:
            return {
                "url": url,
                "status": None,
                "ok": False,
                "error": type(err).__name__,
            }