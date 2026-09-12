import runpy
from pathlib import Path

import dotenv


CONFIG_PATH = Path(__file__).parents[1] / "config.py"


def run_config(monkeypatch, env_value):
    if env_value is None:
        monkeypatch.delenv("AUTOPOSTER_DRY_RUN", raising=False)
    else:
        monkeypatch.setenv("AUTOPOSTER_DRY_RUN", env_value)

    monkeypatch.setattr(dotenv, "load_dotenv", lambda: None)
    return runpy.run_path(str(CONFIG_PATH))


def test_dry_run_reads_false_from_environment(monkeypatch):
    namespace = run_config(monkeypatch, "false")

    assert namespace["DRY_RUN"] is False


def test_dry_run_reads_true_from_environment(monkeypatch):
    namespace = run_config(monkeypatch, "true")

    assert namespace["DRY_RUN"] is True


def test_dry_run_defaults_to_true_when_environment_is_missing(monkeypatch):
    namespace = run_config(monkeypatch, None)

    assert namespace["DRY_RUN"] is True


def test_dry_run_defaults_to_true_for_invalid_environment(monkeypatch):
    namespace = run_config(monkeypatch, "sometimes")

    assert namespace["DRY_RUN"] is True


def test_dotenv_load_precedes_dry_run_evaluation(monkeypatch):
    calls = []

    def load_test_dotenv():
        calls.append("load_dotenv")
        monkeypatch.setenv("AUTOPOSTER_DRY_RUN", "false")

    monkeypatch.delenv("AUTOPOSTER_DRY_RUN", raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", load_test_dotenv)

    namespace = runpy.run_path(str(CONFIG_PATH))

    assert calls == ["load_dotenv"]
    assert namespace["DRY_RUN"] is False
