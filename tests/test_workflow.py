from pathlib import Path


WORKFLOW = Path(".github/workflows/autoposter.yml")
VIDEO_WORKFLOW = Path(".github/workflows/videos.yml")


def test_workflow_is_manual_and_safe():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "cancel-in-progress: false" in text
    assert 'AUTOPOSTER_DRY_RUN: "false"' in text
    assert "TELEGRAM_BOT_TOKEN" in text
    assert "TELEGRAM_CHAT_ID" in text
    assert "git add storage/published.json" in text
    assert "git add ." not in text


def test_video_workflow_is_manual_safe_preview_by_default():
    text = VIDEO_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "PEXELS_API_KEY" in text
    assert "PIXABAY_API_KEY" in text
    assert "default: false" in text
    assert "python video_main.py" in text
    assert "git add storage/published.json" in text
    assert "git add ." not in text
