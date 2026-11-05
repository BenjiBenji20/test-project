from typing import Any, Dict, Optional
import requests


class YouTubeExtractor:
    INNERTUBE_URL = "https://www.youtube.com/youtubei/v1/player"
    DEFAULT_HEADERS = {
        "User-Agent": (
            "com.google.android.youtube/19.09.37 "
            "(Linux; U; Android 11; US) gzip"
        ),
        "Content-Type": "application/json",
    }

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()

    def get_video_info(self, video_id: str) -> Dict[str, Any]:
        """Queries the Innertube API using an Android client context to obtain stream URLs."""
        payload = {
            "videoId": video_id,
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": "19.09.37",
                    "androidSdkVersion": 30,
                    "hl": "en",
                    "gl": "US",
                }
            },
        }

        response = self.session.post(
            self.INNERTUBE_URL,
            json=payload,
            headers=self.DEFAULT_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        playability = data.get("playabilityStatus", {})
        if playability.get("status") != "OK":
            reason = playability.get("reason", "Video is unavailable or restricted.")
            raise RuntimeError(f"Unable to play video: {reason}")

        return data

    def select_best_progressive_stream(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Selects the highest-resolution progressive format (muxed audio + video)."""
        streaming_data = player_data.get("streamingData", {})
        formats = streaming_data.get("formats", [])

        if not formats:
            raise RuntimeError("No direct progressive streams available for this video.")

        # Filter formats that have a direct URL and valid video dimensions
        valid_streams = [
            fmt for fmt in formats
            if fmt.get("url") and fmt.get("qualityLabel")
        ]

        if not valid_streams:
            raise RuntimeError("Streams require signature deciphering or are DASH-only.")

        # Sort descending by resolution (height)
        valid_streams.sort(key=lambda x: x.get("height", 0), reverse=True)
        return valid_streams[0]