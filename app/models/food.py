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
    """菜品营养数据"""
    name: str = Field(..., description="菜品名称")
    calories: float = Field(..., description="热量（千卡）")
    protein: float = Field(..., description="蛋白质（克）")
    fat: float = Field(..., description="脂肪（克）")
    carbs: float = Field(..., description="碳水化合物（克）")
    recommendation: str = Field(..., description="AI推荐理由")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "番茄炒蛋",
                "calories": 150.0,
                "protein": 10.5,
                "fat": 8.2,
                "carbs": 6.3,
                "recommendation": "这道菜营养均衡，蛋白质含量较高，适合减脂期食用。建议控制油量，搭配粗粮主食。"
            }
        }


class FoodResponse(BaseModel):
    """API响应"""
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
                    "recommendation": "这道菜营养均衡，适合减脂期食用"
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
