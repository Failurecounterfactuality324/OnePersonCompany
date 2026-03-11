from __future__ import annotations

import argparse
import json
import sys
from typing import List

from .config import settings
from .logging_setup import get_logger, setup_logging
from .models import InputUpdate, Language, TaskStatus
from .service import OnePersonCompanyService

setup_logging()
logger = get_logger("onepersoncompany.cli")


def parse_updates(raw_updates: List[str]) -> List[InputUpdate]:
    return [InputUpdate(summary=item, source="cli") for item in raw_updates]


def main() -> None:
    default_lang = settings.default_lang if settings.default_lang in [Language.ZH.value, Language.EN.value] else Language.ZH.value
    parser = argparse.ArgumentParser(description="OnePersonCompany CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Seed default tasks")

    run_parser = subparsers.add_parser("run", help="Run an agent flow")
    run_parser.add_argument("flow", choices=["daily-brief", "launch-pack", "weekly-review"])
    run_parser.add_argument("--update", action="append", default=[], help="Founder update text")
    run_parser.add_argument("--lang", choices=[Language.ZH.value, Language.EN.value], default=default_lang)

    task_parser = subparsers.add_parser("task", help="Manage tasks")
    task_subparsers = task_parser.add_subparsers(dest="task_command", required=True)

    task_subparsers.add_parser("list", help="List all tasks")

    task_add = task_subparsers.add_parser("add", help="Add a task")
    task_add.add_argument("--title", required=True, help="Task title")
    task_add.add_argument("--priority", type=int, default=3, choices=[1, 2, 3, 4, 5], help="Task priority")
    task_add.add_argument("--source", default="cli", help="Task source")

    task_done = task_subparsers.add_parser("done", help="Mark task done")
    task_done.add_argument("--id", required=True, help="Task ID")

    share_parser = subparsers.add_parser("share", help="Generate social share copy")
    share_parser.add_argument("--lang", choices=[Language.ZH.value, Language.EN.value], default=default_lang)

    demo_parser = subparsers.add_parser("demo", help="Run one-command demo flow")
    demo_parser.add_argument("name", choices=["day0"])
    demo_parser.add_argument("--lang", choices=[Language.ZH.value, Language.EN.value], default=default_lang)

    args = parser.parse_args()
    logger.info("CLI command received: %s", args.command)
    try:
        service = OnePersonCompanyService()
    except ValueError as exc:
        logger.exception("CLI init failed: %s", exc)
        print(f"LLM config error: {exc}", file=sys.stderr)
        print("Tip: set provider key env vars or run with OPC_LLM_ENABLED=false for local fallback.", file=sys.stderr)
        raise SystemExit(2)

    if args.command == "init":
        created = service.init_seed_tasks()
        print(json.dumps({"created_tasks": len(created)}, ensure_ascii=False))
        return

    if args.command == "task":
        if args.task_command == "list":
            payload = [task.model_dump(mode="json") for task in service.list_tasks()]
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        if args.task_command == "add":
            task = service.add_task(title=args.title, priority=args.priority, source=args.source)
            print(json.dumps(task.model_dump(mode="json"), ensure_ascii=False, indent=2))
            return
        if args.task_command == "done":
            task = service.mark_task_status(task_id=args.id, status=TaskStatus.DONE)
            print(json.dumps(task.model_dump(mode="json"), ensure_ascii=False, indent=2))
            return

    if args.command == "share":
        share = service.generate_share_copy(lang=Language(args.lang))
        print(f"{share.title}\n\n{share.content}")
        return

    if args.command == "demo":
        payload = service.run_demo_day0(lang=Language(args.lang))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    lang = Language(args.lang)
    updates = parse_updates(args.update)
    if args.flow == "daily-brief":
        result = service.run_daily_brief(updates, lang=lang)
    elif args.flow == "launch-pack":
        result = service.run_launch_pack(updates, lang=lang)
    else:
        result = service.run_weekly_review(lang=lang)

    print(result.artifact.content)
    logger.info("CLI flow completed: %s", args.flow)


if __name__ == "__main__":
    main()
