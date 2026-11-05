import re
from urllib.parse import parse_qs, urlparse


def extract_video_id(url_or_id: str) -> str:
    """Extracts the 11-character YouTube video ID from various URL formats."""
    url_or_id = url_or_id.strip()

    # Direct 11-character video ID
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url_or_id):
        return url_or_id

    parsed = urlparse(url_or_id)

    # youtu.be/<id>
    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        return parsed.path.lstrip("/").split("/")[0]

    # youtube.com/watch?v=<id>
    if parsed.path == "/watch":
        query_params = parse_qs(parsed.query)
        if "v" in query_params:
            return query_params["v"][0]

    # youtube.com/embed/<id> or /v/<id> or /shorts/<id>
    path_match = re.search(r"/(?:embed|v|shorts)/([a-zA-Z0-9_-]{11})", parsed.path)
    if path_match:
        return path_match.group(1)

    raise ValueError(f"Could not extract a valid YouTube video ID from: {url_or_id}")


def sanitize_filename(name: str) -> str:
    """Removes invalid filesystem characters from a string."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def format_bytes(size: int) -> str:
    """Converts a byte count into a human-readable string."""
    units = ["B", "KB", "MB", "GB"]
    unit_index = 0
    val = float(size)
    while val >= 1024.0 and unit_index < len(units) - 1:
        val /= 1024.0
        unit_index += 1
    return f"{val:.2f} {units[unit_index]}"
    