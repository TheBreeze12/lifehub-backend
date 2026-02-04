"""
统计服务
Phase 15: 热量收支统计

提供每日/每周热量统计功能：
- 统计饮食记录的摄入热量
- 统计运动计划的消耗热量
- 计算净热量（摄入-消耗）
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional

from app.db_models.diet_record import DietRecord
from app.db_models.trip_plan import TripPlan
from app.db_models.trip_item import TripItem
from app.models.stats import DailyCalorieStats, WeeklyCalorieStats, DailyBreakdown


class StatsService:
    """统计服务类"""
    
    def get_daily_calorie_stats(
        self, 
        db: Session, 
        user_id: int, 
        target_date: date
    ) -> DailyCalorieStats:
        """
        获取指定日期的热量统计
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            target_date: 目标日期
            
        Returns:
            DailyCalorieStats: 每日热量统计数据
        """
        # 查询饮食记录
        diet_records = db.query(DietRecord).filter(
            and_(
                DietRecord.user_id == user_id,
                DietRecord.record_date == target_date
            )
        ).all()
        
        # 计算摄入热量
        intake_calories = 0.0
        meal_count = len(diet_records)
        meal_breakdown = {
            "breakfast": 0.0,
            "lunch": 0.0,
            "dinner": 0.0,
            "snack": 0.0
        }
        
        for record in diet_records:
            calories = record.calories or 0.0
            intake_calories += calories
            
            # 餐次分类统计
            meal_type = (record.meal_type or "").lower()
            # 支持中文餐次名称转换
            meal_type_map = {
                "早餐": "breakfast",
                "午餐": "lunch",
                "晚餐": "dinner",
                "加餐": "snack"
            }
            if meal_type in meal_type_map:
                meal_type = meal_type_map[meal_type]
            
            if meal_type in meal_breakdown:
                meal_breakdown[meal_type] += calories
        
        # 查询当日运动计划
        trip_plans = db.query(TripPlan).filter(
            and_(
                TripPlan.user_id == user_id,
                TripPlan.start_date <= target_date,
                TripPlan.end_date >= target_date
            )
        ).all()
        
        # 计算消耗热量
        burn_calories = 0.0
        exercise_count = 0
        exercise_duration = 0
        
        for trip in trip_plans:
            # 查询运动项目
            items = db.query(TripItem).filter(
                TripItem.trip_id == trip.id
            ).all()
            
            for item in items:
                # cost 字段现用于存储卡路里消耗
                if item.cost:
                    burn_calories += item.cost
                exercise_count += 1
                if item.duration:
                    exercise_duration += item.duration
        
        # 计算净热量
        net_calories = intake_calories - burn_calories
        
        return DailyCalorieStats(
            date=target_date.isoformat(),
            user_id=user_id,
            intake_calories=round(intake_calories, 2),
            meal_count=meal_count,
            burn_calories=round(burn_calories, 2),
            exercise_count=exercise_count,
            exercise_duration=exercise_duration,
            net_calories=round(net_calories, 2),
            meal_breakdown=meal_breakdown
        )
    
    def get_weekly_calorie_stats(
        self,
        db: Session,
        user_id: int,
        week_start: date
    ) -> WeeklyCalorieStats:
        """
        获取指定周的热量统计
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            week_start: 周起始日期（应为周一）
            
        Returns:
            WeeklyCalorieStats: 每周热量统计数据
        """
        week_end = week_start + timedelta(days=6)
        
        # 初始化统计变量
        total_intake = 0.0
        total_burn = 0.0
        total_meals = 0
        total_exercises = 0
        active_days = 0
        daily_breakdown = []
        
        # 遍历一周中的每一天
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            
            # 获取当日统计
            daily_stats = self.get_daily_calorie_stats(db, user_id, current_date)
            
            # 累加总计
            total_intake += daily_stats.intake_calories
            total_burn += daily_stats.burn_calories
            total_meals += daily_stats.meal_count
            total_exercises += daily_stats.exercise_count
            
            # 判断是否有记录
            if daily_stats.meal_count > 0 or daily_stats.exercise_count > 0:
                active_days += 1
            
            # 添加每日明细
            daily_breakdown.append(DailyBreakdown(
                date=current_date.isoformat(),
                intake_calories=daily_stats.intake_calories,
                burn_calories=daily_stats.burn_calories,
                net_calories=daily_stats.net_calories
            ))
        
        # 计算平均值（避免除零）
        days_for_avg = active_days if active_days > 0 else 1
        avg_intake = total_intake / days_for_avg
        avg_burn = total_burn / days_for_avg
        avg_net = (total_intake - total_burn) / days_for_avg
        
        return WeeklyCalorieStats(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            user_id=user_id,
            total_intake=round(total_intake, 2),
            total_burn=round(total_burn, 2),
            total_net=round(total_intake - total_burn, 2),
            avg_intake=round(avg_intake, 2),
            avg_burn=round(avg_burn, 2),
            avg_net=round(avg_net, 2),
            total_meals=total_meals,
            total_exercises=total_exercises,
            active_days=active_days,
            daily_breakdown=daily_breakdown
        )


# 创建单例实例
stats_service = StatsService()
