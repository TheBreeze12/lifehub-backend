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
