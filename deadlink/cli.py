import argparse
import json
import sys
from urllib.parse import urlparse
from checker import LinkScanner


def main():
    parser = argparse.ArgumentParser(
        prog="deadlink",
        description="CLI tool to detect broken links and dead references on any web page.",
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
        "--internal-only",
        action="store_true",
        help="Only inspect links matching the target domain",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        metavar="FILE",
        help="Export results to a JSON file",
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

    print(f"Found {len(links)} link(s). Verifying endpoints...\n")

    results = []
    broken_count = 0

    for link in sorted(links):
        data = scanner.check_url(link)
        results.append(data)

        status_str = str(data["status"]) if data["status"] else "ERR"
        if data["ok"]:
            print(f"[{status_str}] OK  : {data['url']}")
        else:
            broken_count += 1
            reason = f" ({data['error']})" if data["error"] else ""
            print(f"[{status_str}] FAIL: {data['url']}{reason}")

    alive_count = len(results) - broken_count
    print(f"\nDone: {alive_count} accessible, {broken_count} broken.")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Saved report to: {args.output}")

    if broken_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()