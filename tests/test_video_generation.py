from generation.video import generate_video_temp


def test_video_generator_creates_streamable_mp4():
    item = {
        "title": "Toyota представила новый кроссовер",
        "description": "Модель получила гибридную силовую установку.",
        "source": "Автоновости дня",
    }
    settings = {
        "duration_seconds": 1,
        "fps": 2,
        "width": 360,
        "height": 640,
        "background": "#101820",
        "accent": "#E63946",
        "highlight": "#F4D35E",
        "foreground": "#FFFFFF",
        "muted": "#D5DEE8",
    }

    video = generate_video_temp(item, settings)
    try:
        assert video.mime_type == "video/mp4"
        assert video.size_bytes > 0
        assert video.path.read_bytes()[4:8] == b"ftyp"
    finally:
        video.path.unlink()
