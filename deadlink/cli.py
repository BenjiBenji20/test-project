import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import sys
from urllib.parse import urlparse
from checker import AIAuditor, HTMLReporter, LinkScanner, WaybackRecovery


def main():
    parser = argparse.ArgumentParser(
        prog="deadlink",
        description="CLI tool to detect dead links, find archive snapshots, and generate visual HTML audit dashboards.",
    )
    parser.add_argument("url", type=str, help="Target URL to inspect (e.g., example.com)")
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
        help="Maximum number of links to check",
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
    print(f"Fetching links from: {scanner.base_url}...")

    try:
        links = scanner.extract_links()
    except Exception as exc:
        print(f"Error fetching source URL: {exc}", file=sys.stderr)
        sys.exit(1)

    target_domain = urlparse(scanner.base_url).netloc
    if args.internal_only:
        links = {u for u in links if urlparse(u).netloc == target_domain}

    sorted_links = sorted(links)
    if args.limit and args.limit > 0:
        sorted_links = sorted_links[:args.limit]

    print(
        f"Scanning {len(sorted_links)} link(s) with {args.workers} worker(s) "
        f"[Wayback: {'ON' if args.wayback else 'OFF'} | AI Audit: {'ON' if args.ai_audit else 'OFF'}]...\n"
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
            results.append(data)

            status_str = str(data["status"]) if data["status"] else "ERR"
            latency_str = f"{data['latency_ms']}ms".rjust(7)

            if data["ok"]:
                if not args.broken_only:
                    print(f"[{status_str}] [{latency_str}] OK  : {data['url']}")
            else:
                broken_count += 1
                reason = f" ({data['error']})" if data["error"] else ""
                print(f"[{status_str}] [{latency_str}] FAIL: {data['url']}{reason}")

                archive_info = None
                if args.wayback:
                    print("       📦 Searching Internet Archive for snapshots...")
                    archive_info = wayback_recovery.find_snapshot(data["url"])
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
                        url=data["url"],
                        status=data["status"],
                        error=data["error"],
                        raw_body=data["raw_body"],
                        archive_info=archive_info,
                    )
                    data["ai_diagnosis"] = diagnosis
                    print(f"       💡 AI Report: {diagnosis}")

                if args.wayback or args.ai_audit:
                    print()

    alive_count = len(results) - broken_count
    print(f"Done: {alive_count} accessible, {broken_count} broken.")

    # Generate interactive HTML dashboard if requested
    if args.html:
        HTMLReporter.generate(results, scanner.base_url, args.html)
        print(f"Generated visual HTML report: {args.html}")

    # Export machine-readable JSON if requested
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