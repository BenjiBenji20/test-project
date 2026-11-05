import argparse
import os
import sys
from downloader import StreamDownloader
from extractor import YouTubeExtractor
from utils import extract_video_id, sanitize_filename


def main():
    parser = argparse.ArgumentParser(
        prog="yt-download",
        description="CLI tool to download or delete YouTube videos using requests.",
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
        help="Directory where video files are saved or looked up (default: current directory)",
    )
    parser.add_argument(
        "-d",
        "--delete",
        action="store_true",
        help="Delete the downloaded video file corresponding to the URL instead of downloading",
    )

    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.url)
        print(f"Target Video ID : {video_id}")

        extractor = YouTubeExtractor()
        downloader = StreamDownloader()

        print("Fetching video metadata...")
        data = extractor.get_video_info(video_id)

        title = data.get("videoDetails", {}).get("title", f"video_{video_id}")
        clean_title = sanitize_filename(title)
        filename = f"{clean_title}.mp4"
        target_path = os.path.join(args.output_dir, filename)

        # Deletion branch
        if args.delete:
            if downloader.delete_file(target_path):
                print(f"Successfully deleted: {target_path}")
            else:
                print(f"File not found: {target_path}", file=sys.stderr)
                sys.exit(1)
            return

        # Download branch
        print(f"Title           : {title}")
        best_stream = extractor.select_best_progressive_stream(data)
        quality = best_stream.get("qualityLabel", "Unknown")
        print(f"Selected Quality: {quality}")
        print(f"Saving to       : {target_path}")

        downloader.download(best_stream["url"], target_path)
        print("Download finished.")

    except KeyboardInterrupt:
        print("\nOperation canceled by user.")
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()