"""A. 规则引擎域（Rule Engine）：流派、规则包与各类规则。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class School(Base, TimestampMixin):
    """流派（三合派、飞星派、钦天派……）。"""

    __tablename__ = "school"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    version: Mapped[Optional[str]] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)

    rule_packages: Mapped[list["RulePackage"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )


class RulePackage(Base, TimestampMixin):
    """规则包：一个流派 + 一套规则版本。"""

    __tablename__ = "rule_package"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    school_id: Mapped[int] = mapped_column(
        ForeignKey("school.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[Optional[str]] = mapped_column(String(32))
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)

    school: Mapped[School] = relationship(back_populates="rule_packages")
    calendar_rules: Mapped[list["CalendarRule"]] = relationship(
        back_populates="rule_package", cascade="all, delete-orphan"
    )
    star_position_rules: Mapped[list["StarPositionRule"]] = relationship(
        back_populates="rule_package", cascade="all, delete-orphan"
    )
    sihua_rules: Mapped[list["SihuaRule"]] = relationship(
        back_populates="rule_package", cascade="all, delete-orphan"
    )
    period_rules: Mapped[list["PeriodRule"]] = relationship(
        back_populates="rule_package", cascade="all, delete-orphan"
    )
    analysis_rules: Mapped[list["AnalysisRule"]] = relationship(
        back_populates="rule_package", cascade="all, delete-orphan"
    )


class CalendarRule(Base, TimestampMixin):
    """历法规则：农历转换、节气、四柱、子时跨日。"""

    __tablename__ = "calendar_rule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_package_id: Mapped[int] = mapped_column(
        ForeignKey("rule_package.id"), nullable=False, index=True
    )
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    condition_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    result_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rule_package: Mapped[RulePackage] = relationship(back_populates="calendar_rules")


class StarPositionRule(Base, TimestampMixin):
    """安星规则：紫微/天府/辅星/小星定位。"""

    __tablename__ = "star_position_rule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_package_id: Mapped[int] = mapped_column(
        ForeignKey("rule_package.id"), nullable=False, index=True
    )
    star_id: Mapped[Optional[int]] = mapped_column(ForeignKey("star.id"), index=True)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    condition_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    result_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rule_package: Mapped[RulePackage] = relationship(
        back_populates="star_position_rules"
    )
    star: Mapped[Optional["Star"]] = relationship()


class SihuaRule(Base, TimestampMixin):
    """四化规则：生年四化、飞化、自化。"""

    __tablename__ = "sihua_rule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_package_id: Mapped[int] = mapped_column(
        ForeignKey("rule_package.id"), nullable=False, index=True
    )
    heavenly_stem: Mapped[str] = mapped_column(String(4), nullable=False)
    star_id: Mapped[Optional[int]] = mapped_column(ForeignKey("star.id"), index=True)
    hua_type: Mapped[str] = mapped_column(String(16), nullable=False)
    direction: Mapped[Optional[str]] = mapped_column(String(16))

    rule_package: Mapped[RulePackage] = relationship(back_populates="sihua_rules")
    star: Mapped[Optional["Star"]] = relationship()


class PeriodRule(Base, TimestampMixin):
    """时间周期规则：大限、流年、小限。"""

    __tablename__ = "period_rule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_package_id: Mapped[int] = mapped_column(
        ForeignKey("rule_package.id"), nullable=False, index=True
    )
    period_type: Mapped[str] = mapped_column(String(16), nullable=False)
    condition_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    result_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rule_package: Mapped[RulePackage] = relationship(back_populates="period_rules")


class AnalysisRule(Base, TimestampMixin):
    """分析规则：格局判断、星曜组合、宫位分析。"""

    __tablename__ = "analysis_rule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_package_id: Mapped[int] = mapped_column(
        ForeignKey("rule_package.id"), nullable=False, index=True
    )
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    condition_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    result_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rule_package: Mapped[RulePackage] = relationship(back_populates="analysis_rules")


from .knowledge import Star  # noqa: E402  （解决循环引用：star 外键）
