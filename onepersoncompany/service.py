from __future__ import annotations

import json
from datetime import date
from typing import Dict, List, Optional

from .agents import ChiefOfStaffAgent, LaunchManagerAgent, MarketResearcherAgent, SupportResponderAgent
from .config import settings
from .llm import LLMClient
from .logging_setup import get_logger
from .models import AgentResult, Artifact, ArtifactType, InputUpdate, Language, ShareCopy, SharePack, Task, TaskStatus
from .storage import JsonStorage

logger = get_logger("onepersoncompany.service")


class OnePersonCompanyService:
    def __init__(self, storage: JsonStorage | None = None) -> None:
        self.storage = storage or JsonStorage()
        self.chief = ChiefOfStaffAgent()
        self.market = MarketResearcherAgent()
        self.launch = LaunchManagerAgent()
        self.support = SupportResponderAgent()
        self.llm_client: Optional[LLMClient] = None
        self.llm_init_error: Optional[str] = None
        if settings.llm_enabled:
            try:
                self.llm_client = LLMClient()
                logger.info("LLM client enabled: provider=%s model=%s", settings.llm_provider, settings.llm_model)
            except ValueError as exc:
                self.llm_init_error = str(exc)
                logger.warning("LLM client init failed: %s", exc)
                if not settings.llm_strict:
                    self.llm_client = None

    def init_seed_tasks(self) -> List[Task]:
        if settings.default_lang == Language.EN.value:
            default_tasks = [
                "Define this week's top growth hypothesis",
                "Ship one customer-facing improvement",
                "Reply to all support messages within 24h",
                "Publish a short weekly build-in-public update",
            ]
        else:
            default_tasks = [
                "明确本周最重要增长假设",
                "交付一个用户可感知改进",
                "24 小时内回复全部用户反馈",
                "发布一条本周 build-in-public 更新",
            ]
        existing_titles = {task.title for task in self.storage.list_tasks()}
        created = []
        for title in default_tasks:
            if title not in existing_titles:
                created.append(self.storage.create_task(title=title, priority=2, source="seed"))
        return created

    def list_tasks(self) -> List[Task]:
        return self.storage.list_tasks()

    def add_task(self, title: str, priority: int = 3, source: str = "manual") -> Task:
        return self.storage.create_task(title=title, priority=priority, source=source)

    def mark_task_status(self, task_id: str, status: TaskStatus) -> Task:
        return self.storage.update_task_status(task_id=task_id, status=status)

    def add_updates_as_tasks(self, updates: List[InputUpdate]) -> List[Task]:
        tasks = []
        for update in updates:
            tasks.append(self.storage.create_task(title=update.summary, priority=3, source=update.source))
        return tasks

    def _task_rows(self, tasks: List[Task]) -> List[Dict[str, str]]:
        return [
            {
                "id": task.id,
                "title": task.title,
                "priority": str(task.priority),
                "status": task.status.value,
                "source": task.source,
            }
            for task in tasks
        ]

    def _llm_generate(self, title: str, prompt: str, fallback: str, lang: Language) -> str:
        if self.llm_client is None:
            if settings.llm_enabled and settings.llm_strict and self.llm_init_error:
                logger.error("Strict LLM mode blocked generation: title=%s error=%s", title, self.llm_init_error)
                raise RuntimeError(f"LLM generation failed for {title}: {self.llm_init_error}")
            logger.info("Using fallback generation for title=%s", title)
            return fallback
        system_prompt = (
            "You are the operating system for a solo founder. "
            "Output practical markdown only. Avoid generic filler. "
            "Use concise sections and action items."
        )
        if lang == Language.ZH:
            system_prompt += " Respond in Simplified Chinese."
        else:
            system_prompt += " Respond in English."
        try:
            logger.info("Calling LLM for title=%s lang=%s", title, lang.value)
            return self.llm_client.generate(system_prompt=system_prompt, user_prompt=prompt)
        except Exception as exc:
            logger.exception("LLM call failed for title=%s: %s", title, exc)
            if settings.llm_strict:
                raise RuntimeError(f"LLM generation failed for {title}: {exc}")
            return fallback

    def run_daily_brief(self, updates: List[InputUpdate], lang: Language = Language.ZH) -> AgentResult:
        self.add_updates_as_tasks(updates)
        tasks = self.storage.list_tasks()
        artifact_type, title, fallback_content = self.chief.run(tasks, [item.summary for item in updates], lang=lang)
        prompt = (
            f"Generate a {'Chinese' if lang == Language.ZH else 'English'} daily founder brief in markdown.\n"
            "Must include sections: priorities, progress, risks, next actions.\n"
            f"Today: {date.today().isoformat()}\n"
            f"Tasks JSON:\n{json.dumps(self._task_rows(tasks), ensure_ascii=False, indent=2)}\n"
            f"Updates JSON:\n{json.dumps([u.model_dump(mode='json') for u in updates], ensure_ascii=False, indent=2)}\n"
            "Keep it highly actionable and short."
        )
        content = self._llm_generate(title=title, prompt=prompt, fallback=fallback_content, lang=lang)
        artifact = self.storage.save_artifact(
            artifact_type=artifact_type,
            title=title,
            content=content,
            metadata={"agent": self.chief.name, "lang": lang.value, "llm_enabled": str(settings.llm_enabled)},
        )
        return AgentResult(agent=self.chief.name, artifact=artifact)

    def run_launch_pack(self, updates: List[InputUpdate], lang: Language = Language.ZH) -> AgentResult:
        self.add_updates_as_tasks(updates)
        tasks = self.storage.list_tasks()
        market_notes = self.market.run([item.summary for item in updates], lang=lang)
        support_notes = self.support.run(tasks, lang=lang)
        artifact_type, title, fallback_content = self.launch.run(tasks, market_notes, lang=lang)
        prompt = (
            f"Generate a {'Chinese' if lang == Language.ZH else 'English'} launch pack in markdown.\n"
            "Must include: release notes, launch checklist, risk watchlist, FAQ suggestions, next batch.\n"
            f"Today: {date.today().isoformat()}\n"
            f"Tasks JSON:\n{json.dumps(self._task_rows(tasks), ensure_ascii=False, indent=2)}\n"
            f"Founder updates:\n{json.dumps([u.model_dump(mode='json') for u in updates], ensure_ascii=False, indent=2)}\n"
            f"Market notes:\n{market_notes}\n"
            f"Support notes:\n{support_notes}\n"
            "Output markdown only."
        )
        content = self._llm_generate(
            title=title,
            prompt=prompt,
            fallback=f"{fallback_content}\n\n{support_notes}",
            lang=lang,
        )
        artifact = self.storage.save_artifact(
            artifact_type=artifact_type,
            title=title,
            content=content,
            metadata={"agent": self.launch.name, "lang": lang.value, "llm_enabled": str(settings.llm_enabled)},
        )
        return AgentResult(agent=self.launch.name, artifact=artifact)

    def run_weekly_review(self, lang: Language = Language.ZH) -> AgentResult:
        tasks = self.storage.list_tasks()
        artifacts = self.storage.list_artifacts()
        done = len([task for task in tasks if task.status == TaskStatus.DONE])
        total = len(tasks)
        if lang == Language.EN:
            fallback_content = (
                "# Weekly Review\n\n"
                f"- Total tasks: {total}\n"
                f"- Completed tasks: {done}\n"
                f"- Artifacts generated: {len(artifacts)}\n"
                "- Focus next week: convert one repeated manual task into an automation.\n"
            )
            title = "Weekly Review"
        else:
            fallback_content = (
                "# 周复盘\n\n"
                f"- 总任务数: {total}\n"
                f"- 已完成任务: {done}\n"
                f"- 已产出文档: {len(artifacts)}\n"
                "- 下周重点: 把一个重复手工流程变成自动化。\n"
            )
            title = "周复盘"

        prompt = (
            f"Generate a {'Chinese' if lang == Language.ZH else 'English'} weekly review in markdown.\n"
            "Must include: scorecard, wins, misses, bottlenecks, next-week plan.\n"
            f"Stats: total_tasks={total}, done_tasks={done}, artifacts={len(artifacts)}\n"
            f"Tasks JSON:\n{json.dumps(self._task_rows(tasks), ensure_ascii=False, indent=2)}\n"
            "Keep it concrete and execution-focused."
        )
        content = self._llm_generate(title=title, prompt=prompt, fallback=fallback_content, lang=lang)
        artifact = self.storage.save_artifact(
            artifact_type=ArtifactType.WEEKLY_REVIEW,
            title=title,
            content=content,
            metadata={"agent": "ChiefOfStaff", "lang": lang.value, "llm_enabled": str(settings.llm_enabled)},
        )
        return AgentResult(agent="ChiefOfStaff", artifact=artifact)

    def generate_share_copy(self, artifact: Artifact | None = None, lang: Language = Language.ZH) -> ShareCopy:
        target = artifact or self.storage.get_latest_artifact()
        if target is None:
            if lang == Language.EN:
                return ShareCopy(title="No Artifact Yet", content="Run `daily-brief` first, then share your output.")
            return ShareCopy(title="还没有可分享内容", content="请先运行 `daily-brief` 生成第一份产物。")

        preview = "\n".join(target.content.splitlines()[:8]).strip()
        fallback = (
            (
                "Built with OnePersonCompany\n\n"
                f"I turned daily startup chaos into a reusable artifact today ({target.title}).\n\n"
                f"{preview}\n\n"
                "#buildinpublic #aiagents #solofounder\n"
                "Try: python opc.py demo day0"
            )
            if lang == Language.EN
            else (
                "今天用 OnePersonCompany 产出的成果\n\n"
                f"我把今天创业中的碎片工作，整理成了可执行交付物（{target.title}）。\n\n"
                f"{preview}\n\n"
                "#独立开发 #AI代理 #一人公司\n"
                "体验命令：python opc.py demo day0"
            )
        )

        prompt = (
            f"Write one social post in {'Chinese' if lang == Language.ZH else 'English'} to showcase a solo-founder agent workflow.\n"
            "Need: hook in first sentence, concrete result, 3 hashtags, one CTA command.\n"
            f"Artifact title: {target.title}\n"
            f"Artifact preview:\n{preview}\n"
            "Tone: confident, practical, non-hype."
        )
        content = self._llm_generate(title="share_copy", prompt=prompt, fallback=fallback, lang=lang)
        title = "Built with OnePersonCompany" if lang == Language.EN else "今天用 OnePersonCompany 产出的成果"
        return ShareCopy(title=title, content=content)

    def generate_share_pack(self, artifact: Artifact | None = None, lang: Language = Language.ZH) -> SharePack:
        target = artifact or self.storage.get_latest_artifact()
        if target is None:
            if lang == Language.EN:
                return SharePack(
                    title="Share Pack",
                    x_post="No artifact yet. Run one flow first.\n#buildinpublic #aiagents",
                    moments_post="No artifact yet. Run one flow first.",
                    xiaohongshu_post="No artifact yet. Run one flow first.",
                )
            return SharePack(
                title="分享素材包",
                x_post="还没有可分享成果，先运行一次流程。\n#独立开发 #AI代理",
                moments_post="还没有可分享成果，先运行一次流程。",
                xiaohongshu_post="还没有可分享成果，先运行一次流程。",
            )

        preview = " ".join(target.content.splitlines()[:3]).strip()
        if lang == Language.EN:
            return SharePack(
                title="Share Pack",
                x_post=(
                    f"Just turned founder chaos into a shippable artifact with OnePersonCompany ({target.title}). "
                    f"{preview}\n#buildinpublic #aiagents #solofounder"
                ),
                moments_post=(
                    f"Today's founder update became a clear deliverable: {target.title}. "
                    "Less context switching, more shipping."
                ),
                xiaohongshu_post=(
                    f"Solved my solo-founder workflow with OnePersonCompany.\n"
                    f"- Output: {target.title}\n- Preview: {preview}\n"
                    "Prompt me if you want my setup."
                ),
            )

        return SharePack(
            title="分享素材包",
            x_post=(
                f"我刚把一人创业的碎片工作流，压成了可交付成果（{target.title}）。"
                f"{preview}\n#独立开发 #AI代理 #一人公司"
            ),
            moments_post=(
                f"今天把零散工作整理成了可执行文档：{target.title}。"
                "减少切换，直接推进。"
            ),
            xiaohongshu_post=(
                "一人创业如何不被琐事拖住？\n"
                f"我用 OnePersonCompany 直接产出：{target.title}\n"
                f"预览：{preview}\n"
                "需要的话我可以发你我的模板。"
            ),
        )

    def run_instant_demo(self, lang: Language = Language.ZH) -> Dict[str, object]:
        if lang == Language.EN:
            before = [
                "Switching between issue tracker, notes, and social drafts",
                "Release notes and community post are written repeatedly",
                "Weekly summary depends on memory at midnight",
            ]
            after = [
                "Daily Brief generated in one click",
                "Launch Pack and FAQ draft generated automatically",
                "Share-ready post + PNG card exported in under 30 seconds",
            ]
            sample_output = (
                "# Daily Brief\\n\\n"
                "- Priority: fix onboarding drop-off\\n"
                "- Progress: shipping referral tracking\\n"
                "- Risk: pricing page confusion from 3 users\\n"
                "- Next Action: publish launch note before 6 PM\\n"
            )
            value = "From 20 minutes of context switching to 20 seconds of clear output."
        else:
            before = [
                "在任务系统、文档、社媒草稿间反复切换",
                "每次发版都要重复整理说明和 FAQ",
                "周复盘靠记忆，容易漏掉关键信息",
            ]
            after = [
                "一键生成每日简报，直接进入执行",
                "自动生成发版包和 FAQ 草稿",
                "30 秒导出分享文案和结果卡片",
            ]
            sample_output = (
                "# 每日简报\\n\\n"
                "- 优先级：修复 onboarding 流失\\n"
                "- 进展：邀请返利功能已上线\\n"
                "- 风险：3 位用户反馈定价页不清晰\\n"
                "- 下一步：18:00 前发布发版说明\\n"
            )
            value = "从 20 分钟碎片整理，压缩到 20 秒结构化输出。"

        return {
            "mode": "instant_demo",
            "lang": lang.value,
            "before": before,
            "after": after,
            "value_statement": value,
            "sample_output": sample_output,
        }

    def run_demo_day0(self, lang: Language = Language.ZH) -> Dict[str, str]:
        self.init_seed_tasks()
        if lang == Language.EN:
            updates = [
                InputUpdate(summary="Ship onboarding improvement", source="demo"),
                InputUpdate(summary="Collect top 3 user complaints", source="demo"),
            ]
        else:
            updates = [
                InputUpdate(summary="优化新用户引导流程", source="demo"),
                InputUpdate(summary="整理 3 条高频用户投诉", source="demo"),
            ]
        daily = self.run_daily_brief(updates=updates, lang=lang)
        launch = self.run_launch_pack(updates=updates, lang=lang)
        weekly = self.run_weekly_review(lang=lang)
        share = self.generate_share_copy(artifact=launch.artifact, lang=lang)
        return {
            "daily_brief_id": daily.artifact.id,
            "launch_pack_id": launch.artifact.id,
            "weekly_review_id": weekly.artifact.id,
            "share_title": share.title,
            "share_content": share.content,
            "generated_on": date.today().isoformat(),
        }
