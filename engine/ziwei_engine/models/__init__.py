"""紫微斗数平台 ORM 模型统一入口。

四大领域：
  A. 规则引擎 rule_engine:  School / RulePackage / CalendarRule /
     StarPositionRule / SihuaRule / PeriodRule / AnalysisRule
  B. 知识库   knowledge:    Star / StarAttribute / PalaceDefinition /
     StarStatusDefinition / ShenshaDefinition / PatternDefinition
  C. 用户命盘 chart:        User / Person / Chart / ChartPalace / ChartStar /
     ChartShensha / ChartPeriod
  D. AI 与同步 ai:          PromptTemplate / AnalysisResult / AIReport /
     ChartSnapshot / SyncRecord
"""

from .base import Base, TimestampMixin
from .rule_engine import (
    AnalysisRule,
    CalendarRule,
    PeriodRule,
    RulePackage,
    School,
    SihuaRule,
    StarPositionRule,
)
from .knowledge import (
    PalaceDefinition,
    PatternDefinition,
    ShenshaDefinition,
    Star,
    StarAttribute,
    StarStatusDefinition,
)
from .chart import (
    Chart,
    ChartPalace,
    ChartPeriod,
    ChartShensha,
    ChartStar,
    Person,
    User,
)
from .ai import (
    AIReport,
    AnalysisResult,
    ChartSnapshot,
    PromptTemplate,
    SyncRecord,
)

__all__ = [
    "Base",
    "TimestampMixin",
    # A. 规则引擎
    "School",
    "RulePackage",
    "CalendarRule",
    "StarPositionRule",
    "SihuaRule",
    "PeriodRule",
    "AnalysisRule",
    # B. 知识库
    "Star",
    "StarAttribute",
    "PalaceDefinition",
    "StarStatusDefinition",
    "ShenshaDefinition",
    "PatternDefinition",
    # C. 用户命盘
    "User",
    "Person",
    "Chart",
    "ChartPalace",
    "ChartStar",
    "ChartShensha",
    "ChartPeriod",
    # D. AI 与同步
    "PromptTemplate",
    "AnalysisResult",
    "AIReport",
    "ChartSnapshot",
    "SyncRecord",
]
