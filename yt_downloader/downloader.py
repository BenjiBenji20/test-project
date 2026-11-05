import os
import sys
from typing import Optional
import requests
from utils import format_bytes


class StreamDownloader:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()

    def download(self, stream_url: str, output_path: str, chunk_size: int = 1024 * 1024) -> None:
        """Streams the video content to disk with a terminal progress bar."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }

        with self.session.get(stream_url, headers=headers, stream=True, timeout=15) as res:
            res.raise_for_status()

            total_size = int(res.headers.get("content-length", 0))
            downloaded = 0

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            with open(output_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        bar_len = 30
                        filled = int(bar_len * downloaded / total_size)
                        bar = "=" * filled + "-" * (bar_len - filled)
                        sys.stdout.write(
                            f"\r[{bar}] {percent:.1f}% ({format_bytes(downloaded)} / {format_bytes(total_size)})"
                        )
                    else:
                        sys.stdout.write(f"\rDownloaded {format_bytes(downloaded)}")
                    sys.stdout.flush()

            sys.stdout.write("\n")

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Removes the target file from disk if it exists."""
        if os.path.isfile(file_path):
            os.remove(file_path)
            return True
        return False