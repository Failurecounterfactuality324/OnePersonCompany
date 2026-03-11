import os
from pathlib import Path

os.environ["OPC_LLM_ENABLED"] = "false"

from onepersoncompany.models import InputUpdate, Language, TaskStatus
from onepersoncompany.service import OnePersonCompanyService
from onepersoncompany.storage import JsonStorage


def build_service(tmp_path: Path) -> OnePersonCompanyService:
    storage = JsonStorage(base_dir=tmp_path)
    service = OnePersonCompanyService(storage=storage)
    service.init_seed_tasks()
    return service


def test_daily_brief_generation(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    result = service.run_daily_brief(
        [InputUpdate(summary="Investigate churn for trial users", source="cli")],
        lang=Language.EN,
    )
    assert result.agent == "ChiefOfStaff"
    assert "Daily Brief" in result.artifact.title
    assert "Top Priorities" in result.artifact.content


def test_launch_pack_generation(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    result = service.run_launch_pack(
        [InputUpdate(summary="Ship billing retry flow", source="cli")],
        lang=Language.EN,
    )
    assert result.agent == "LaunchManager"
    assert "Launch Pack" in result.artifact.title
    assert "Release Notes" in result.artifact.content
    assert "Support Suggestions" in result.artifact.content


def test_weekly_review_generation(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    result = service.run_weekly_review(lang=Language.ZH)
    assert result.artifact.title == "周复盘"
    assert "总任务数" in result.artifact.content


def test_mark_task_done(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    target = service.list_tasks()[0]
    updated = service.mark_task_status(task_id=target.id, status=TaskStatus.DONE)
    assert updated.status == TaskStatus.DONE


def test_share_copy_generation(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    service.run_daily_brief([InputUpdate(summary="Fix churn issue", source="cli")], lang=Language.ZH)
    share = service.generate_share_copy(lang=Language.ZH)
    assert "OnePersonCompany" in share.title or "OnePersonCompany" in share.content
