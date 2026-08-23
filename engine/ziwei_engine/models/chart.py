"""C. 用户命盘域（User Chart）：用户、人物、命盘及其实例数据。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .knowledge import PalaceDefinition, Star, StarStatusDefinition
from .rule_engine import RulePackage


class User(Base):
    """系统账号。

    注意：PostgreSQL 中 user 为保留字，表名使用 users，
    以保持 SQLite/PostgreSQL 双端可迁移。
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    persons: Mapped[list["Person"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Person(Base, TimestampMixin):
    """排盘对象：一个用户可有多个（自己、孩子、配偶、客户……）。"""

    __tablename__ = "person"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(8))
    birthday: Mapped[Optional[datetime]] = mapped_column(DateTime)
    remark: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="persons")
    charts: Mapped[list["Chart"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )


class Chart(Base, TimestampMixin):
    """命盘主表。"""

    __tablename__ = "chart"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("person.id"), nullable=False, index=True
    )
    rule_package_id: Mapped[int] = mapped_column(
        ForeignKey("rule_package.id"), nullable=False, index=True
    )
    engine_version: Mapped[Optional[str]] = mapped_column(String(32))
    solar_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    lunar_datetime: Mapped[Optional[str]] = mapped_column(String(64))
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    timezone: Mapped[Optional[str]] = mapped_column(String(32))
    gender: Mapped[Optional[str]] = mapped_column(String(8))
    body_master: Mapped[Optional[str]] = mapped_column(String(16))
    life_master: Mapped[Optional[str]] = mapped_column(String(16))
    body_palace: Mapped[Optional[str]] = mapped_column(String(16))
    origin_palace: Mapped[Optional[str]] = mapped_column(String(16))

    person: Mapped[Person] = relationship(back_populates="charts")
    rule_package: Mapped[RulePackage] = relationship()
    palaces: Mapped[list["ChartPalace"]] = relationship(
        back_populates="chart", cascade="all, delete-orphan"
    )
    stars: Mapped[list["ChartStar"]] = relationship(
        back_populates="chart", cascade="all, delete-orphan"
    )
    shenshas: Mapped[list["ChartShensha"]] = relationship(
        back_populates="chart", cascade="all, delete-orphan"
    )
    periods: Mapped[list["ChartPeriod"]] = relationship(
        back_populates="chart", cascade="all, delete-orphan"
    )


class ChartPalace(Base, TimestampMixin):
    """命盘十二宫实例。"""

    __tablename__ = "chart_palace"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chart_id: Mapped[int] = mapped_column(
        ForeignKey("chart.id"), nullable=False, index=True
    )
    palace_definition_id: Mapped[int] = mapped_column(
        ForeignKey("palace_definition.id"), nullable=False, index=True
    )
    heavenly_stem: Mapped[Optional[str]] = mapped_column(String(4))
    earth_branch: Mapped[Optional[str]] = mapped_column(String(4))
    position: Mapped[Optional[int]] = mapped_column(Integer)

    chart: Mapped[Chart] = relationship(back_populates="palaces")
    palace_definition: Mapped[PalaceDefinition] = relationship()
    stars: Mapped[list["ChartStar"]] = relationship(back_populates="chart_palace")
    shenshas: Mapped[list["ChartShensha"]] = relationship(
        back_populates="chart_palace"
    )
    periods: Mapped[list["ChartPeriod"]] = relationship(back_populates="chart_palace")


class ChartStar(Base, TimestampMixin):
    """星曜落宫：某命盘某宫中的星曜及其状态、四化。"""

    __tablename__ = "chart_star"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chart_id: Mapped[int] = mapped_column(
        ForeignKey("chart.id"), nullable=False, index=True
    )
    chart_palace_id: Mapped[int] = mapped_column(
        ForeignKey("chart_palace.id"), nullable=False, index=True
    )
    star_id: Mapped[int] = mapped_column(
        ForeignKey("star.id"), nullable=False, index=True
    )
    category: Mapped[Optional[str]] = mapped_column(String(16))
    status_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("star_status_definition.id"), index=True
    )
    birth_hua: Mapped[Optional[str]] = mapped_column(String(16))
    self_hua_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)

    chart: Mapped[Chart] = relationship(back_populates="stars")
    chart_palace: Mapped[ChartPalace] = relationship(back_populates="stars")
    star: Mapped[Star] = relationship()
    status: Mapped[Optional[StarStatusDefinition]] = relationship()


class ChartShensha(Base, TimestampMixin):
    """命盘中的神煞实例。"""

    __tablename__ = "chart_shensha"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chart_id: Mapped[int] = mapped_column(
        ForeignKey("chart.id"), nullable=False, index=True
    )
    chart_palace_id: Mapped[int] = mapped_column(
        ForeignKey("chart_palace.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(32), nullable=False)

    chart: Mapped[Chart] = relationship(back_populates="shenshas")
    chart_palace: Mapped[ChartPalace] = relationship(back_populates="shenshas")


class ChartPeriod(Base, TimestampMixin):
    """大限 / 流年 / 小限。"""

    __tablename__ = "chart_period"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chart_id: Mapped[int] = mapped_column(
        ForeignKey("chart.id"), nullable=False, index=True
    )
    period_type: Mapped[str] = mapped_column(String(16), nullable=False)
    age_start: Mapped[Optional[int]] = mapped_column(Integer)
    age_end: Mapped[Optional[int]] = mapped_column(Integer)
    year: Mapped[Optional[int]] = mapped_column(Integer)
    chart_palace_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("chart_palace.id"), index=True
    )

    chart: Mapped[Chart] = relationship(back_populates="periods")
    chart_palace: Mapped[Optional[ChartPalace]] = relationship(
        back_populates="periods"
    )
