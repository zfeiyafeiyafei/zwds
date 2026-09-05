"""四域 ORM 模型建表与完整链路插入/查询测试（内存 SQLite）。"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from ziwei_engine.models import (
    AIReport,
    AnalysisResult,
    AnalysisRule,
    Base,
    CalendarRule,
    Chart,
    ChartPalace,
    ChartPeriod,
    ChartShensha,
    ChartSnapshot,
    ChartStar,
    PalaceDefinition,
    PatternDefinition,
    PeriodRule,
    Person,
    PromptTemplate,
    RulePackage,
    School,
    ShenshaDefinition,
    SihuaRule,
    Star,
    StarAttribute,
    StarPositionRule,
    StarStatusDefinition,
    SyncRecord,
    User,
)

EXPECTED_TABLES = {
    # A. 规则引擎
    "school",
    "rule_package",
    "calendar_rule",
    "star_position_rule",
    "sihua_rule",
    "period_rule",
    "analysis_rule",
    # B. 知识库
    "star",
    "star_attribute",
    "palace_definition",
    "star_status_definition",
    "shensha_definition",
    "pattern_definition",
    # C. 用户命盘
    "users",
    "person",
    "chart",
    "chart_palace",
    "chart_star",
    "chart_shensha",
    "chart_period",
    # D. AI 与同步
    "prompt_template",
    "analysis_result",
    "ai_config",
    "ai_report",
    "chart_snapshot",
    "sync_record",
}


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_all_tables_created(session):
    assert EXPECTED_TABLES == set(Base.metadata.tables)


def test_full_chain_insert_and_query(session):
    # A. 规则引擎域
    school = School(name="三合派", code="sanhe", description="传统三合派", version="1.0")
    session.add(school)
    session.flush()
    package = RulePackage(
        school_id=school.id, name="三合派传统版", version="1.0", status="active"
    )
    session.add(package)
    session.flush()

    calendar_rule = CalendarRule(
        rule_package_id=package.id,
        rule_type="zi_shi",
        condition_json={"late_zi": True},
        result_json={"day_switch": "next"},
        priority=10,
    )
    sihua_rule = SihuaRule(
        rule_package_id=package.id,
        heavenly_stem="甲",
        hua_type="化禄",
        direction="向心",
    )
    period_rule = PeriodRule(
        rule_package_id=package.id,
        period_type="大限",
        condition_json={"direction": "阳男顺行"},
        result_json={"step": 1},
    )
    analysis_rule = AnalysisRule(
        rule_package_id=package.id,
        rule_type="pattern",
        condition_json={"stars": ["紫微", "天府"]},
        result_json={"pattern": "紫府朝垣"},
        priority=5,
    )
    session.add_all([calendar_rule, sihua_rule, period_rule, analysis_rule])

    # B. 知识库域
    star = Star(
        name="紫微", code="ziwei", category="主星", level="甲级", description="帝星"
    )
    session.add(star)
    session.flush()
    star_attr = StarAttribute(
        star_id=star.id, attribute_type="五行", attribute_value="土"
    )
    palace_def = PalaceDefinition(name="命宫", sequence=1, description="本命之宫")
    status_def = StarStatusDefinition(name="庙", description="星曜最亮")
    shensha_def = ShenshaDefinition(type="岁前星", name="岁建", description="岁前十二星")
    pattern_def = PatternDefinition(name="紫府朝垣", category="吉格")
    session.add_all([star_attr, palace_def, status_def, shensha_def, pattern_def])
    session.flush()

    star_position_rule = StarPositionRule(
        rule_package_id=package.id,
        star_id=star.id,
        rule_type="安紫微",
        condition_json={"lunar_day": "*"},
        result_json={"method": "五行局"},
        priority=1,
    )
    session.add(star_position_rule)

    # C. 用户命盘域
    user = User(username="tester", email="t@example.com", password_hash="x" * 64)
    session.add(user)
    session.flush()
    person = Person(
        user_id=user.id, name="张三", gender="男", birthday=datetime(1990, 5, 15, 6, 30)
    )
    session.add(person)
    session.flush()
    chart = Chart(
        person_id=person.id,
        rule_package_id=package.id,
        engine_version="0.1.0",
        solar_datetime=datetime(1990, 5, 15, 6, 30),
        lunar_datetime="庚午年四月廿一卯时",
        longitude=116.4,
        timezone="+08:00",
        gender="男",
        body_master="天同",
        life_master="贪狼",
        body_palace="福德宫",
        origin_palace="命宫",
    )
    session.add(chart)
    session.flush()
    chart_palace = ChartPalace(
        chart_id=chart.id,
        palace_definition_id=palace_def.id,
        heavenly_stem="丙",
        earth_branch="子",
        position=1,
    )
    session.add(chart_palace)
    session.flush()
    chart_star = ChartStar(
        chart_id=chart.id,
        chart_palace_id=chart_palace.id,
        star_id=star.id,
        category="主星",
        status_id=status_def.id,
        birth_hua="化科",
        self_hua_json={"type": "化禄", "direction": "离心"},
    )
    chart_shensha = ChartShensha(
        chart_id=chart.id,
        chart_palace_id=chart_palace.id,
        type="岁前星",
        name="岁建",
    )
    chart_period = ChartPeriod(
        chart_id=chart.id,
        period_type="大限",
        age_start=26,
        age_end=35,
        year=2016,
        chart_palace_id=chart_palace.id,
    )
    session.add_all([chart_star, chart_shensha, chart_period])

    # D. AI 与同步域
    snapshot = ChartSnapshot(
        chart_id=chart.id,
        json_content={"chart": {"palaces": 12}},
        engine_version="0.1.0",
    )
    prompt = PromptTemplate(
        name="综合分析",
        category="综合",
        template_content="请分析 {chart}",
        variables=["chart"],
    )
    session.add_all([snapshot, prompt])
    session.flush()
    analysis = AnalysisResult(
        chart_id=chart.id,
        analysis_type="pattern",
        rule_package_id=package.id,
        content_json={"patterns": ["紫府朝垣"]},
    )
    report = AIReport(
        chart_id=chart.id,
        prompt_id=prompt.id,
        model_name="kimi-k3",
        content="命主紫微坐命……",
    )
    sync = SyncRecord(
        object_type="chart",
        object_id=chart.id,
        local_version=1,
        cloud_version=0,
        status="pending",
    )
    session.add_all([analysis, report, sync])
    session.commit()

    # ---- 查询与关联断言 ----
    loaded_chart = session.get(Chart, chart.id)
    assert loaded_chart is not None
    assert loaded_chart.person.user.username == "tester"
    assert loaded_chart.person.name == "张三"
    assert loaded_chart.rule_package.name == "三合派传统版"
    assert loaded_chart.rule_package.school.code == "sanhe"
    assert loaded_chart.body_master == "天同"
    assert loaded_chart.created_time is not None

    palace = session.get(ChartPalace, chart_palace.id)
    assert palace.chart is loaded_chart
    assert palace.palace_definition.name == "命宫"
    assert palace.heavenly_stem == "丙" and palace.earth_branch == "子"

    star_row = session.get(ChartStar, chart_star.id)
    assert star_row.star.name == "紫微"
    assert star_row.status.name == "庙"
    assert star_row.chart_palace is palace
    assert star_row.self_hua_json == {"type": "化禄", "direction": "离心"}
    assert star_row.birth_hua == "化科"

    assert session.get(ChartShensha, chart_shensha.id).chart_palace is palace
    period = session.get(ChartPeriod, chart_period.id)
    assert period.chart_palace is palace and period.age_start == 26

    snap = session.get(ChartSnapshot, snapshot.id)
    assert snap.chart is loaded_chart
    assert snap.json_content["chart"]["palaces"] == 12

    result = session.get(AnalysisResult, analysis.id)
    assert result.chart is loaded_chart
    assert result.rule_package.name == "三合派传统版"

    rep = session.get(AIReport, report.id)
    assert rep.chart is loaded_chart
    assert rep.prompt_template.name == "综合分析"

    rec = session.get(SyncRecord, sync.id)
    assert rec.object_id == chart.id and rec.updated_time is not None

    # 规则域关联
    loaded_pkg = session.get(RulePackage, package.id)
    assert loaded_pkg.calendar_rules[0].priority == 10
    assert loaded_pkg.sihua_rules[0].hua_type == "化禄"
    assert loaded_pkg.period_rules[0].period_type == "大限"
    assert loaded_pkg.analysis_rules[0].result_json == {"pattern": "紫府朝垣"}
    assert loaded_pkg.star_position_rules[0].star.name == "紫微"

    loaded_star = session.get(Star, star.id)
    assert loaded_star.attributes[0].attribute_value == "土"

    # select 风格查询
    stmt = select(ChartStar).where(ChartStar.chart_id == chart.id)
    rows = session.scalars(stmt).all()
    assert len(rows) == 1 and rows[0].star.name == "紫微"


def test_unique_constraints(session):
    session.add(Star(name="天府", code="tianfu", category="主星"))
    session.commit()
    session.add(Star(name="天府", code="tianfu2", category="主星"))
    with pytest.raises(Exception):
        session.flush()
    session.rollback()

    session.add(User(username="u1", email="u1@example.com", password_hash="h"))
    session.commit()
    session.add(User(username="u1", email="u2@example.com", password_hash="h"))
    with pytest.raises(Exception):
        session.flush()
    session.rollback()
