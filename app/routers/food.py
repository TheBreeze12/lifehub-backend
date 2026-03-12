"""
食物相关API路由
"""
from fastapi import APIRouter, File, UploadFile, Depends, Form
from sqlalchemy.orm import Session
from typing import Optional
from app.models.food import (
    FoodRequest,
    FoodResponse,
    FoodData,
    RecognizeMenuResponse,
    AddDietRecordRequest,
    UpdateDietRecordRequest,
    DietRecordData,
    DietRecordsByDateResponse,
    ApiResponse,
    AllergenCheckRequest,
    AllergenCheckResponse,
    AllergenCategoriesResponse,
    RecommendationResponse,
)
from app.models.meal_comparison import BeforeMealUploadResponse, AfterMealUploadResponse
from app.services import food_service
from app.database import get_db

router = APIRouter(prefix="/api/food", tags=["食物分析"])


@router.post("/analyze", response_model=FoodResponse)
async def analyze_food(request: FoodRequest):
    """
    分析菜品营养成分

    - **food_name**: 菜品名称
    """
    return food_service.analyze_food(request)


@router.post("/recognize", response_model=RecognizeMenuResponse)
async def recognize_menu(
    image: UploadFile = File(..., description="菜单图片文件"),
    userId: Optional[str] = Form(None, description="用户ID（可选）"),
    db: Session = Depends(get_db)
):
    """
    上传菜单图片识别

    - **image**: 菜单图片文件
    - **userId**: 用户ID（可选，用于根据健康目标生成推荐）
    """
    return food_service.recognize_menu(db, image, userId)


@router.get("/latest-recognition")
async def get_latest_recognition(
    userId: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    获取用户最新的菜单识别结果

    - **userId**: 用户ID（可选）
    """
    return food_service.get_latest_recognition(db, userId)


@router.post("/record", response_model=ApiResponse)
async def add_diet_record(
    request: AddDietRecordRequest,
    db: Session = Depends(get_db)
):
    """
    添加饮食记录

    - **userId**: 用户ID
    - **foodName**: 菜品名称
    - **calories**: 热量（kcal）
    - **protein**: 蛋白质（g）
    - **fat**: 脂肪（g）
    - **carbs**: 碳水化合物（g）
    - **mealType**: 餐次（早餐/午餐/晚餐/加餐 或 breakfast/lunch/dinner/snack）
    - **recordDate**: 记录日期（YYYY-MM-DD格式）
    """
    return food_service.add_diet_record(db, request)


@router.get("/records", response_model=DietRecordsByDateResponse)
async def get_diet_records(
    userId: int,
    db: Session = Depends(get_db)
):
    """
    获取用户所有饮食记录，按日期划分

    - **userId**: 用户ID
    """
    return food_service.get_diet_records(db, userId)


@router.get("/records/today", response_model=DietRecordsByDateResponse)
async def get_today_diet_records(
    userId: int,
    db: Session = Depends(get_db)
):
    """
    获取用户今天的饮食记录

    - **userId**: 用户ID
    """
    return food_service.get_today_diet_records(db, userId)


@router.put("/diet/{record_id}", response_model=ApiResponse)
async def update_diet_record(
    record_id: int,
    request: UpdateDietRecordRequest,
    db: Session = Depends(get_db)
):
    """
    更新饮食记录

    - **record_id**: 记录ID
    - **userId**: 用户ID（用于权限校验，只能更新自己的记录）
    - **foodName**: 菜品名称（可选）
    - **calories**: 热量（可选）
    - **protein**: 蛋白质（可选）
    - **fat**: 脂肪（可选）
    - **carbs**: 碳水化合物（可选）
    - **mealType**: 餐次（可选）
    - **recordDate**: 记录日期（可选）
    """
    return food_service.update_diet_record(db, record_id, request)


@router.delete("/diet/{record_id}", response_model=ApiResponse)
async def delete_diet_record(
    record_id: int,
    userId: int,
    db: Session = Depends(get_db)
):
    """
    删除饮食记录

    - **record_id**: 记录ID
    - **userId**: 用户ID（用于权限校验，只能删除自己的记录）
    """
    return food_service.delete_diet_record(db, record_id, userId)


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "food-analysis"}


# ==================== 过敏原检测接口 ====================

@router.post("/allergen/check", response_model=AllergenCheckResponse)
async def check_allergens(request: AllergenCheckRequest):
    """
    检测菜品中的过敏原

    基于关键词匹配检测八大类过敏原：
    - 乳制品（牛奶）
    - 鸡蛋
    - 鱼类
    - 甲壳类（虾、蟹等）
    - 花生
    - 树坚果（杏仁、核桃等）
    - 小麦（麸质）
    - 大豆

    - **food_name**: 菜品名称
    - **ingredients**: 配料列表（可选，提供后检测更精确）
    - **user_allergens**: 用户的过敏原列表（可选，用于匹配告警）
    """
    return food_service.check_allergens(request)


@router.get("/allergen/categories", response_model=AllergenCategoriesResponse)
async def get_allergen_categories():
    """
    获取所有过敏原类别信息

    返回八大类过敏原的详细信息，包括：
    - 过敏原代码
    - 中文名称
    - 英文名称
    - 描述
    """
    return food_service.get_allergen_categories()


# ==================== Phase 41: 个性化菜品推荐接口 ====================

@router.get("/recommend", response_model=RecommendationResponse)
async def get_food_recommendations(
    user_id: int,
    meal_type: str = "lunch",
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """
    获取个性化菜品推荐

    基于用户健康目标、热量配额、历史偏好的多因子推荐算法：
    - 健康目标匹配（减脂/增肌/控糖/均衡）
    - 热量配额过滤（根据当日剩余热量）
    - 历史偏好排序（根据用户饮食记录）
    - 过敏原过滤（自动排除含用户过敏原的菜品）
    - 多样性保证（今天已吃过的菜品降权）

    - **user_id**: 用户ID（必填）
    - **meal_type**: 餐次（breakfast/lunch/dinner/snack，默认lunch）
    - **limit**: 返回推荐数量（默认5）
    """
    return food_service.get_food_recommendations(db, user_id, meal_type, limit)


# ==================== 餐前餐后对比接口 (Phase 11) ====================

ensure_upload_dir = food_service.ensure_upload_dir


@router.post("/meal/before", response_model=BeforeMealUploadResponse)
async def upload_before_meal_image(
    image: UploadFile = File(..., description="餐前食物图片"),
    user_id: int = Form(..., description="用户ID"),
    db: Session = Depends(get_db)
):
    """
    上传餐前图片

    Phase 11: 餐前图片上传接口

    接收餐前食物图片，调用AI进行特征提取（菜品识别、份量估算、热量估算），
    创建MealComparison记录并返回comparison_id供后续餐后上传使用。

    - **image**: 餐前食物图片文件（支持jpg, jpeg, png格式）
    - **user_id**: 用户ID

    返回：
    - comparison_id: 对比记录ID，用于后续餐后图片上传
    - before_image_url: 餐前图片保存路径
    - before_features: AI识别的菜品特征（菜品列表、估算热量等）
    - status: 记录状态（pending_after表示等待餐后图片上传）
    """
    return await food_service.upload_before_meal_image(db, image, user_id)


# ==================== Phase 12: 餐后图片上传与对比计算 ====================

@router.post("/meal/after/{comparison_id}", response_model=AfterMealUploadResponse)
async def upload_after_meal_image(
    comparison_id: int,
    image: UploadFile = File(..., description="餐后食物图片"),
    db: Session = Depends(get_db)
):
    """
    上传餐后图片并计算净摄入量

    Phase 12: 餐后图片上传与对比计算接口

    接收餐后食物图片，调用AI对比餐前餐后图片，计算剩余比例和净摄入热量，
    更新MealComparison记录并返回对比结果。

    - **comparison_id**: 餐前上传时返回的对比记录ID
    - **image**: 餐后食物图片文件（支持jpg, jpeg, png格式）

    返回：
    - comparison_id: 对比记录ID
    - before_image_url: 餐前图片路径
    - after_image_url: 餐后图片路径
    - consumption_ratio: 消耗比例（0-1，1表示全部吃完）
    - original_calories: 原始估算热量
    - net_calories: 净摄入热量 = 原始热量 × 消耗比例
    - comparison_analysis: AI对比分析说明
    - status: 记录状态（completed表示对比完成）
    """
    return await food_service.upload_after_meal_image(db, comparison_id, image)
