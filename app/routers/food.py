"""
食物相关API路由
"""
from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.models.food import (
    FoodRequest, 
    FoodResponse, 
    FoodData,
    RecognizeMenuResponse
)
from app.services.ai_service import AIService
from app.database import get_db
from app.db_models.user import User

router = APIRouter(prefix="/api/food", tags=["食物分析"])

# 初始化AI服务
ai_service = AIService()


@router.post("/analyze", response_model=FoodResponse)
async def analyze_food(request: FoodRequest):
    """
    分析菜品营养成分
    
    - **food_name**: 菜品名称
    """
    try:
        # 调用AI服务分析
        nutrition_data = ai_service.analyze_food_nutrition(request.food_name)
        
        # 构建响应
        food_data = FoodData(**nutrition_data)
        
        return FoodResponse(
            success=True,
            message="分析成功",
            data=food_data
        )
        
    except ValueError as e:
        # API Key未设置
        raise HTTPException(status_code=500, detail=f"服务配置错误: {str(e)}")
        
    except Exception as e:
        # 其他错误
        print(f"分析食物失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/recognize", response_model=RecognizeMenuResponse)
async def recognize_menu(
    image: UploadFile = File(..., description="菜单图片文件"),
    userId: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    上传菜单图片识别
    
    - **image**: 菜单图片文件
    - **userId**: 用户ID（可选，用于根据健康目标生成推荐）
    """
    try:
        # 验证文件类型
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")
        
        # 获取用户健康目标（如果提供了userId）
        health_goal = None
        if userId:
            user = db.query(User).filter(User.id == userId).first()
            if user:
                health_goal = user.health_goal
        
        # 调用AI服务识别菜单
        dishes = ai_service.recognize_menu_image(image.file, health_goal)
        
        # 构建响应
        return RecognizeMenuResponse(
            code=200,
            message="识别成功",
            data={"dishes": dishes}
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"请求参数错误: {str(e)}")
    except Exception as e:
        print(f"识别菜单失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"识别菜单失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "food-analysis"}

