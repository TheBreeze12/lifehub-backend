"""
统计相关API路由
Phase 15: 热量收支统计
Phase 16: 营养素摄入统计
Phase 26: 饮食-运动数据联动
Phase 36: 健康目标达成率
Phase 51: 运动频率分析

提供每日/每周热量统计接口：
- GET /api/stats/calories/daily - 每日热量统计（含运动记录联动、热量缺口、达成率）
- GET /api/stats/calories/weekly - 每周热量统计
- GET /api/stats/nutrients/daily - 每日营养素统计（Phase 16）
- GET /api/stats/goal-progress - 健康目标达成率（Phase 36）
- GET /api/stats/exercise-frequency - 运动频率分析（Phase 51）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import stats_service
from app.models.stats import (
    DailyCalorieStatsResponse,
    WeeklyCalorieStatsResponse,
    DailyNutrientStatsResponse,
    DailyNutrientStats,
    GoalProgressResponse,
    GoalProgressData,
    ExerciseFrequencyResponse,
    ExerciseFrequencyData,
)

router = APIRouter(prefix="/api/stats", tags=["数据统计"])


parse_date = stats_service.parse_date


@router.get("/calories/daily", response_model=DailyCalorieStatsResponse)
async def get_daily_calorie_stats(
    userId: int = Query(..., description="用户ID", gt=0),
    date: str = Query(..., description="统计日期（YYYY-MM-DD格式）"),
    db: Session = Depends(get_db)
):
    """
    获取每日热量统计（Phase 26增强）

    统计指定用户在指定日期的热量摄入和消耗情况：
    - **intake_calories**: 摄入热量（来自饮食记录）
    - **burn_calories**: 有效消耗热量（有运动记录时用实际值，否则用计划值）
    - **planned_burn_calories**: 计划消耗热量（来自运动计划）
    - **actual_burn_calories**: 实际消耗热量（来自运动记录）
    - **net_calories**: 净热量（摄入-有效消耗）
    - **calorie_deficit**: 热量缺口（摄入-有效消耗）
    - **goal_achievement_rate**: 目标达成率（实际消耗/计划消耗×100）
    - **meal_count**: 餐次数量
    - **exercise_count**: 运动计划项目数量
    - **actual_exercise_count**: 实际运动记录数量
    - **meal_breakdown**: 餐次分类统计（早餐/午餐/晚餐/加餐）

    Args:
        userId: 用户ID
        date: 统计日期（YYYY-MM-DD格式）

    Returns:
        DailyCalorieStatsResponse: 每日热量统计响应
    """
    return stats_service.get_daily_calorie_stats(db, userId, date)


@router.get("/calories/weekly", response_model=WeeklyCalorieStatsResponse)
async def get_weekly_calorie_stats(
    userId: int = Query(..., description="用户ID", gt=0),
    week_start: str = Query(..., description="周起始日期（YYYY-MM-DD格式，应为周一）"),
    db: Session = Depends(get_db)
):
    """
    获取每周热量统计

    统计指定用户在指定周的热量摄入和消耗情况：
    - **total_intake**: 周总摄入热量
    - **total_burn**: 周总消耗热量
    - **total_net**: 周净热量
    - **avg_intake**: 日均摄入热量
    - **avg_burn**: 日均消耗热量
    - **avg_net**: 日均净热量
    - **daily_breakdown**: 每日明细（7天）
    - **active_days**: 有记录的天数

    Args:
        userId: 用户ID
        week_start: 周起始日期（YYYY-MM-DD格式）

    Returns:
        WeeklyCalorieStatsResponse: 每周热量统计响应
    """
    return stats_service.get_weekly_calorie_stats(db, userId, week_start)


@router.get("/health")
async def stats_health_check():
    """统计服务健康检查"""
    return {
        "status": "ok",
        "service": "calorie-stats"
    }


# ============== Phase 16: 营养素统计接口 ==============

@router.get("/nutrients/daily", response_model=DailyNutrientStatsResponse)
async def get_daily_nutrient_stats(
    userId: int = Query(..., description="用户ID", gt=0),
    date: str = Query(..., description="统计日期（YYYY-MM-DD格式）"),
    db: Session = Depends(get_db)
):
    """
    获取每日营养素统计（Phase 16）

    统计指定用户在指定日期的营养素摄入情况：
    - **total_protein**: 蛋白质总量（g）
    - **total_fat**: 脂肪总量（g）
    - **total_carbs**: 碳水化合物总量（g）
    - **total_calories**: 总热量（kcal）
    - **protein_ratio**: 蛋白质热量占比（%）
    - **fat_ratio**: 脂肪热量占比（%）
    - **carbs_ratio**: 碳水化合物热量占比（%）
    - **guidelines_comparison**: 与《中国居民膳食指南2022》对比结果

    膳食指南建议占比：
    - 蛋白质: 10-15%
    - 脂肪: 20-30%
    - 碳水化合物: 50-65%

    Args:
        userId: 用户ID
        date: 统计日期（YYYY-MM-DD格式）

    Returns:
        DailyNutrientStatsResponse: 每日营养素统计响应
    """
    return stats_service.get_daily_nutrient_stats(db, userId, date)


# ============== Phase 36: 健康目标达成率接口 ==============

@router.get("/goal-progress", response_model=GoalProgressResponse)
async def get_goal_progress(
    userId: int = Query(..., description="用户ID", gt=0),
    days: int = Query(7, description="统计天数（默认7天）", ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    获取健康目标达成率（Phase 36）

    根据用户设置的健康目标，统计指定天数内的饮食和运动数据，
    计算各维度达成率和综合得分。

    支持的健康目标类型：
    - **reduce_fat（减脂）**: 评估热量控制、脂肪比例、运动消耗
    - **gain_muscle（增肌）**: 评估蛋白质摄入、热量充足、运动消耗
    - **control_sugar（控糖）**: 评估碳水比例、热量控制、运动辅助
    - **balanced（均衡）**: 评估营养均衡、运动规律、饮食规律

    返回数据包含：
    - **overall_score**: 综合得分（0-100）
    - **overall_status**: 综合状态（excellent/good/fair/poor）
    - **dimensions**: 各维度详细评分
    - **suggestions**: 个性化建议
    - **streak_days**: 连续记录天数

    Args:
        userId: 用户ID
        days: 统计天数（1-90，默认7）

    Returns:
        GoalProgressResponse: 健康目标达成率响应
    """
    return stats_service.get_goal_progress(db, userId, days)


# ============== Phase 51: 运动频率分析接口 ==============

@router.get("/exercise-frequency", response_model=ExerciseFrequencyResponse)
async def get_exercise_frequency(
    user_id: int = Query(..., alias="user_id", description="用户ID", gt=0),
    period: str = Query("week", description="统计周期：week=最近一周，month=最近一个月"),
    db: Session = Depends(get_db)
):
    """
    获取运动频率分析（Phase 51）

    统计指定周期内的运动频率、类型分布，并给出评级和建议。

    返回数据包含：
    - **total_days**: 统计总天数
    - **active_days**: 有运动记录的天数
    - **total_exercise_count**: 总运动次数
    - **total_duration**: 总运动时长（分钟）
    - **total_calories**: 总消耗热量（kcal）
    - **avg_frequency**: 平均每周运动次数
    - **avg_duration_per_session**: 平均每次运动时长（分钟）
    - **avg_calories_per_session**: 平均每次消耗热量（kcal）
    - **daily_data**: 每日运动频率明细
    - **type_distribution**: 运动类型分布
    - **frequency_rating**: 运动频率评级（excellent/good/fair/insufficient）
    - **frequency_suggestion**: 运动频率建议

    Args:
        user_id: 用户ID
        period: 统计周期（week/month，默认week）

    Returns:
        ExerciseFrequencyResponse: 运动频率分析响应
    """
    return stats_service.get_exercise_frequency(db, user_id, period)
