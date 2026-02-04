"""
食物相关数据模型
"""
from pydantic import BaseModel, Field


class FoodRequest(BaseModel):
    """菜品分析请求"""
    food_name: str = Field(..., description="菜品名称", min_length=1, max_length=50)
    
    class Config:
        json_schema_extra = {
            "example": {
                "food_name": "番茄炒蛋"
            }
        }


class FoodData(BaseModel):
    """菜品营养数据（Phase 7增强：含过敏原推理）"""
    name: str = Field(..., description="菜品名称")
    calories: float = Field(..., description="热量（千卡）")
    protein: float = Field(..., description="蛋白质（克）")
    fat: float = Field(..., description="脂肪（克）")
    carbs: float = Field(..., description="碳水化合物（克）")
    recommendation: str = Field(..., description="AI推荐理由")
    # Phase 7: 过敏原推理字段
    allergens: list[str] = Field(default=[], description="AI推理的过敏原代码列表（如peanut, egg等）")
    allergen_reasoning: str = Field(default="", description="过敏原推理说明")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "番茄炒蛋",
                "calories": 150.0,
                "protein": 10.5,
                "fat": 8.2,
                "carbs": 6.3,
                "recommendation": "这道菜营养均衡，蛋白质含量较高，适合减脂期食用。建议控制油量，搭配粗粮主食。",
                "allergens": ["egg"],
                "allergen_reasoning": "番茄炒蛋的主要食材是鸡蛋，属于蛋类过敏原。"
            }
        }


class FoodResponse(BaseModel):
    """API响应（Phase 7增强：含过敏原推理）"""
    success: bool = Field(..., description="请求是否成功")
    message: str = Field(default="", description="消息")
    data: FoodData | None = Field(None, description="菜品数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "分析成功",
                "data": {
                    "name": "番茄炒蛋",
                    "calories": 150.0,
                    "protein": 10.5,
                    "fat": 8.2,
                    "carbs": 6.3,
                    "recommendation": "这道菜营养均衡，适合减脂期食用",
                    "allergens": ["egg"],
                    "allergen_reasoning": "番茄炒蛋的主要食材是鸡蛋，属于蛋类过敏原。"
                }
            }
        }


class DishData(BaseModel):
    """菜品数据（用于菜单识别响应）"""
    name: str = Field(..., description="菜品名称")
    calories: float = Field(..., description="热量（千卡）")
    protein: float = Field(..., description="蛋白质（克）")
    fat: float = Field(..., description="脂肪（克）")
    carbs: float = Field(..., description="碳水化合物（克）")
    isRecommended: bool = Field(..., description="是否推荐")
    reason: str = Field(..., description="推荐理由")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "宫保鸡丁",
                "calories": 320.0,
                "protein": 28.0,
                "fat": 18.0,
                "carbs": 15.0,
                "isRecommended": True,
                "reason": "蛋白质丰富，适合您的减脂目标"
            }
        }


class RecognizeMenuResponse(BaseModel):
    """菜单识别响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("识别成功", description="消息")
    data: dict = Field(..., description="识别结果")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "识别成功",
                "data": {
                    "dishes": [
                        {
                            "name": "宫保鸡丁",
                            "calories": 320.0,
                            "protein": 28.0,
                            "fat": 18.0,
                            "carbs": 15.0,
                            "isRecommended": True,
                            "reason": "蛋白质丰富，适合您的减脂目标"
                        }
                    ]
                }
            }
        }


class AddDietRecordRequest(BaseModel):
    """添加饮食记录请求"""
    userId: int = Field(..., description="用户ID")
    foodName: str = Field(..., description="菜品名称", min_length=1, max_length=100)
    calories: float = Field(..., description="热量（kcal）", ge=0)
    protein: float = Field(0.0, description="蛋白质（g）", ge=0)
    fat: float = Field(0.0, description="脂肪（g）", ge=0)
    carbs: float = Field(0.0, description="碳水化合物（g）", ge=0)
    mealType: str = Field(..., description="餐次: 早餐/午餐/晚餐/加餐 或 breakfast/lunch/dinner/snack")
    recordDate: str = Field(..., description="记录日期（YYYY-MM-DD格式）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123,
                "foodName": "宫保鸡丁",
                "calories": 320.0,
                "protein": 28.0,
                "fat": 18.0,
                "carbs": 15.0,
                "mealType": "午餐",
                "recordDate": "2026-01-23"
            }
        }


class DietRecordData(BaseModel):
    """饮食记录数据"""
    id: int = Field(..., description="记录ID")
    userId: int = Field(..., description="用户ID")
    foodName: str = Field(..., description="菜品名称")
    calories: float = Field(..., description="热量（kcal）")
    protein: float = Field(0.0, description="蛋白质（g）")
    fat: float = Field(0.0, description="脂肪（g）")
    carbs: float = Field(0.0, description="碳水化合物（g）")
    mealType: str = Field(..., description="餐次")
    recordDate: str = Field(..., description="记录日期（YYYY-MM-DD）")
    createdAt: str = Field(..., description="创建时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "userId": 123,
                "foodName": "宫保鸡丁",
                "calories": 320.0,
                "protein": 28.0,
                "fat": 18.0,
                "carbs": 15.0,
                "mealType": "午餐",
                "recordDate": "2026-01-23",
                "createdAt": "2026-01-23T10:30:00"
            }
        }


class DietRecordsByDateResponse(BaseModel):
    """按日期分组的饮食记录响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("获取成功", description="消息")
    data: dict = Field(..., description="按日期分组的记录，格式: {\"2026-01-23\": [记录列表], ...}")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "2026-01-23": [
                        {
                            "id": 1,
                            "userId": 123,
                            "foodName": "宫保鸡丁",
                            "calories": 320.0,
                            "protein": 28.0,
                            "fat": 18.0,
                            "carbs": 15.0,
                            "mealType": "午餐",
                            "recordDate": "2026-01-23",
                            "createdAt": "2026-01-23T10:30:00"
                        }
                    ]
                }
            }
        }


class UpdateDietRecordRequest(BaseModel):
    """更新饮食记录请求"""
    userId: int = Field(..., description="用户ID（用于权限校验）", gt=0)
    foodName: str | None = Field(None, description="菜品名称", min_length=1, max_length=100)
    calories: float | None = Field(None, description="热量（kcal）", ge=0)
    protein: float | None = Field(None, description="蛋白质（g）", ge=0)
    fat: float | None = Field(None, description="脂肪（g）", ge=0)
    carbs: float | None = Field(None, description="碳水化合物（g）", ge=0)
    mealType: str | None = Field(None, description="餐次: 早餐/午餐/晚餐/加餐 或 breakfast/lunch/dinner/snack")
    recordDate: str | None = Field(None, description="记录日期（YYYY-MM-DD格式）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123,
                "foodName": "更新的菜名",
                "calories": 300.0,
                "protein": 25.0,
                "fat": 15.0,
                "carbs": 20.0,
                "mealType": "午餐",
                "recordDate": "2026-01-23"
            }
        }


class ApiResponse(BaseModel):
    """通用API响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("操作成功", description="消息")
    data: dict | None = Field(None, description="响应数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "记录成功",
                "data": None
            }
        }


# ==================== 过敏原检测相关模型 ====================

class AllergenCheckRequest(BaseModel):
    """过敏原检测请求"""
    food_name: str = Field(..., description="菜品名称", min_length=1, max_length=100)
    ingredients: list[str] | None = Field(None, description="配料列表（可选，提供后检测更精确）")
    user_allergens: list[str] | None = Field(None, description="用户的过敏原列表（用于匹配告警）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "food_name": "宫保鸡丁",
                "ingredients": ["鸡肉", "花生", "辣椒", "葱"],
                "user_allergens": ["花生", "鸡蛋"]
            }
        }


class AllergenInfo(BaseModel):
    """过敏原信息"""
    code: str = Field(..., description="过敏原代码")
    name: str = Field(..., description="过敏原中文名称")
    name_en: str = Field(..., description="过敏原英文名称")
    matched_keywords: list[str] = Field(..., description="匹配到的关键词")
    confidence: str = Field(..., description="置信度：high/medium/low")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "peanut",
                "name": "花生",
                "name_en": "Peanut",
                "matched_keywords": ["花生", "宫保"],
                "confidence": "high"
            }
        }


class AllergenWarning(BaseModel):
    """过敏原警告信息"""
    allergen: str = Field(..., description="过敏原名称")
    level: str = Field(..., description="警告级别：high/medium/low")
    message: str = Field(..., description="警告消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "allergen": "花生",
                "level": "high",
                "message": "警告：检测到您的过敏原【花生】，匹配关键词：花生, 宫保"
            }
        }


class AllergenCheckResponse(BaseModel):
    """过敏原检测响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("检测完成", description="消息")
    data: dict = Field(..., description="检测结果")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "检测完成",
                "data": {
                    "food_name": "宫保鸡丁",
                    "detected_allergens": [
                        {
                            "code": "peanut",
                            "name": "花生",
                            "name_en": "Peanut",
                            "matched_keywords": ["花生", "宫保"],
                            "confidence": "high"
                        }
                    ],
                    "allergen_count": 1,
                    "has_allergens": True,
                    "warnings": [
                        {
                            "allergen": "花生",
                            "level": "high",
                            "message": "警告：检测到您的过敏原【花生】"
                        }
                    ],
                    "has_warnings": True
                }
            }
        }


class AllergenCategoryInfo(BaseModel):
    """过敏原类别信息"""
    code: str = Field(..., description="过敏原代码")
    name: str = Field(..., description="过敏原中文名称")
    name_en: str = Field(..., description="过敏原英文名称")
    description: str = Field(..., description="描述")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "peanut",
                "name": "花生",
                "name_en": "Peanut",
                "description": "包括花生及花生制品"
            }
        }


class AllergenCategoriesResponse(BaseModel):
    """过敏原类别列表响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("获取成功", description="消息")
    data: list[dict] = Field(..., description="过敏原类别列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": [
                    {
                        "code": "milk",
                        "name": "乳制品",
                        "name_en": "Milk",
                        "description": "包括牛奶及其制品"
                    },
                    {
                        "code": "peanut",
                        "name": "花生",
                        "name_en": "Peanut",
                        "description": "包括花生及花生制品"
                    }
                ]
            }
        }
