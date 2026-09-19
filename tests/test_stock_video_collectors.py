from collectors.pexels_video_collector import collect_pexels_videos
from collectors.pixabay_video_collector import collect_pixabay_videos


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_pexels_selects_compact_vertical_mp4(monkeypatch):
    request = {}
    payload = {"videos": [{
        "id": 42, "duration": 12,
        "url": "https://www.pexels.com/video/42/",
        "video_files": [{
            "file_type": "video/mp4",
            "link": "https://video.test/car.mp4",
            "width": 720, "height": 1280,
            "file_size": 8_000_000,
        }],
    }]}

    def get(url, **kwargs):
        request.update(url=url, **kwargs)
        return Response(payload)

    monkeypatch.setattr("collectors.pexels_video_collector.requests.get", get)
    items = collect_pexels_videos(
        "key", "scenic car drive", "portrait", 30, 35, 49_000_000
    )

    assert request["params"]["query"] == "scenic car drive"
    assert request["params"]["orientation"] == "portrait"
    assert items[0]["media_id"] == "pexels:42"


def test_pixabay_uses_safe_transportation_film_search(monkeypatch):
    request = {}
    payload = {"hits": [{
        "id": 77, "duration": 14,
        "pageURL": "https://pixabay.com/videos/id-77/",
        "videos": {"medium": {
            "url": "https://cdn.test/car.mp4",
            "width": 1920, "height": 1080,
            "size": 12_000_000,
        }},
    }]}

    def get(url, **kwargs):
        request.update(url=url, **kwargs)
        return Response(payload)

    monkeypatch.setattr("collectors.pixabay_video_collector.requests.get", get)
    items = collect_pixabay_videos(
        "key", "car sunset road", 30, 35, 49_000_000
    )

    assert request["params"]["category"] == "transportation"
    assert request["params"]["video_type"] == "film"
    assert request["params"]["safesearch"] == "true"
    assert items[0]["media_id"] == "pixabay:77"
