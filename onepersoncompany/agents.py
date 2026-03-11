from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Iterable, List, Tuple

from .models import ArtifactType, Language, Task, TaskStatus


class ChiefOfStaffAgent:
    name = "ChiefOfStaff"

    def run(self, tasks: List[Task], updates: Iterable[str], lang: Language) -> Tuple[ArtifactType, str, str]:
        top_tasks = sorted(tasks, key=lambda t: (t.priority, t.title))[:5]
        bullets = "\n".join([f"- [P{item.priority}] {item.title} ({item.status})" for item in top_tasks])
        if lang == Language.EN:
            notes = "\n".join([f"- {line}" for line in updates]) or "- No manual updates yet"
            content = (
                f"# Daily Brief - {date.today().isoformat()}\n\n"
                "## Top Priorities\n"
                f"{bullets or '- No tasks in queue'}\n\n"
                "## Founder Notes\n"
                f"{notes}\n\n"
                "## Suggested Next Action\n"
                "- Clear one high-priority blocker before noon.\n"
            )
            return ArtifactType.DAILY_BRIEF, "Daily Brief", content

        notes = "\n".join([f"- {line}" for line in updates]) or "- 今日还没有手动更新"
        content = (
            f"# 每日简报 - {date.today().isoformat()}\n\n"
            "## 今日优先事项\n"
            f"{bullets or '- 当前任务队列为空'}\n\n"
            "## 创始人更新\n"
            f"{notes}\n\n"
            "## 下一步建议\n"
            "- 上午优先清理 1 个高优先级阻塞项。\n"
        )
        return ArtifactType.DAILY_BRIEF, "每日简报", content


class MarketResearcherAgent:
    name = "MarketResearcher"

    def run(self, updates: Iterable[str], lang: Language) -> str:
        word_counter = Counter()
        for line in updates:
            for word in line.lower().split():
                if len(word) >= 4:
                    word_counter[word.strip(',.!?')] += 1
        top_words = word_counter.most_common(5)
        if lang == Language.EN:
            lines = [f"- {word}: {count}" for word, count in top_words] or ["- No trend signals yet"]
            trend_lines = "\n".join(lines)
            return (
                "## Market Signals\n"
                "Top recurring terms from latest founder notes:\n"
                f"{trend_lines}\n"
            )

        lines = [f"- {word}: {count}" for word, count in top_words] or ["- 暂无明显趋势信号"]
        trend_lines = "\n".join(lines)
        return (
            "## 市场信号\n"
            "最近更新里出现频率最高的关键词：\n"
            f"{trend_lines}\n"
        )


class LaunchManagerAgent:
    name = "LaunchManager"

    def run(self, tasks: List[Task], market_notes: str, lang: Language) -> Tuple[ArtifactType, str, str]:
        completed = [t for t in tasks if t.status == TaskStatus.DONE]
        in_progress = [t for t in tasks if t.status != TaskStatus.DONE]

        if lang == Language.EN:
            completed_lines = "\n".join([f"- {item.title}" for item in completed]) or "- No completed items yet"
            next_lines = "\n".join([f"- {item.title}" for item in in_progress[:5]]) or "- No pending items"

            content = (
                f"# Launch Pack - {date.today().isoformat()}\n\n"
                "## Release Notes\n"
                f"{completed_lines}\n\n"
                "## Launch Checklist\n"
                "- [ ] Confirm metrics dashboard\n"
                "- [ ] Validate pricing and onboarding flow\n"
                "- [ ] Post changelog to community\n"
                "- [ ] Queue customer follow-up\n\n"
                "## Next Batch\n"
                f"{next_lines}\n\n"
                f"{market_notes}"
            )
            return ArtifactType.LAUNCH_PACK, "Launch Pack", content

        completed_lines = "\n".join([f"- {item.title}" for item in completed]) or "- 暂无已完成任务"
        next_lines = "\n".join([f"- {item.title}" for item in in_progress[:5]]) or "- 当前无待办任务"
        content = (
            f"# 发版包 - {date.today().isoformat()}\n\n"
            "## 发版说明\n"
            f"{completed_lines}\n\n"
            "## 发布检查清单\n"
            "- [ ] 确认核心指标看板正常\n"
            "- [ ] 检查定价页与引导流程\n"
            "- [ ] 发布更新日志到社区\n"
            "- [ ] 安排重点用户回访\n\n"
            "## 下一批执行项\n"
            f"{next_lines}\n\n"
            f"{market_notes}"
        )
        return ArtifactType.LAUNCH_PACK, "发版包", content


class SupportResponderAgent:
    name = "SupportResponder"

    def run(self, tasks: List[Task], lang: Language) -> str:
        unresolved = [task for task in tasks if task.status != TaskStatus.DONE]
        if lang == Language.EN:
            suggestions = "\n".join([f"- FAQ candidate: {task.title}" for task in unresolved[:3]])
            return (
                "## Support Suggestions\n"
                "Draft response style: concise, accountable, timeline-based.\n"
                f"{suggestions or '- No open support topics'}\n"
            )
        suggestions = "\n".join([f"- FAQ 候选: {task.title}" for task in unresolved[:3]])
        return (
            "## 客服建议\n"
            "建议回复风格：简洁、负责、给出明确时间点。\n"
            f"{suggestions or '- 当前无未解决客服议题'}\n"
        )
