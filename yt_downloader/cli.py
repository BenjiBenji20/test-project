import argparse
import os
import sys
from downloader import StreamDownloader
from extractor import YouTubeExtractor
from utils import extract_video_id, sanitize_filename


def main():
    parser = argparse.ArgumentParser(
        prog="yt-download",
        description="CLI tool to download YouTube videos using requests.",
    )
    parser.add_argument(
        "url",
        type=str,
        help="YouTube video URL or 11-character video ID",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=".",
        help="Directory to save downloaded files (default: current directory)",
    )

    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.url)
        print(f"Target Video ID : {video_id}")

        extractor = YouTubeExtractor()
        downloader = StreamDownloader()

        print("Fetching stream metadata...")
        data = extractor.get_video_info(video_id)

        title = data.get("videoDetails", {}).get("title", f"video_{video_id}")
        clean_title = sanitize_filename(title)
        print(f"Title           : {title}")

        best_stream = extractor.select_best_progressive_stream(data)
        quality = best_stream.get("qualityLabel", "Unknown")
        print(f"Selected Quality: {quality}")

        filename = f"{clean_title}.mp4"
        dest_path = os.path.join(args.output_dir, filename)
        print(f"Saving to       : {dest_path}")

        downloader.download(best_stream["url"], dest_path)
        print("Download finished.")

    except KeyboardInterrupt:
        print("\nDownload canceled by user.")
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()