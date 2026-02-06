"""
统计相关数据模型
Phase 15: 热量收支统计
Phase 16: 营养素摄入统计
Phase 26: 饮食-运动数据联动（新增字段）
"""
from pydantic import BaseModel, Field
from typing import Optional


# ============== 膳食指南常量 ==============
# 中国居民膳食指南2022建议
DIETARY_GUIDELINES = {
    "protein": {"min": 10, "max": 15, "name": "蛋白质"},    # 10-15%
    "fat": {"min": 20, "max": 30, "name": "脂肪"},          # 20-30%
    "carbs": {"min": 50, "max": 65, "name": "碳水化合物"},  # 50-65%
}

# 每克营养素的热量（kcal）
PROTEIN_KCAL_PER_GRAM = 4
FAT_KCAL_PER_GRAM = 9
CARBS_KCAL_PER_GRAM = 4



class DailyCalorieStats(BaseModel):
    """每日热量统计数据"""
    date: str = Field(..., description="统计日期（YYYY-MM-DD）")
    user_id: int = Field(..., description="用户ID")
    
    # 摄入相关
    intake_calories: float = Field(0.0, description="摄入热量（kcal）")
    meal_count: int = Field(0, description="餐次数量")
    
    # 消耗相关（有效消耗：有运动记录时用实际值，否则用计划值）
    burn_calories: float = Field(0.0, description="有效消耗热量（kcal）")
    exercise_count: int = Field(0, description="运动计划项目数量")
    exercise_duration: int = Field(0, description="运动计划总时长（分钟）")
    
    # Phase 26新增：计划消耗 vs 实际消耗
    planned_burn_calories: float = Field(0.0, description="计划消耗热量（来自运动计划，kcal）")
    actual_burn_calories: float = Field(0.0, description="实际消耗热量（来自运动记录，kcal）")
    actual_exercise_count: int = Field(0, description="实际运动记录数量")
    actual_exercise_duration: int = Field(0, description="实际运动总时长（分钟）")
    
    # 净热量
    net_calories: float = Field(0.0, description="净热量（摄入-有效消耗）")
    
    # Phase 26新增：热量缺口与达成率
    calorie_deficit: float = Field(0.0, description="热量缺口（摄入-有效消耗，正值表示热量盈余）")
    goal_achievement_rate: Optional[float] = Field(
        None, description="目标达成率（%），实际消耗/计划消耗×100，无计划时为None"
    )
    
    # 餐次分类统计（可选）
    meal_breakdown: Optional[dict] = Field(None, description="餐次分类统计")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-02-04",
                "user_id": 1,
                "intake_calories": 1800.0,
                "meal_count": 3,
                "burn_calories": 500.0,
                "exercise_count": 2,
                "exercise_duration": 60,
                "planned_burn_calories": 500.0,
                "actual_burn_calories": 450.0,
                "actual_exercise_count": 2,
                "actual_exercise_duration": 55,
                "net_calories": 1350.0,
                "calorie_deficit": 1350.0,
                "goal_achievement_rate": 90.0,
                "meal_breakdown": {
                    "breakfast": 400.0,
                    "lunch": 700.0,
                    "dinner": 600.0,
                    "snack": 100.0
                }
            }
        }


class DailyBreakdown(BaseModel):
    """每日统计明细（用于周统计）"""
    date: str = Field(..., description="日期")
    intake_calories: float = Field(0.0, description="摄入热量")
    burn_calories: float = Field(0.0, description="消耗热量")
    net_calories: float = Field(0.0, description="净热量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-02-04",
                "intake_calories": 1800.0,
                "burn_calories": 500.0,
                "net_calories": 1300.0
            }
        }


class WeeklyCalorieStats(BaseModel):
    """每周热量统计数据"""
    week_start: str = Field(..., description="周起始日期（YYYY-MM-DD，周一）")
    week_end: str = Field(..., description="周结束日期（YYYY-MM-DD，周日）")
    user_id: int = Field(..., description="用户ID")
    
    # 周总计
    total_intake: float = Field(0.0, description="周总摄入热量（kcal）")
    total_burn: float = Field(0.0, description="周总消耗热量（kcal）")
    total_net: float = Field(0.0, description="周净热量")
    
    # 周平均
    avg_intake: float = Field(0.0, description="日均摄入热量（kcal）")
    avg_burn: float = Field(0.0, description="日均消耗热量（kcal）")
    avg_net: float = Field(0.0, description="日均净热量")
    
    # 统计数据
    total_meals: int = Field(0, description="周总餐次")
    total_exercises: int = Field(0, description="周总运动次数")
    active_days: int = Field(0, description="有记录的天数")
    
    # 每日明细
    daily_breakdown: list[DailyBreakdown] = Field(default_factory=list, description="每日明细")
    
    class Config:
        json_schema_extra = {
            "example": {
                "week_start": "2026-02-03",
                "week_end": "2026-02-09",
                "user_id": 1,
                "total_intake": 12600.0,
                "total_burn": 3500.0,
                "total_net": 9100.0,
                "avg_intake": 1800.0,
                "avg_burn": 500.0,
                "avg_net": 1300.0,
                "total_meals": 21,
                "total_exercises": 14,
                "active_days": 7,
                "daily_breakdown": []
            }
        }


class DailyCalorieStatsResponse(BaseModel):
    """每日热量统计响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("获取成功", description="消息")
    data: DailyCalorieStats = Field(..., description="统计数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "date": "2026-02-04",
                    "user_id": 1,
                    "intake_calories": 1800.0,
                    "meal_count": 3,
                    "burn_calories": 500.0,
                    "exercise_count": 2,
                    "exercise_duration": 60,
                    "planned_burn_calories": 500.0,
                    "actual_burn_calories": 450.0,
                    "actual_exercise_count": 2,
                    "actual_exercise_duration": 55,
                    "net_calories": 1350.0,
                    "calorie_deficit": 1350.0,
                    "goal_achievement_rate": 90.0
                }
            }
        }


class WeeklyCalorieStatsResponse(BaseModel):
    """每周热量统计响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("获取成功", description="消息")
    data: WeeklyCalorieStats = Field(..., description="统计数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "week_start": "2026-02-03",
                    "week_end": "2026-02-09",
                    "user_id": 1,
                    "total_intake": 12600.0,
                    "total_burn": 3500.0,
                    "total_net": 9100.0,
                    "avg_intake": 1800.0,
                    "avg_burn": 500.0,
                    "avg_net": 1300.0,
                    "total_meals": 21,
                    "total_exercises": 14,
                    "active_days": 7,
                    "daily_breakdown": []
                }
            }
        }


# ============== Phase 16: 营养素统计模型 ==============

class NutrientComparison(BaseModel):
    """营养素与膳食指南对比"""
    actual_ratio: float = Field(..., description="实际占比（%）")
    recommended_min: float = Field(..., description="建议最小占比（%）")
    recommended_max: float = Field(..., description="建议最大占比（%）")
    status: str = Field(..., description="状态：low/normal/high")
    message: str = Field(..., description="对比说明")
    
    class Config:
        json_schema_extra = {
            "example": {
                "actual_ratio": 12.5,
                "recommended_min": 10,
                "recommended_max": 15,
                "status": "normal",
                "message": "蛋白质摄入在建议范围内"
            }
        }


class GuidelinesComparison(BaseModel):
    """膳食指南对比结果"""
    protein: NutrientComparison = Field(..., description="蛋白质对比")
    fat: NutrientComparison = Field(..., description="脂肪对比")
    carbs: NutrientComparison = Field(..., description="碳水化合物对比")
    
    class Config:
        json_schema_extra = {
            "example": {
                "protein": {
                    "actual_ratio": 12.5,
                    "recommended_min": 10,
                    "recommended_max": 15,
                    "status": "normal",
                    "message": "蛋白质摄入在建议范围内"
                },
                "fat": {
                    "actual_ratio": 35.0,
                    "recommended_min": 20,
                    "recommended_max": 30,
                    "status": "high",
                    "message": "脂肪摄入偏高，建议控制油脂摄入"
                },
                "carbs": {
                    "actual_ratio": 52.5,
                    "recommended_min": 50,
                    "recommended_max": 65,
                    "status": "normal",
                    "message": "碳水化合物摄入在建议范围内"
                }
            }
        }


class DailyNutrientStats(BaseModel):
    """每日营养素统计数据"""
    date: str = Field(..., description="统计日期（YYYY-MM-DD）")
    user_id: int = Field(..., description="用户ID")
    
    # 营养素总量（克）
    total_protein: float = Field(0.0, description="蛋白质总量（g）")
    total_fat: float = Field(0.0, description="脂肪总量（g）")
    total_carbs: float = Field(0.0, description="碳水化合物总量（g）")
    total_calories: float = Field(0.0, description="总热量（kcal）")
    
    # 营养素热量（kcal）
    protein_calories: float = Field(0.0, description="蛋白质提供的热量（kcal）")
    fat_calories: float = Field(0.0, description="脂肪提供的热量（kcal）")
    carbs_calories: float = Field(0.0, description="碳水化合物提供的热量（kcal）")
    
    # 营养素占比（基于营养素热量计算，%）
    protein_ratio: float = Field(0.0, description="蛋白质热量占比（%）")
    fat_ratio: float = Field(0.0, description="脂肪热量占比（%）")
    carbs_ratio: float = Field(0.0, description="碳水化合物热量占比（%）")
    
    # 餐次统计
    meal_count: int = Field(0, description="餐次数量")
    meal_breakdown: Optional[dict] = Field(None, description="餐次分类统计")
    
    # 膳食指南对比
    guidelines_comparison: Optional[GuidelinesComparison] = Field(
        None, description="与膳食指南对比结果"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-02-05",
                "user_id": 1,
                "total_protein": 75.0,
                "total_fat": 60.0,
                "total_carbs": 280.0,
                "total_calories": 1960.0,
                "protein_calories": 300.0,
                "fat_calories": 540.0,
                "carbs_calories": 1120.0,
                "protein_ratio": 15.3,
                "fat_ratio": 27.6,
                "carbs_ratio": 57.1,
                "meal_count": 3,
                "meal_breakdown": {
                    "breakfast": {"protein": 20.0, "fat": 15.0, "carbs": 60.0},
                    "lunch": {"protein": 35.0, "fat": 30.0, "carbs": 120.0},
                    "dinner": {"protein": 20.0, "fat": 15.0, "carbs": 100.0}
                },
                "guidelines_comparison": {
                    "protein": {
                        "actual_ratio": 15.3,
                        "recommended_min": 10,
                        "recommended_max": 15,
                        "status": "normal",
                        "message": "蛋白质摄入在建议范围内"
                    },
                    "fat": {
                        "actual_ratio": 27.6,
                        "recommended_min": 20,
                        "recommended_max": 30,
                        "status": "normal",
                        "message": "脂肪摄入在建议范围内"
                    },
                    "carbs": {
                        "actual_ratio": 57.1,
                        "recommended_min": 50,
                        "recommended_max": 65,
                        "status": "normal",
                        "message": "碳水化合物摄入在建议范围内"
                    }
                }
            }
        }


class DailyNutrientStatsResponse(BaseModel):
    """每日营养素统计响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("获取成功", description="消息")
    data: DailyNutrientStats = Field(..., description="营养素统计数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "date": "2026-02-05",
                    "user_id": 1,
                    "total_protein": 75.0,
                    "total_fat": 60.0,
                    "total_carbs": 280.0,
                    "total_calories": 1960.0,
                    "protein_ratio": 15.3,
                    "fat_ratio": 27.6,
                    "carbs_ratio": 57.1,
                    "meal_count": 3
                }
            }
        }


# ============== Phase 36: 健康目标达成率模型 ==============

# 健康目标中文标签
HEALTH_GOAL_LABELS = {
    "reduce_fat": "减脂",
    "gain_muscle": "增肌",
    "control_sugar": "控糖",
    "balanced": "均衡",
}


class GoalDimension(BaseModel):
    """健康目标评估维度"""
    name: str = Field(..., description="维度名称（如：热量控制、蛋白质摄入）")
    score: float = Field(..., description="维度得分（0-100）")
    status: str = Field(..., description="状态：excellent/good/fair/poor")
    current_value: float = Field(..., description="当前指标值")
    target_value: float = Field(..., description="目标指标值")
    unit: str = Field(..., description="指标单位")
    description: str = Field(..., description="维度描述说明")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "热量控制",
                "score": 85.0,
                "status": "good",
                "current_value": 1800.0,
                "target_value": 2000.0,
                "unit": "kcal/天",
                "description": "日均摄入热量在合理范围内"
            }
        }


class GoalProgressData(BaseModel):
    """健康目标达成率数据"""
    user_id: int = Field(..., description="用户ID")
    health_goal: str = Field(..., description="健康目标：reduce_fat/gain_muscle/control_sugar/balanced")
    health_goal_label: str = Field(..., description="健康目标中文标签")
    period_days: int = Field(..., description="统计天数")
    start_date: str = Field(..., description="统计起始日期（YYYY-MM-DD）")
    end_date: str = Field(..., description="统计结束日期（YYYY-MM-DD）")
    overall_score: float = Field(..., description="综合得分（0-100）")
    overall_status: str = Field(..., description="综合状态：excellent/good/fair/poor")
    dimensions: list[GoalDimension] = Field(default_factory=list, description="各维度评估")
    suggestions: list[str] = Field(default_factory=list, description="个性化建议列表")
    streak_days: int = Field(0, description="连续记录天数（从今天往前）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "health_goal": "reduce_fat",
                "health_goal_label": "减脂",
                "period_days": 7,
                "start_date": "2026-02-01",
                "end_date": "2026-02-07",
                "overall_score": 75.0,
                "overall_status": "good",
                "dimensions": [
                    {
                        "name": "热量控制",
                        "score": 85.0,
                        "status": "good",
                        "current_value": 1800.0,
                        "target_value": 2000.0,
                        "unit": "kcal/天",
                        "description": "日均摄入热量在合理范围内"
                    }
                ],
                "suggestions": ["继续保持每日热量缺口", "建议增加有氧运动时间"],
                "streak_days": 5
            }
        }


class GoalProgressResponse(BaseModel):
    """健康目标达成率响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("获取成功", description="消息")
    data: GoalProgressData = Field(..., description="目标达成率数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "user_id": 1,
                    "health_goal": "reduce_fat",
                    "health_goal_label": "减脂",
                    "period_days": 7,
                    "start_date": "2026-02-01",
                    "end_date": "2026-02-07",
                    "overall_score": 75.0,
                    "overall_status": "good",
                    "dimensions": [],
                    "suggestions": ["继续保持"],
                    "streak_days": 5
                }
            }
        }

