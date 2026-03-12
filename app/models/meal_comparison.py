"""
餐前餐后对比相关Pydantic模型
Phase 10: 餐前餐后对比核心创新功能数据模型
"""
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== 餐前上传相关模型 ====================

class BeforeMealUploadResponse(BaseModel):
    """餐前图片上传响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("上传成功", description="消息")
    data: dict = Field(..., description="上传结果")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "餐前图片上传成功",
                "data": {
                    "comparison_id": 1,
                    "before_image_url": "/uploads/meal/before_1.jpg",
                    "before_features": {
                        "dishes": [
                            {"name": "红烧肉", "estimated_weight": 200, "estimated_calories": 500},
                            {"name": "清炒时蔬", "estimated_weight": 150, "estimated_calories": 80}
                        ],
                        "total_estimated_calories": 580
                    },
                    "status": "pending_after"
                }
            }
        }


# ==================== 餐后上传相关模型 ====================

class AfterMealUploadResponse(BaseModel):
    """餐后图片上传响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("上传成功", description="消息")
    data: dict = Field(..., description="对比结果")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "餐后图片上传成功，对比完成",
                "data": {
                    "comparison_id": 1,
                    "before_image_url": "/uploads/meal/before_1.jpg",
                    "after_image_url": "/uploads/meal/after_1.jpg",
                    "consumption_ratio": 0.75,
                    "original_calories": 580,
                    "net_calories": 435,
                    "original_protein": 25.0,
                    "original_fat": 35.0,
                    "original_carbs": 15.0,
                    "net_protein": 18.75,
                    "net_fat": 26.25,
                    "net_carbs": 11.25,
                    "comparison_analysis": "您大约吃掉了75%的食物，剩余了一些红烧肉和少量蔬菜。",
                    "status": "completed"
                }
            }
        }


# ==================== 对比记录数据模型 ====================

class MealComparisonData(BaseModel):
    """餐前餐后对比记录数据"""
    id: int = Field(..., description="对比记录ID")
    userId: int = Field(..., description="用户ID")
    beforeImageUrl: str | None = Field(None, description="餐前图片URL")
    afterImageUrl: str | None = Field(None, description="餐后图片URL")
    beforeFeatures: dict | None = Field(None, description="餐前图片特征")
    afterFeatures: dict | None = Field(None, description="餐后图片特征")
    consumptionRatio: float | None = Field(None, description="消耗比例（0-1）")
    originalCalories: float | None = Field(None, description="原始估算热量（kcal）")
    netCalories: float | None = Field(None, description="净摄入热量（kcal）")
    originalProtein: float | None = Field(None, description="原始蛋白质（g）")
    originalFat: float | None = Field(None, description="原始脂肪（g）")
    originalCarbs: float | None = Field(None, description="原始碳水化合物（g）")
    netProtein: float | None = Field(None, description="净摄入蛋白质（g）")
    netFat: float | None = Field(None, description="净摄入脂肪（g）")
    netCarbs: float | None = Field(None, description="净摄入碳水化合物（g）")
    status: str = Field(..., description="状态: pending_before/pending_after/completed")
    comparisonAnalysis: str | None = Field(None, description="AI对比分析说明")
    createdAt: str = Field(..., description="创建时间")
    updatedAt: str = Field(..., description="更新时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "userId": 123,
                "beforeImageUrl": "/uploads/meal/before_1.jpg",
                "afterImageUrl": "/uploads/meal/after_1.jpg",
                "beforeFeatures": {
                    "dishes": [{"name": "红烧肉", "estimated_calories": 500}]
                },
                "afterFeatures": {
                    "dishes": [{"name": "红烧肉", "remaining_ratio": 0.25}]
                },
                "consumptionRatio": 0.75,
                "originalCalories": 580,
                "netCalories": 435,
                "originalProtein": 25.0,
                "originalFat": 35.0,
                "originalCarbs": 15.0,
                "netProtein": 18.75,
                "netFat": 26.25,
                "netCarbs": 11.25,
                "status": "completed",
                "comparisonAnalysis": "您大约吃掉了75%的食物",
                "createdAt": "2026-02-04T12:00:00",
                "updatedAt": "2026-02-04T12:30:00"
            }
        }


class MealComparisonListResponse(BaseModel):
    """餐前餐后对比记录列表响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("获取成功", description="消息")
    data: list[dict] = Field(..., description="对比记录列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": [
                    {
                        "id": 1,
                        "userId": 123,
                        "consumptionRatio": 0.75,
                        "netCalories": 435,
                        "status": "completed",
                        "createdAt": "2026-02-04T12:00:00"
                    }
                ]
            }
        }


class MealComparisonDetailResponse(BaseModel):
    """餐前餐后对比记录详情响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("获取成功", description="消息")
    data: dict | None = Field(None, description="对比记录详情")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "id": 1,
                    "userId": 123,
                    "beforeImageUrl": "/uploads/meal/before_1.jpg",
                    "afterImageUrl": "/uploads/meal/after_1.jpg",
                    "consumptionRatio": 0.75,
                    "originalCalories": 580,
                    "netCalories": 435,
                    "status": "completed",
                    "comparisonAnalysis": "您大约吃掉了75%的食物",
                    "createdAt": "2026-02-04T12:00:00"
                }
            }
        }


# ==================== 手动调整相关模型 ====================

class AdjustConsumptionRequest(BaseModel):
    """手动调整消耗比例请求"""
    userId: int = Field(..., description="用户ID（用于权限校验）", gt=0)
    consumptionRatio: float = Field(..., description="手动调整的消耗比例（0-1）", ge=0, le=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123,
                "consumptionRatio": 0.8
            }
        }


class AdjustConsumptionResponse(BaseModel):
    """手动调整消耗比例响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("调整成功", description="消息")
    data: dict = Field(..., description="调整后的数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "调整成功",
                "data": {
                    "comparison_id": 1,
                    "consumptionRatio": 0.8,
                    "originalCalories": 580,
                    "netCalories": 464,
                    "netProtein": 20.0,
                    "netFat": 28.0,
                    "netCarbs": 12.0
                }
            }
        }


# ==================== 图片特征相关模型 ====================

class DishFeature(BaseModel):
    """单个菜品特征"""
    name: str = Field(..., description="菜品名称")
    estimated_weight: float | None = Field(None, description="估算重量（g）")
    estimated_calories: float = Field(..., description="估算热量（kcal）")
    estimated_protein: float | None = Field(None, description="估算蛋白质（g）")
    estimated_fat: float | None = Field(None, description="估算脂肪（g）")
    estimated_carbs: float | None = Field(None, description="估算碳水化合物（g）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "红烧肉",
                "estimated_weight": 200,
                "estimated_calories": 500,
                "estimated_protein": 25.0,
                "estimated_fat": 35.0,
                "estimated_carbs": 10.0
            }
        }


class BeforeFeatures(BaseModel):
    """餐前图片特征"""
    dishes: list[DishFeature] = Field(..., description="识别到的菜品列表")
    total_estimated_calories: float = Field(..., description="总估算热量（kcal）")
    total_estimated_protein: float | None = Field(None, description="总估算蛋白质（g）")
    total_estimated_fat: float | None = Field(None, description="总估算脂肪（g）")
    total_estimated_carbs: float | None = Field(None, description="总估算碳水化合物（g）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dishes": [
                    {"name": "红烧肉", "estimated_calories": 500},
                    {"name": "清炒时蔬", "estimated_calories": 80}
                ],
                "total_estimated_calories": 580,
                "total_estimated_protein": 30.0,
                "total_estimated_fat": 38.0,
                "total_estimated_carbs": 15.0
            }
        }


class RemainingDishFeature(BaseModel):
    """餐后剩余菜品特征"""
    name: str = Field(..., description="菜品名称")
    remaining_ratio: float = Field(..., description="剩余比例（0-1）", ge=0, le=1)
    remaining_weight: float | None = Field(None, description="剩余重量（g）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "红烧肉",
                "remaining_ratio": 0.25,
                "remaining_weight": 50
            }
        }


class AfterFeatures(BaseModel):
    """餐后图片特征"""
    dishes: list[RemainingDishFeature] = Field(..., description="剩余菜品列表")
    overall_remaining_ratio: float = Field(..., description="整体剩余比例（0-1）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dishes": [
                    {"name": "红烧肉", "remaining_ratio": 0.25},
                    {"name": "清炒时蔬", "remaining_ratio": 0.0}
                ],
                "overall_remaining_ratio": 0.25
            }
        }
