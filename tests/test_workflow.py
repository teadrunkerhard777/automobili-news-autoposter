from pathlib import Path


WORKFLOW = Path(".github/workflows/autoposter.yml")


def test_workflow_has_cloud_schedule_and_safe_dispatch():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" in text
    assert 'cron: "0 8 * * *"' in text
    assert 'cron: "0 15 * * *"' in text
    assert "cancel-in-progress: false" in text
    assert 'AUTOPOSTER_DRY_RUN: "false"' in text
    assert "TELEGRAM_BOT_TOKEN" in text
    assert "TELEGRAM_CHAT_ID" in text
    assert "git add storage/published.json" in text
    assert "git add ." not in text
