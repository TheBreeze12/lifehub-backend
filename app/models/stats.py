"""
统计相关数据模型
Phase 15: 热量收支统计
Phase 16: 营养素摄入统计
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
    
    # 消耗相关
    burn_calories: float = Field(0.0, description="消耗热量（kcal）")
    exercise_count: int = Field(0, description="运动项目数量")
    exercise_duration: int = Field(0, description="运动总时长（分钟）")
    
    # 净热量
    net_calories: float = Field(0.0, description="净热量（摄入-消耗）")
    
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
                "net_calories": 1300.0,
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
                    "net_calories": 1300.0
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

