"""
统计服务
Phase 15: 热量收支统计
Phase 16: 营养素摄入统计
Phase 26: 饮食-运动数据联动
Phase 36: 健康目标达成率
Phase 51: 运动频率分析

提供每日/每周热量统计功能：
- 统计饮食记录的摄入热量
- 统计运动计划的计划消耗热量
- 统计运动记录的实际消耗热量（Phase 26新增）
- 计算净热量（摄入-有效消耗）
- 计算实际热量缺口和目标达成率（Phase 26新增）
- 统计营养素（蛋白质、脂肪、碳水）摄入比例
- 与膳食指南建议值对比
- 根据用户健康目标计算多维度达成率（Phase 36新增）
- 统计运动频率、类型分布、评级与建议（Phase 51新增）
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional, List

from app.db_models.diet_record import DietRecord
from app.db_models.trip_plan import TripPlan
from app.db_models.trip_item import TripItem
from app.db_models.exercise_record import ExerciseRecord
from app.db_models.user import User
from app.models.stats import (
    DailyCalorieStats, WeeklyCalorieStats, DailyBreakdown,
    DailyNutrientStats, NutrientComparison, GuidelinesComparison,
    DIETARY_GUIDELINES, PROTEIN_KCAL_PER_GRAM, FAT_KCAL_PER_GRAM, CARBS_KCAL_PER_GRAM,
    GoalProgressData, GoalDimension, HEALTH_GOAL_LABELS,
    ExerciseFrequencyData, DailyExerciseFrequency, ExerciseTypeDistribution,
    EXERCISE_TYPE_LABELS
)


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
        
        # 查询当日运动计划（计划消耗）
        trip_plans = db.query(TripPlan).filter(
            and_(
                TripPlan.user_id == user_id,
                TripPlan.start_date <= target_date,
                TripPlan.end_date >= target_date
            )
        ).all()
        
        # 计算计划消耗热量
        planned_burn_calories = 0.0
        exercise_count = 0
        exercise_duration = 0
        
        for trip in trip_plans:
            items = db.query(TripItem).filter(
                TripItem.trip_id == trip.id
            ).all()
            
            for item in items:
                if item.cost:
                    planned_burn_calories += item.cost
                exercise_count += 1
                if item.duration:
                    exercise_duration += item.duration
        
        # Phase 26: 查询当日运动记录（实际消耗）
        exercise_records = db.query(ExerciseRecord).filter(
            and_(
                ExerciseRecord.user_id == user_id,
                ExerciseRecord.exercise_date == target_date
            )
        ).all()
        
        actual_burn_calories = 0.0
        actual_exercise_count = len(exercise_records)
        actual_exercise_duration = 0
        
        for record in exercise_records:
            actual_burn_calories += record.actual_calories or 0.0
            actual_exercise_duration += record.actual_duration or 0
        
        # 有效消耗：有运动记录时用实际值，否则用计划值
        if actual_exercise_count > 0:
            burn_calories = actual_burn_calories
        else:
            burn_calories = planned_burn_calories
        
        # 计算净热量和热量缺口
        net_calories = intake_calories - burn_calories
        calorie_deficit = net_calories  # 正值=热量盈余，负值=热量亏缺
        
        # 计算目标达成率
        goal_achievement_rate = None
        if planned_burn_calories > 0:
            goal_achievement_rate = round(
                (actual_burn_calories / planned_burn_calories) * 100, 1
            )
        
        return DailyCalorieStats(
            date=target_date.isoformat(),
            user_id=user_id,
            intake_calories=round(intake_calories, 2),
            meal_count=meal_count,
            burn_calories=round(burn_calories, 2),
            exercise_count=exercise_count,
            exercise_duration=exercise_duration,
            planned_burn_calories=round(planned_burn_calories, 2),
            actual_burn_calories=round(actual_burn_calories, 2),
            actual_exercise_count=actual_exercise_count,
            actual_exercise_duration=actual_exercise_duration,
            net_calories=round(net_calories, 2),
            calorie_deficit=round(calorie_deficit, 2),
            goal_achievement_rate=goal_achievement_rate,
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


    # ============== Phase 16: 营养素统计方法 ==============
    
    def _create_nutrient_comparison(
        self, 
        nutrient_key: str, 
        actual_ratio: float
    ) -> NutrientComparison:
        """
        创建营养素与膳食指南对比结果
        
        Args:
            nutrient_key: 营养素键名（protein/fat/carbs）
            actual_ratio: 实际占比（%）
            
        Returns:
            NutrientComparison: 对比结果
        """
        guideline = DIETARY_GUIDELINES[nutrient_key]
        min_val = guideline["min"]
        max_val = guideline["max"]
        name = guideline["name"]
        
        # 判断状态
        if actual_ratio < min_val:
            status = "low"
            message = f"{name}摄入偏低，建议适当增加{name}摄入"
        elif actual_ratio > max_val:
            status = "high"
            message = f"{name}摄入偏高，建议控制{name}摄入"
        else:
            status = "normal"
            message = f"{name}摄入在建议范围内"
        
        return NutrientComparison(
            actual_ratio=round(actual_ratio, 1),
            recommended_min=min_val,
            recommended_max=max_val,
            status=status,
            message=message
        )
    
    def get_daily_nutrient_stats(
        self,
        db: Session,
        user_id: int,
        target_date: date
    ) -> DailyNutrientStats:
        """
        获取指定日期的营养素统计
        
        统计蛋白质、脂肪、碳水化合物的摄入量和占比，
        并与《中国居民膳食指南2022》建议值对比。
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            target_date: 目标日期
            
        Returns:
            DailyNutrientStats: 每日营养素统计数据
        """
        # 查询饮食记录
        diet_records = db.query(DietRecord).filter(
            and_(
                DietRecord.user_id == user_id,
                DietRecord.record_date == target_date
            )
        ).all()
        
        # 初始化统计变量
        total_protein = 0.0
        total_fat = 0.0
        total_carbs = 0.0
        total_calories = 0.0
        meal_count = len(diet_records)
        
        # 餐次分类统计
        meal_breakdown = {
            "breakfast": {"protein": 0.0, "fat": 0.0, "carbs": 0.0, "calories": 0.0},
            "lunch": {"protein": 0.0, "fat": 0.0, "carbs": 0.0, "calories": 0.0},
            "dinner": {"protein": 0.0, "fat": 0.0, "carbs": 0.0, "calories": 0.0},
            "snack": {"protein": 0.0, "fat": 0.0, "carbs": 0.0, "calories": 0.0}
        }
        
        # 餐次名称映射
        meal_type_map = {
            "早餐": "breakfast",
            "午餐": "lunch",
            "晚餐": "dinner",
            "加餐": "snack"
        }
        
        # 遍历记录，累加营养素
        for record in diet_records:
            protein = record.protein or 0.0
            fat = record.fat or 0.0
            carbs = record.carbs or 0.0
            calories = record.calories or 0.0
            
            total_protein += protein
            total_fat += fat
            total_carbs += carbs
            total_calories += calories
            
            # 餐次分类
            meal_type = (record.meal_type or "").lower()
            if meal_type in meal_type_map:
                meal_type = meal_type_map[meal_type]
            
            if meal_type in meal_breakdown:
                meal_breakdown[meal_type]["protein"] += protein
                meal_breakdown[meal_type]["fat"] += fat
                meal_breakdown[meal_type]["carbs"] += carbs
                meal_breakdown[meal_type]["calories"] += calories
        
        # 计算各营养素提供的热量
        protein_calories = total_protein * PROTEIN_KCAL_PER_GRAM
        fat_calories = total_fat * FAT_KCAL_PER_GRAM
        carbs_calories = total_carbs * CARBS_KCAL_PER_GRAM
        
        # 计算营养素热量总和（用于计算占比）
        total_nutrient_calories = protein_calories + fat_calories + carbs_calories
        
        # 计算营养素占比
        if total_nutrient_calories > 0:
            protein_ratio = (protein_calories / total_nutrient_calories) * 100
            fat_ratio = (fat_calories / total_nutrient_calories) * 100
            carbs_ratio = (carbs_calories / total_nutrient_calories) * 100
        else:
            protein_ratio = 0.0
            fat_ratio = 0.0
            carbs_ratio = 0.0
        
        # 创建膳食指南对比
        if total_nutrient_calories > 0:
            guidelines_comparison = GuidelinesComparison(
                protein=self._create_nutrient_comparison("protein", protein_ratio),
                fat=self._create_nutrient_comparison("fat", fat_ratio),
                carbs=self._create_nutrient_comparison("carbs", carbs_ratio)
            )
        else:
            # 无数据时也返回对比结构，但状态为low
            guidelines_comparison = GuidelinesComparison(
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
        
        # 清理meal_breakdown中的空餐次
        cleaned_meal_breakdown = {
            k: v for k, v in meal_breakdown.items()
            if v["calories"] > 0
        }
        
        return DailyNutrientStats(
            date=target_date.isoformat(),
            user_id=user_id,
            total_protein=round(total_protein, 2),
            total_fat=round(total_fat, 2),
            total_carbs=round(total_carbs, 2),
            total_calories=round(total_calories, 2),
            protein_calories=round(protein_calories, 2),
            fat_calories=round(fat_calories, 2),
            carbs_calories=round(carbs_calories, 2),
            protein_ratio=round(protein_ratio, 1),
            fat_ratio=round(fat_ratio, 1),
            carbs_ratio=round(carbs_ratio, 1),
            meal_count=meal_count,
            meal_breakdown=cleaned_meal_breakdown if cleaned_meal_breakdown else None,
            guidelines_comparison=guidelines_comparison
        )


    # ============== Phase 36: 健康目标达成率方法 ==============

    @staticmethod
    def _score_to_status(score: float) -> str:
        """将分数转换为状态标签"""
        if score >= 85:
            return "excellent"
        elif score >= 65:
            return "good"
        elif score >= 40:
            return "fair"
        else:
            return "poor"

    @staticmethod
    def _clamp_score(score: float) -> float:
        """将分数限制在0-100范围内"""
        return round(max(0.0, min(100.0, score)), 1)

    def _calc_streak_days(
        self, db: Session, user_id: int, end_date: date
    ) -> int:
        """
        计算从end_date往前的连续记录天数。
        只要某天有饮食记录或运动记录就算有记录。
        """
        streak = 0
        current = end_date
        while True:
            has_diet = db.query(DietRecord).filter(
                and_(
                    DietRecord.user_id == user_id,
                    DietRecord.record_date == current
                )
            ).first() is not None

            has_exercise = db.query(ExerciseRecord).filter(
                and_(
                    ExerciseRecord.user_id == user_id,
                    ExerciseRecord.exercise_date == current
                )
            ).first() is not None

            if has_diet or has_exercise:
                streak += 1
                current -= timedelta(days=1)
            else:
                break
        return streak

    def _gather_period_data(
        self, db: Session, user_id: int, start_date: date, end_date: date
    ) -> dict:
        """
        收集统计周期内的汇总数据。
        返回字典包含各种累计值和日均值。
        """
        total_days = (end_date - start_date).days + 1
        days_with_diet = 0
        days_with_exercise = 0

        sum_calories = 0.0
        sum_protein = 0.0
        sum_fat = 0.0
        sum_carbs = 0.0
        sum_burn = 0.0
        sum_exercise_duration = 0
        sum_planned_burn = 0.0

        for i in range(total_days):
            d = start_date + timedelta(days=i)

            # 饮食
            diet_records = db.query(DietRecord).filter(
                and_(DietRecord.user_id == user_id, DietRecord.record_date == d)
            ).all()
            if diet_records:
                days_with_diet += 1
            for r in diet_records:
                sum_calories += r.calories or 0.0
                sum_protein += r.protein or 0.0
                sum_fat += r.fat or 0.0
                sum_carbs += r.carbs or 0.0

            # 运动记录（实际）
            ex_records = db.query(ExerciseRecord).filter(
                and_(ExerciseRecord.user_id == user_id, ExerciseRecord.exercise_date == d)
            ).all()
            if ex_records:
                days_with_exercise += 1
            for er in ex_records:
                sum_burn += er.actual_calories or 0.0
                sum_exercise_duration += er.actual_duration or 0

            # 运动计划（计划消耗）
            plans = db.query(TripPlan).filter(
                and_(
                    TripPlan.user_id == user_id,
                    TripPlan.start_date <= d,
                    TripPlan.end_date >= d
                )
            ).all()
            for p in plans:
                items = db.query(TripItem).filter(TripItem.trip_id == p.id).all()
                for item in items:
                    sum_planned_burn += item.cost or 0.0

        active_days = max(days_with_diet, days_with_exercise)
        divisor = active_days if active_days > 0 else 1

        # 营养素热量占比
        protein_cal = sum_protein * PROTEIN_KCAL_PER_GRAM
        fat_cal = sum_fat * FAT_KCAL_PER_GRAM
        carbs_cal = sum_carbs * CARBS_KCAL_PER_GRAM
        nutrient_cal_total = protein_cal + fat_cal + carbs_cal

        if nutrient_cal_total > 0:
            protein_ratio = (protein_cal / nutrient_cal_total) * 100
            fat_ratio = (fat_cal / nutrient_cal_total) * 100
            carbs_ratio = (carbs_cal / nutrient_cal_total) * 100
        else:
            protein_ratio = 0.0
            fat_ratio = 0.0
            carbs_ratio = 0.0

        return {
            "total_days": total_days,
            "active_days": active_days,
            "days_with_diet": days_with_diet,
            "days_with_exercise": days_with_exercise,
            "sum_calories": sum_calories,
            "sum_protein": sum_protein,
            "sum_fat": sum_fat,
            "sum_carbs": sum_carbs,
            "sum_burn": sum_burn,
            "sum_exercise_duration": sum_exercise_duration,
            "sum_planned_burn": sum_planned_burn,
            "avg_calories": sum_calories / divisor,
            "avg_protein": sum_protein / divisor,
            "avg_burn": sum_burn / divisor,
            "avg_exercise_duration": sum_exercise_duration / divisor,
            "protein_ratio": protein_ratio,
            "fat_ratio": fat_ratio,
            "carbs_ratio": carbs_ratio,
        }

    def _evaluate_reduce_fat(self, data: dict, user: User) -> tuple:
        """减脂目标评估，返回 (dimensions, suggestions)"""
        dims: List[GoalDimension] = []
        suggestions: List[str] = []

        # 基础代谢估算（Mifflin-St Jeor）
        weight = user.weight or 70.0
        height = user.height or 170.0
        age = user.age or 30
        if (user.gender or "male") == "male":
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        target_intake = bmr * 1.2  # 轻度活动TDEE
        # 减脂建议热量 = TDEE - 500
        target_deficit_intake = target_intake - 500

        # 维度1: 热量控制
        avg_cal = data["avg_calories"]
        if avg_cal <= 0:
            cal_score = 50.0
            cal_desc = "暂无饮食数据"
        else:
            # 越接近 target_deficit_intake 得分越高
            ratio = avg_cal / target_deficit_intake if target_deficit_intake > 0 else 1.0
            if ratio <= 1.0:
                cal_score = min(100.0, 60 + 40 * ratio)
            else:
                cal_score = max(0.0, 100 - (ratio - 1.0) * 150)
            cal_desc = f"日均摄入{avg_cal:.0f}kcal，建议{target_deficit_intake:.0f}kcal"
        dims.append(GoalDimension(
            name="热量控制", score=self._clamp_score(cal_score),
            status=self._score_to_status(cal_score),
            current_value=round(avg_cal, 1),
            target_value=round(target_deficit_intake, 1),
            unit="kcal/天", description=cal_desc
        ))
        if avg_cal > target_deficit_intake * 1.1 and avg_cal > 0:
            suggestions.append("建议降低每日热量摄入，保持适度热量缺口以促进减脂")

        # 维度2: 脂肪比例
        fat_r = data["fat_ratio"]
        fat_target_max = DIETARY_GUIDELINES["fat"]["max"]
        if data["sum_calories"] <= 0:
            fat_score = 50.0
            fat_desc = "暂无营养数据"
        elif fat_r <= fat_target_max:
            fat_score = 80 + (fat_target_max - fat_r)
            fat_desc = f"脂肪占比{fat_r:.1f}%，在建议范围内"
        else:
            fat_score = max(0, 80 - (fat_r - fat_target_max) * 5)
            fat_desc = f"脂肪占比{fat_r:.1f}%，超出建议上限{fat_target_max}%"
            suggestions.append("脂肪摄入比例偏高，建议减少油炸和高脂食物")
        dims.append(GoalDimension(
            name="脂肪比例", score=self._clamp_score(fat_score),
            status=self._score_to_status(fat_score),
            current_value=round(fat_r, 1),
            target_value=float(fat_target_max),
            unit="%", description=fat_desc
        ))

        # 维度3: 运动消耗
        avg_burn = data["avg_burn"]
        target_burn = 300.0  # 减脂建议日均消耗
        if avg_burn <= 0:
            burn_score = 20.0
            burn_desc = "暂无运动记录"
            suggestions.append("建议每日进行至少30分钟有氧运动以促进减脂")
        else:
            burn_ratio = avg_burn / target_burn
            burn_score = min(100.0, burn_ratio * 100)
            burn_desc = f"日均运动消耗{avg_burn:.0f}kcal，建议{target_burn:.0f}kcal"
            if avg_burn < target_burn * 0.7:
                suggestions.append("运动消耗不足，建议增加有氧运动频率和时长")
        dims.append(GoalDimension(
            name="运动消耗", score=self._clamp_score(burn_score),
            status=self._score_to_status(burn_score),
            current_value=round(avg_burn, 1),
            target_value=target_burn,
            unit="kcal/天", description=burn_desc
        ))

        return dims, suggestions

    def _evaluate_gain_muscle(self, data: dict, user: User) -> tuple:
        """增肌目标评估"""
        dims: List[GoalDimension] = []
        suggestions: List[str] = []

        weight = user.weight or 70.0

        # 维度1: 蛋白质摄入（增肌建议1.6-2.2g/kg体重）
        avg_protein = data["avg_protein"]
        target_protein = weight * 1.8  # 中间值
        if avg_protein <= 0:
            prot_score = 20.0
            prot_desc = "暂无蛋白质摄入数据"
            suggestions.append("增肌需要充足蛋白质，建议每日摄入1.6-2.2g/kg体重")
        else:
            prot_ratio = avg_protein / target_protein
            if prot_ratio >= 1.0:
                prot_score = min(100.0, 85 + (prot_ratio - 1.0) * 30)
            else:
                prot_score = max(0.0, prot_ratio * 85)
            prot_desc = f"日均蛋白质{avg_protein:.1f}g，建议{target_protein:.0f}g"
            if prot_ratio < 0.8:
                suggestions.append(f"蛋白质摄入不足，建议增加至每日{target_protein:.0f}g以上")
        dims.append(GoalDimension(
            name="蛋白质摄入", score=self._clamp_score(prot_score),
            status=self._score_to_status(prot_score),
            current_value=round(avg_protein, 1),
            target_value=round(target_protein, 1),
            unit="g/天", description=prot_desc
        ))

        # 维度2: 热量充足（增肌需要热量盈余）
        avg_cal = data["avg_calories"]
        height = user.height or 170.0
        age = user.age or 25
        if (user.gender or "male") == "male":
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        target_intake = bmr * 1.4 + 300  # TDEE + 盈余
        if avg_cal <= 0:
            cal_score = 30.0
            cal_desc = "暂无热量数据"
        else:
            ratio = avg_cal / target_intake
            if ratio >= 0.9:
                cal_score = min(100.0, 70 + ratio * 30)
            else:
                cal_score = max(0.0, ratio * 80)
            cal_desc = f"日均摄入{avg_cal:.0f}kcal，增肌建议{target_intake:.0f}kcal"
            if ratio < 0.85:
                suggestions.append("热量摄入不足以支撑增肌，建议适当增加热量摄入")
        dims.append(GoalDimension(
            name="热量充足", score=self._clamp_score(cal_score),
            status=self._score_to_status(cal_score),
            current_value=round(avg_cal, 1),
            target_value=round(target_intake, 1),
            unit="kcal/天", description=cal_desc
        ))

        # 维度3: 运动消耗（力量训练）
        avg_burn = data["avg_burn"]
        target_burn = 400.0
        if avg_burn <= 0:
            burn_score = 20.0
            burn_desc = "暂无运动记录"
            suggestions.append("增肌需要规律的力量训练，建议每周至少3次")
        else:
            burn_ratio = avg_burn / target_burn
            burn_score = min(100.0, burn_ratio * 100)
            burn_desc = f"日均运动消耗{avg_burn:.0f}kcal，建议{target_burn:.0f}kcal"
        dims.append(GoalDimension(
            name="运动消耗", score=self._clamp_score(burn_score),
            status=self._score_to_status(burn_score),
            current_value=round(avg_burn, 1),
            target_value=target_burn,
            unit="kcal/天", description=burn_desc
        ))

        return dims, suggestions

    def _evaluate_control_sugar(self, data: dict, user: User) -> tuple:
        """控糖目标评估"""
        dims: List[GoalDimension] = []
        suggestions: List[str] = []

        # 维度1: 碳水比例（控糖目标希望碳水比例偏低，建议<=50%）
        carbs_r = data["carbs_ratio"]
        target_carbs_max = 50.0  # 控糖目标建议碳水不超过50%
        if data["sum_calories"] <= 0:
            carbs_score = 50.0
            carbs_desc = "暂无营养数据"
        elif carbs_r <= target_carbs_max:
            carbs_score = 80 + (target_carbs_max - carbs_r)
            carbs_desc = f"碳水占比{carbs_r:.1f}%，控制良好"
        else:
            carbs_score = max(0, 80 - (carbs_r - target_carbs_max) * 4)
            carbs_desc = f"碳水占比{carbs_r:.1f}%，建议控制在{target_carbs_max}%以下"
            suggestions.append("碳水化合物比例偏高，建议减少精制碳水和甜食摄入")
        dims.append(GoalDimension(
            name="碳水比例", score=self._clamp_score(carbs_score),
            status=self._score_to_status(carbs_score),
            current_value=round(carbs_r, 1),
            target_value=target_carbs_max,
            unit="%", description=carbs_desc
        ))

        # 维度2: 热量控制
        weight = user.weight or 70.0
        height = user.height or 170.0
        age = user.age or 30
        if (user.gender or "male") == "male":
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        target_intake = bmr * 1.3
        avg_cal = data["avg_calories"]
        if avg_cal <= 0:
            cal_score = 50.0
            cal_desc = "暂无热量数据"
        else:
            ratio = avg_cal / target_intake if target_intake > 0 else 1.0
            if 0.85 <= ratio <= 1.1:
                cal_score = 90.0
            elif ratio < 0.85:
                cal_score = max(40, 90 - (0.85 - ratio) * 200)
            else:
                cal_score = max(0, 90 - (ratio - 1.1) * 150)
            cal_desc = f"日均摄入{avg_cal:.0f}kcal，建议{target_intake:.0f}kcal"
            if ratio > 1.2:
                suggestions.append("热量摄入偏高，建议适当控制总热量")
        dims.append(GoalDimension(
            name="热量控制", score=self._clamp_score(cal_score),
            status=self._score_to_status(cal_score),
            current_value=round(avg_cal, 1),
            target_value=round(target_intake, 1),
            unit="kcal/天", description=cal_desc
        ))

        # 维度3: 运动辅助
        avg_burn = data["avg_burn"]
        target_burn = 250.0
        if avg_burn <= 0:
            burn_score = 30.0
            burn_desc = "暂无运动记录"
            suggestions.append("适当运动有助于控糖，建议每日进行中等强度运动")
        else:
            burn_ratio = avg_burn / target_burn
            burn_score = min(100.0, burn_ratio * 100)
            burn_desc = f"日均运动消耗{avg_burn:.0f}kcal，建议{target_burn:.0f}kcal"
        dims.append(GoalDimension(
            name="运动辅助", score=self._clamp_score(burn_score),
            status=self._score_to_status(burn_score),
            current_value=round(avg_burn, 1),
            target_value=target_burn,
            unit="kcal/天", description=burn_desc
        ))

        return dims, suggestions

    def _evaluate_balanced(self, data: dict, user: User) -> tuple:
        """均衡目标评估"""
        dims: List[GoalDimension] = []
        suggestions: List[str] = []

        # 维度1: 营养均衡（三大营养素是否在膳食指南范围内）
        prot_r = data["protein_ratio"]
        fat_r = data["fat_ratio"]
        carbs_r = data["carbs_ratio"]

        if data["sum_calories"] <= 0:
            balance_score = 50.0
            balance_desc = "暂无营养数据"
        else:
            score_parts = []
            for nutrient, ratio in [("protein", prot_r), ("fat", fat_r), ("carbs", carbs_r)]:
                g = DIETARY_GUIDELINES[nutrient]
                mid = (g["min"] + g["max"]) / 2
                half_range = (g["max"] - g["min"]) / 2
                if g["min"] <= ratio <= g["max"]:
                    # 在范围内，越接近中点越好
                    dist = abs(ratio - mid) / half_range
                    score_parts.append(85 + (1 - dist) * 15)
                else:
                    # 超出范围
                    if ratio < g["min"]:
                        deviation = g["min"] - ratio
                    else:
                        deviation = ratio - g["max"]
                    score_parts.append(max(0, 80 - deviation * 5))

            balance_score = sum(score_parts) / len(score_parts)
            in_range_count = sum(1 for n, r in [("protein", prot_r), ("fat", fat_r), ("carbs", carbs_r)]
                                 if DIETARY_GUIDELINES[n]["min"] <= r <= DIETARY_GUIDELINES[n]["max"])
            balance_desc = f"三大营养素{in_range_count}/3项在推荐范围内"

            if prot_r < DIETARY_GUIDELINES["protein"]["min"]:
                suggestions.append("蛋白质摄入偏低，建议增加优质蛋白来源")
            if fat_r > DIETARY_GUIDELINES["fat"]["max"]:
                suggestions.append("脂肪摄入偏高，建议减少油脂摄入")
            if carbs_r > DIETARY_GUIDELINES["carbs"]["max"]:
                suggestions.append("碳水化合物摄入偏高，建议适当控制主食量")

        dims.append(GoalDimension(
            name="营养均衡", score=self._clamp_score(balance_score),
            status=self._score_to_status(balance_score),
            current_value=round(data.get("sum_calories", 0) / max(data["active_days"], 1), 1),
            target_value=100.0,
            unit="分", description=balance_desc
        ))

        # 维度2: 运动规律
        exercise_ratio = data["days_with_exercise"] / max(data["total_days"], 1)
        target_exercise_ratio = 0.7  # 建议70%的天数有运动
        if data["days_with_exercise"] == 0:
            ex_score = 20.0
            ex_desc = "暂无运动记录"
            suggestions.append("建议保持规律运动习惯，每周至少运动5天")
        else:
            ex_score = min(100.0, (exercise_ratio / target_exercise_ratio) * 100)
            ex_desc = f"过去{data['total_days']}天中{data['days_with_exercise']}天有运动记录"
            if exercise_ratio < 0.5:
                suggestions.append("运动频率偏低，建议增加运动天数")
        dims.append(GoalDimension(
            name="运动规律", score=self._clamp_score(ex_score),
            status=self._score_to_status(ex_score),
            current_value=round(exercise_ratio * 100, 1),
            target_value=round(target_exercise_ratio * 100, 1),
            unit="%", description=ex_desc
        ))

        # 维度3: 饮食规律
        diet_ratio = data["days_with_diet"] / max(data["total_days"], 1)
        target_diet_ratio = 0.85
        if data["days_with_diet"] == 0:
            diet_score = 20.0
            diet_desc = "暂无饮食记录"
            suggestions.append("建议坚持记录每日饮食，有助于管理健康")
        else:
            diet_score = min(100.0, (diet_ratio / target_diet_ratio) * 100)
            diet_desc = f"过去{data['total_days']}天中{data['days_with_diet']}天有饮食记录"
        dims.append(GoalDimension(
            name="饮食规律", score=self._clamp_score(diet_score),
            status=self._score_to_status(diet_score),
            current_value=round(diet_ratio * 100, 1),
            target_value=round(target_diet_ratio * 100, 1),
            unit="%", description=diet_desc
        ))

        return dims, suggestions

    def get_goal_progress(
        self,
        db: Session,
        user_id: int,
        days: int = 7
    ) -> GoalProgressData:
        """
        获取用户健康目标达成率（Phase 36）

        根据用户设置的健康目标，统计指定天数内的饮食和运动数据，
        计算各维度达成率和综合得分。

        Args:
            db: 数据库会话
            user_id: 用户ID
            days: 统计天数（默认7天）

        Returns:
            GoalProgressData: 目标达成率数据
        """
        today = date.today()
        start_date = today - timedelta(days=max(days - 1, 0))
        end_date = today

        # 获取用户信息
        user = db.query(User).filter(User.id == user_id).first()
        health_goal = (user.health_goal if user and user.health_goal else "balanced")
        if health_goal not in HEALTH_GOAL_LABELS:
            health_goal = "balanced"
        health_goal_label = HEALTH_GOAL_LABELS[health_goal]

        # 收集统计数据
        data = self._gather_period_data(db, user_id, start_date, end_date)

        # 计算连续记录天数
        streak = self._calc_streak_days(db, user_id, end_date)

        # 根据目标类型评估
        evaluators = {
            "reduce_fat": self._evaluate_reduce_fat,
            "gain_muscle": self._evaluate_gain_muscle,
            "control_sugar": self._evaluate_control_sugar,
            "balanced": self._evaluate_balanced,
        }
        evaluator = evaluators.get(health_goal, self._evaluate_balanced)
        dimensions, suggestions = evaluator(data, user or User(
            id=user_id, nickname="", password="",
            weight=70.0, height=170.0, age=30, gender="male"
        ))

        # 通用建议
        if streak == 0:
            suggestions.append("开始记录你的饮食和运动吧，坚持是健康的关键！")
        elif streak >= 7:
            suggestions.append(f"已连续记录{streak}天，非常棒，继续保持！")

        # 计算综合得分（各维度加权平均）
        if dimensions:
            overall_score = sum(d.score for d in dimensions) / len(dimensions)
        else:
            overall_score = 0.0
        overall_score = self._clamp_score(overall_score)

        return GoalProgressData(
            user_id=user_id,
            health_goal=health_goal,
            health_goal_label=health_goal_label,
            period_days=days,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            overall_score=overall_score,
            overall_status=self._score_to_status(overall_score),
            dimensions=dimensions,
            suggestions=suggestions,
            streak_days=streak
        )


    # ============== Phase 51: 运动频率分析方法 ==============

    @staticmethod
    def _rate_frequency(active_days: int, total_days: int, period: str) -> tuple:
        """
        根据运动频率评级并给出建议。
        WHO建议：成人每周至少150分钟中等强度或75分钟高强度有氧运动，
        折算约每周至少3-5天有运动记录。

        Returns:
            (rating, suggestion)
        """
        if total_days == 0:
            return "insufficient", "暂无运动数据，建议开始规律运动"

        if period == "week":
            if active_days >= 5:
                return "excellent", "运动频率优秀，保持每周5天以上运动习惯！"
            elif active_days >= 3:
                return "good", "运动频率良好，建议逐步增加到每周5天"
            elif active_days >= 1:
                return "fair", "运动频率偏低，建议每周至少运动3天"
            else:
                return "insufficient", "本周暂无运动记录，建议尽快开始运动"
        else:  # month
            weekly_avg = active_days / (total_days / 7.0)
            if weekly_avg >= 5:
                return "excellent", f"月均每周运动{weekly_avg:.1f}天，频率优秀！"
            elif weekly_avg >= 3:
                return "good", f"月均每周运动{weekly_avg:.1f}天，频率良好"
            elif weekly_avg >= 1:
                return "fair", f"月均每周运动{weekly_avg:.1f}天，建议增加运动频率"
            else:
                return "insufficient", "本月运动频率不足，建议每周至少运动3天"

    def get_exercise_frequency(
        self,
        db: Session,
        user_id: int,
        period: str = "week"
    ) -> ExerciseFrequencyData:
        """
        获取运动频率分析数据（Phase 51）

        统计指定周期内的运动频率、类型分布，并给出评级和建议。

        Args:
            db: 数据库会话
            user_id: 用户ID
            period: 统计周期，week=最近7天，month=最近30天

        Returns:
            ExerciseFrequencyData: 运动频率分析数据
        """
        today = date.today()

        if period == "month":
            start_date = today - timedelta(days=29)
            total_days = 30
            period_label = "最近一个月"
        else:
            start_date = today - timedelta(days=6)
            total_days = 7
            period_label = "最近一周"

        # 查询周期内所有运动记录
        records = db.query(ExerciseRecord).filter(
            and_(
                ExerciseRecord.user_id == user_id,
                ExerciseRecord.exercise_date >= start_date,
                ExerciseRecord.exercise_date <= today
            )
        ).order_by(ExerciseRecord.exercise_date).all()

        # 按日期聚合
        daily_map: dict = {}
        type_map: dict = {}

        for rec in records:
            d_str = rec.exercise_date.isoformat() if hasattr(rec.exercise_date, 'isoformat') else str(rec.exercise_date)
            cal = rec.actual_calories or 0.0
            dur = rec.actual_duration or 0
            ex_type = rec.exercise_type or "outdoor"

            # 每日聚合
            if d_str not in daily_map:
                daily_map[d_str] = {
                    "count": 0, "total_duration": 0,
                    "total_calories": 0.0, "exercise_types": set()
                }
            daily_map[d_str]["count"] += 1
            daily_map[d_str]["total_duration"] += dur
            daily_map[d_str]["total_calories"] += cal
            daily_map[d_str]["exercise_types"].add(ex_type)

            # 类型聚合
            if ex_type not in type_map:
                type_map[ex_type] = {"count": 0, "total_duration": 0, "total_calories": 0.0}
            type_map[ex_type]["count"] += 1
            type_map[ex_type]["total_duration"] += dur
            type_map[ex_type]["total_calories"] += cal

        # 构建每日明细（覆盖整个周期，无记录的天也要包含）
        daily_data = []
        for i in range(total_days):
            d = start_date + timedelta(days=i)
            d_str = d.isoformat()
            if d_str in daily_map:
                info = daily_map[d_str]
                daily_data.append(DailyExerciseFrequency(
                    date=d_str,
                    count=info["count"],
                    total_duration=info["total_duration"],
                    total_calories=round(info["total_calories"], 2),
                    exercise_types=sorted(list(info["exercise_types"]))
                ))
            else:
                daily_data.append(DailyExerciseFrequency(
                    date=d_str,
                    count=0,
                    total_duration=0,
                    total_calories=0.0,
                    exercise_types=[]
                ))

        # 构建类型分布
        total_count = sum(v["count"] for v in type_map.values())
        type_distribution = []
        for ex_type, info in sorted(type_map.items(), key=lambda x: x[1]["count"], reverse=True):
            pct = (info["count"] / total_count * 100) if total_count > 0 else 0.0
            type_distribution.append(ExerciseTypeDistribution(
                exercise_type=ex_type,
                label=EXERCISE_TYPE_LABELS.get(ex_type, ex_type),
                count=info["count"],
                total_duration=info["total_duration"],
                total_calories=round(info["total_calories"], 2),
                percentage=round(pct, 1)
            ))

        # 汇总统计
        active_days = len(daily_map)
        total_exercise_count = total_count
        total_duration = sum(v["total_duration"] for v in daily_map.values())
        total_calories = sum(v["total_calories"] for v in daily_map.values())

        # 平均值
        weeks_in_period = total_days / 7.0
        avg_frequency = round(total_exercise_count / weeks_in_period, 1) if weeks_in_period > 0 else 0.0
        avg_duration = round(total_duration / total_exercise_count, 1) if total_exercise_count > 0 else 0.0
        avg_calories = round(total_calories / total_exercise_count, 1) if total_exercise_count > 0 else 0.0

        # 评级与建议
        rating, suggestion = self._rate_frequency(active_days, total_days, period)

        return ExerciseFrequencyData(
            user_id=user_id,
            period=period,
            period_label=period_label,
            start_date=start_date.isoformat(),
            end_date=today.isoformat(),
            total_days=total_days,
            active_days=active_days,
            total_exercise_count=total_exercise_count,
            total_duration=total_duration,
            total_calories=round(total_calories, 2),
            avg_frequency=avg_frequency,
            avg_duration_per_session=avg_duration,
            avg_calories_per_session=avg_calories,
            daily_data=daily_data,
            type_distribution=type_distribution,
            frequency_rating=rating,
            frequency_suggestion=suggestion
        )


# 创建单例实例
stats_service = StatsService()
