import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import sys
from urllib.parse import urlparse
from checker import AIAuditor, HTMLReporter, LinkScanner, WaybackRecovery


def main():
    parser = argparse.ArgumentParser(
        prog="deadlink",
        description="CLI tool to detect dead links, parse XML sitemaps, trace referring pages, and run AI audits.",
    )
    parser.add_argument("url", type=str, help="Target URL to inspect (e.g., example.com)")
    parser.add_argument(
        "-s",
        "--sitemap",
        nargs="?",
        const="auto",
        default=None,
        help="Seed crawl from /sitemap.xml or a custom sitemap URL",
    )
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=1,
        help="Crawl depth for discovering links across internal pages (default: 1)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=40,
        help="Maximum internal pages to visit during recursive crawl (default: 40)",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout in seconds for checking individual links (default: 5.0)",
    )
    parser.add_argument(
        "-r",
        "--retries",
        type=int,
        default=0,
        help="Number of retries for failed requests (default: 0)",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=5,
        help="Number of concurrent worker threads (default: 5)",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=None,
        help="Maximum number of unique links to verify",
    )
    parser.add_argument(
        "--internal-only",
        action="store_true",
        help="Only inspect links matching the target domain",
    )
    parser.add_argument(
        "-b",
        "--broken-only",
        action="store_true",
        help="Only display dead or failed links in stdout",
    )
    parser.add_argument(
        "--wayback",
        action="store_true",
        help="Query the Internet Archive to find working replacement snapshots for broken links",
    )
    parser.add_argument(
        "-a",
        "--ai-audit",
        action="store_true",
        help="Enable AI root-cause analysis on broken links",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for AI audit (or set OPENAI_API_KEY environment variable)",
    )
    parser.add_argument(
        "--api-base",
        type=str,
        default="https://api.openai.com/v1",
        help="OpenAI-compatible API base URL (e.g., Ollama, Groq, OpenRouter)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        metavar="FILE",
        help="Export full results and diagnostics to a JSON file",
    )
    parser.add_argument(
        "--html",
        type=str,
        metavar="FILE",
        help="Generate an interactive, standalone HTML audit report",
    )

    args = parser.parse_args()

    scanner = LinkScanner(args.url, timeout=args.timeout)

    sitemap_urls = set()
    sitemap_label = None
    if args.sitemap:
        sitemap_label = (
            f"{scanner.base_scheme}://{scanner.base_domain}/sitemap.xml"
            if args.sitemap == "auto"
            else args.sitemap
        )
        print(f"Parsing sitemap: {sitemap_label}...")
        sitemap_urls = scanner.fetch_sitemap_urls(args.sitemap)
        print(f"Discovered {len(sitemap_urls)} URL(s) from sitemap.")

    print(f"Crawling {scanner.base_url} (depth={args.depth}, max_pages={args.max_pages})...")

    try:
        link_referrers, pages_crawled = scanner.crawl(
            max_depth=args.depth,
            max_pages=args.max_pages,
            seed_urls=sitemap_urls,
            sitemap_source=sitemap_label,
        )
    except Exception as exc:
        print(f"Error during crawl: {exc}", file=sys.stderr)
        sys.exit(1)

    all_links = set(link_referrers.keys())
    target_domain = urlparse(scanner.base_url).netloc
    if args.internal_only:
        all_links = {u for u in all_links if urlparse(u).netloc == target_domain}

    sorted_links = sorted(all_links)
    if args.limit and args.limit > 0:
        sorted_links = sorted_links[:args.limit]

    print(
        f"Crawled {pages_crawled} page(s). Verifying {len(sorted_links)} unique link(s) "
        f"with {args.workers} worker(s)...\n"
    )

    ai_auditor = AIAuditor(api_key=args.api_key, api_base=args.api_base)
    wayback_recovery = WaybackRecovery()

    results = []
    broken_count = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_url = {
            executor.submit(scanner.check_url, link, args.retries): link
            for link in sorted_links
        }

        for future in as_completed(future_to_url):
            data = future.result()
            target_link = data["url"]
            referrers = link_referrers.get(target_link, [])
            data["referrers"] = referrers
            results.append(data)

            status_str = str(data["status"]) if data["status"] else "ERR"
            latency_str = f"{data['latency_ms']}ms".rjust(7)

            if data["ok"]:
                if not args.broken_only:
                    print(f"[{status_str}] [{latency_str}] OK  : {target_link}")
            else:
                broken_count += 1
                reason = f" ({data['error']})" if data["error"] else ""
                print(f"[{status_str}] [{latency_str}] FAIL: {target_link}{reason}")

                if referrers:
                    primary_ref = referrers[0]
                    more = f" (+{len(referrers)-1} more)" if len(referrers) > 1 else ""
                    print(f"       🔗 Found on: {primary_ref}{more}")

                archive_info = None
                if args.wayback:
                    print("       📦 Searching Internet Archive for snapshots...")
                    archive_info = wayback_recovery.find_snapshot(target_link)
                    data["wayback_snapshot"] = archive_info
                    if archive_info:
                        print(
                            f"       ✨ Archive Found ({archive_info['timestamp']}): {archive_info['archive_url']}"
                        )
                    else:
                        print("       ❌ No archived snapshot exists on Wayback Machine.")

                if args.ai_audit:
                    print("       🤖 Running AI diagnosis...")
                    diagnosis = ai_auditor.diagnose_failure(
                        url=target_link,
                        status=data["status"],
                        error=data["error"],
                        raw_body=data["raw_body"],
                        archive_info=archive_info,
                        referrers=referrers,
                    )
                    data["ai_diagnosis"] = diagnosis
                    print(f"       💡 AI Report: {diagnosis}")

                print()

    alive_count = len(results) - broken_count
    print(f"Done: {alive_count} accessible, {broken_count} broken across {pages_crawled} page(s).")

    if args.html:
        HTMLReporter.generate(
            results, scanner.base_url, args.html, pages_crawled=pages_crawled
        )
        print(f"Generated visual HTML report: {args.html}")

    if args.output:
        for item in results:
            item.pop("raw_body", None)
        results.sort(key=lambda item: item["url"])
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Saved full report to: {args.output}")

    if broken_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()