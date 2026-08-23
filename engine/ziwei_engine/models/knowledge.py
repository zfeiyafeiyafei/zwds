"""B. 知识库域（Knowledge Base）：星曜、宫位、神煞、格局定义。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Star(Base, TimestampMixin):
    """星曜基础表（主星、辅星、小星、煞星）。"""

    __tablename__ = "star"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(16))
    description: Mapped[Optional[str]] = mapped_column(Text)

    attributes: Mapped[list["StarAttribute"]] = relationship(
        back_populates="star", cascade="all, delete-orphan"
    )


class StarAttribute(Base, TimestampMixin):
    """星曜属性：五行、阴阳、象义、性格关键词。"""

    __tablename__ = "star_attribute"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    star_id: Mapped[int] = mapped_column(
        ForeignKey("star.id"), nullable=False, index=True
    )
    attribute_type: Mapped[str] = mapped_column(String(32), nullable=False)
    attribute_value: Mapped[str] = mapped_column(String(128), nullable=False)

    star: Mapped[Star] = relationship(back_populates="attributes")


class PalaceDefinition(Base, TimestampMixin):
    """十二宫定义（命宫、兄弟宫……）。"""

    __tablename__ = "palace_definition"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)


class StarStatusDefinition(Base, TimestampMixin):
    """星曜状态定义（庙、旺、得、利、平、陷）。"""

    __tablename__ = "star_status_definition"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)


class ShenshaDefinition(Base, TimestampMixin):
    """神煞定义（岁前星、将前星、十二长生、太岁煞禄）。"""

    __tablename__ = "shensha_definition"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)


class PatternDefinition(Base, TimestampMixin):
    """格局定义（紫府朝垣、杀破狼、机月同梁……）。"""

    __tablename__ = "pattern_definition"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(32))
    description: Mapped[Optional[str]] = mapped_column(Text)
