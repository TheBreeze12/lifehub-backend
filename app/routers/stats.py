"""
统计相关API路由
Phase 15: 热量收支统计
Phase 16: 营养素摄入统计

提供每日/每周热量统计接口：
- GET /api/stats/calories/daily - 每日热量统计
- GET /api/stats/calories/weekly - 每周热量统计
- GET /api/stats/nutrients/daily - 每日营养素统计（Phase 16）
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, datetime

from app.database import get_db
from app.services.stats_service import stats_service
from app.models.stats import (
    DailyCalorieStatsResponse,
    WeeklyCalorieStatsResponse,
    DailyNutrientStatsResponse,
    DailyNutrientStats
)
from app.db_models.user import User

router = APIRouter(prefix="/api/stats", tags=["数据统计"])


def parse_date(date_str: str) -> date:
    """
    解析日期字符串
    
    Args:
        date_str: 日期字符串（YYYY-MM-DD格式）
        
    Returns:
        date: 日期对象
        
    Raises:
        HTTPException: 日期格式错误时抛出400错误
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"日期格式错误，请使用 YYYY-MM-DD 格式，收到: {date_str}"
        )


@router.get("/calories/daily", response_model=DailyCalorieStatsResponse)
async def get_daily_calorie_stats(
    userId: int = Query(..., description="用户ID", gt=0),
    date: str = Query(..., description="统计日期（YYYY-MM-DD格式）"),
    db: Session = Depends(get_db)
):
    """
    获取每日热量统计
    
    统计指定用户在指定日期的热量摄入和消耗情况：
    - **intake_calories**: 摄入热量（来自饮食记录）
    - **burn_calories**: 消耗热量（来自运动计划）
    - **net_calories**: 净热量（摄入-消耗）
    - **meal_count**: 餐次数量
    - **exercise_count**: 运动项目数量
    - **meal_breakdown**: 餐次分类统计（早餐/午餐/晚餐/加餐）
    
    Args:
        userId: 用户ID
        date: 统计日期（YYYY-MM-DD格式）
        
    Returns:
        DailyCalorieStatsResponse: 每日热量统计响应
    """
    # 解析日期
    target_date = parse_date(date)
    
    # 验证用户是否存在（可选，取决于业务需求）
    user = db.query(User).filter(User.id == userId).first()
    if not user:
        # 返回空统计而非404，便于前端处理
        from app.models.stats import DailyCalorieStats
        empty_stats = DailyCalorieStats(
            date=date,
            user_id=userId,
            intake_calories=0.0,
            meal_count=0,
            burn_calories=0.0,
            exercise_count=0,
            exercise_duration=0,
            net_calories=0.0,
            meal_breakdown=None
        )
        return DailyCalorieStatsResponse(
            code=200,
            message="获取成功（用户无记录）",
            data=empty_stats
        )
    
    # 获取统计数据
    stats = stats_service.get_daily_calorie_stats(db, userId, target_date)
    
    return DailyCalorieStatsResponse(
        code=200,
        message="获取成功",
        data=stats
    )


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
    # 解析日期
    start_date = parse_date(week_start)
    
    # 验证用户是否存在（可选）
    user = db.query(User).filter(User.id == userId).first()
    if not user:
        # 返回空统计
        from app.models.stats import WeeklyCalorieStats, DailyBreakdown
        from datetime import timedelta
        
        week_end = start_date + timedelta(days=6)
        empty_breakdown = [
            DailyBreakdown(
                date=(start_date + timedelta(days=i)).isoformat(),
                intake_calories=0.0,
                burn_calories=0.0,
                net_calories=0.0
            )
            for i in range(7)
        ]
        
        empty_stats = WeeklyCalorieStats(
            week_start=week_start,
            week_end=week_end.isoformat(),
            user_id=userId,
            total_intake=0.0,
            total_burn=0.0,
            total_net=0.0,
            avg_intake=0.0,
            avg_burn=0.0,
            avg_net=0.0,
            total_meals=0,
            total_exercises=0,
            active_days=0,
            daily_breakdown=empty_breakdown
        )
        return WeeklyCalorieStatsResponse(
            code=200,
            message="获取成功（用户无记录）",
            data=empty_stats
        )
    
    # 获取统计数据
    stats = stats_service.get_weekly_calorie_stats(db, userId, start_date)
    
    return WeeklyCalorieStatsResponse(
        code=200,
        message="获取成功",
        data=stats
    )


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
    # 解析日期
    target_date = parse_date(date)
    
    # 验证用户是否存在
    user = db.query(User).filter(User.id == userId).first()
    if not user:
        # 返回空统计而非404，便于前端处理
        from app.models.stats import (
            GuidelinesComparison, NutrientComparison, DIETARY_GUIDELINES
        )
        empty_comparison = GuidelinesComparison(
            protein=NutrientComparison(
                actual_ratio=0.0,
                recommended_min=DIETARY_GUIDELINES["protein"]["min"],
                recommended_max=DIETARY_GUIDELINES["protein"]["max"],
                status="low",
                message="暂无数据"
            ),
            fat=NutrientComparison(
                actual_ratio=0.0,
                recommended_min=DIETARY_GUIDELINES["fat"]["min"],
                recommended_max=DIETARY_GUIDELINES["fat"]["max"],
                status="low",
                message="暂无数据"
            ),
            carbs=NutrientComparison(
                actual_ratio=0.0,
                recommended_min=DIETARY_GUIDELINES["carbs"]["min"],
                recommended_max=DIETARY_GUIDELINES["carbs"]["max"],
                status="low",
                message="暂无数据"
            )
        )
        empty_stats = DailyNutrientStats(
            date=date,
            user_id=userId,
            total_protein=0.0,
            total_fat=0.0,
            total_carbs=0.0,
            total_calories=0.0,
            protein_calories=0.0,
            fat_calories=0.0,
            carbs_calories=0.0,
            protein_ratio=0.0,
            fat_ratio=0.0,
            carbs_ratio=0.0,
            meal_count=0,
            meal_breakdown=None,
            guidelines_comparison=empty_comparison
        )
        return DailyNutrientStatsResponse(
            code=200,
            message="获取成功（用户无记录）",
            data=empty_stats
        )
    
    # 获取统计数据
    stats = stats_service.get_daily_nutrient_stats(db, userId, target_date)
    
    return DailyNutrientStatsResponse(
        code=200,
        message="获取成功",
        data=stats
    )
