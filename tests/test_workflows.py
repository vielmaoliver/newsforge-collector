from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scheduled_workflows_are_disabled_until_explicit_activation() -> None:
    for name in ("collect.yml", "keepalive.yml"):
        text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "vars.NEWSFORGE_COLLECTOR_ENABLED == 'true'" in text


def test_workflows_use_only_pinned_github_owned_actions() -> None:
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("uses:"):
                continue
            action = stripped.split("uses:", 1)[1].strip().split("#", 1)[0].strip()
            assert action.startswith("actions/")
            assert "@" in action
            revision = action.rsplit("@", 1)[1]
            assert len(revision) == 40
            assert all(char in "0123456789abcdef" for char in revision.lower())


def test_workflows_do_not_enable_forbidden_features() -> None:
    forbidden = (
        "upload-artifact",
        "actions/cache",
        "larger-runner",
        "git lfs",
        "codespaces",
    )
    combined = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in (ROOT / ".github" / "workflows").glob("*.yml")
    )
    for token in forbidden:
        assert token not in combined
