"""D. AI 与同步域：Prompt 模板、分析结果、AI 报告、快照、同步记录。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .chart import Chart
from .rule_engine import RulePackage


class PromptTemplate(Base, TimestampMixin):
    """提示词模板（综合分析、婚姻分析、职业分析……）。"""

    __tablename__ = "prompt_template"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(32))
    template_content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[list[str]]] = mapped_column(JSON)
    # 内置 skill：不可删除/改名（biz_requirement.md §4.4.1）
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    reports: Mapped[list["AIReport"]] = relationship(back_populates="prompt_template")


class AnalysisResult(Base, TimestampMixin):
    """规则/分析引擎输出的分析结果。"""

    __tablename__ = "analysis_result"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chart_id: Mapped[int] = mapped_column(
        ForeignKey("chart.id"), nullable=False, index=True
    )
    analysis_type: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_package_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("rule_package.id"), index=True
    )
    content_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)

    chart: Mapped[Chart] = relationship()
    rule_package: Mapped[Optional[RulePackage]] = relationship()


class AIReport(Base, TimestampMixin):
    """最终 AI 报告。"""

    __tablename__ = "ai_report"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chart_id: Mapped[int] = mapped_column(
        ForeignKey("chart.id"), nullable=False, index=True
    )
    prompt_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("prompt_template.id"), index=True
    )
    model_name: Mapped[Optional[str]] = mapped_column(String(64))
    content: Mapped[Optional[str]] = mapped_column(Text)

    chart: Mapped[Chart] = relationship()
    prompt_template: Mapped[Optional[PromptTemplate]] = relationship(
        back_populates="reports"
    )


class ChartSnapshot(Base, TimestampMixin):
    """命盘 JSON 快照：导出、分享、AI 输入、数据备份。"""

    __tablename__ = "chart_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chart_id: Mapped[int] = mapped_column(
        ForeignKey("chart.id"), nullable=False, index=True
    )
    json_content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    engine_version: Mapped[Optional[str]] = mapped_column(String(32))

    chart: Mapped[Chart] = relationship()


class SyncRecord(Base):
    """SQLite ↔ PostgreSQL 同步记录。"""

    __tablename__ = "sync_record"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    object_id: Mapped[int] = mapped_column(Integer, nullable=False)
    local_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cloud_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    updated_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class AIConfig(Base):
    """LLM API 配置（单行，id 恒为 1；biz_requirement.md §4.4.1）。"""

    __tablename__ = "ai_config"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    base_url: Mapped[str] = mapped_column(
        String(255), default="https://api.openai.com/v1", nullable=False
    )
    api_key: Mapped[Optional[str]] = mapped_column(String(255))
    model: Mapped[str] = mapped_column(String(64), default="gpt-4o-mini", nullable=False)


class AIMessage(Base, TimestampMixin):
    """AI 对话消息：按命盘（chart_key）分线程持久化（biz_requirement.md §4.4.3）。

    chart_key = "solar_date|hour_index|gender"，与命盘是否落库无关。
    """

    __tablename__ = "ai_message"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chart_key: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    skill_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("prompt_template.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user / assistant
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
