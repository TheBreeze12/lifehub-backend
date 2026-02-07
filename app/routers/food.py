"""
食物相关API路由
"""
from fastapi import APIRouter, HTTPException, File, UploadFile, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import date, datetime
from collections import defaultdict
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
from app.services.meal_comparison_service import meal_comparison_service
from app.db_models.meal_comparison import MealComparison
import os
import uuid
import base64
import json as json_module
from app.db_models.diet_record import DietRecord
from app.services.ai_service import AIService
from app.services.allergen_service import allergen_service
from app.services.recommendation_service import get_recommendation_service
from app.database import get_db
from app.db_models.user import User
from app.db_models.menu_recognition import MenuRecognition

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
    userId: Optional[str] = Form(None, description="用户ID（可选）"),
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
        user_id_int = None
        if userId:
            try:
                user_id_int = int(userId)
                user = db.query(User).filter(User.id == user_id_int).first()
                if user:
                    health_goal = user.health_goal
            except ValueError:
                pass
        
        # 调用AI服务识别菜单
        dishes = ai_service.recognize_menu_image(image.file, health_goal)
        
        # 保存识别结果到数据库（如果提供了userId）
        if user_id_int:
            try:
                # 创建新的识别记录
                recognition = MenuRecognition(
                    user_id=user_id_int,
                    dishes=dishes
                )
                db.add(recognition)
                db.commit()
                print(f"✓ 已保存用户 {user_id_int} 的识别结果，共 {len(dishes)} 个菜品")
            except Exception as e:
                print(f"警告: 保存识别结果失败: {str(e)}")
                db.rollback()
                # 即使保存失败，也返回识别结果
        
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


@router.get("/latest-recognition")
async def get_latest_recognition(
    userId: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    获取用户最新的菜单识别结果
    
    - **userId**: 用户ID（可选）
    """
    try:
        # 查询最新的识别记录
        query = db.query(MenuRecognition)
        if userId:
            query = query.filter(MenuRecognition.user_id == userId)
        
        latest = query.order_by(MenuRecognition.created_at.desc()).first()
        
        if not latest:
            return RecognizeMenuResponse(
                code=404,
                message="未找到识别记录",
                data={"dishes": []}
            )
        
        return RecognizeMenuResponse(
            code=200,
            message="获取成功",
            data={"dishes": latest.dishes}
        )
        
    except Exception as e:
        print(f"获取最新识别结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


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
    try:
        # 验证用户是否存在
        user = db.query(User).filter(User.id == request.userId).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 转换餐次格式（中文转英文）
        meal_type_map = {
            "早餐": "breakfast",
            "午餐": "lunch",
            "晚餐": "dinner",
            "加餐": "snack",
            "breakfast": "breakfast",
            "lunch": "lunch",
            "dinner": "dinner",
            "snack": "snack"
        }
        meal_type = meal_type_map.get(request.mealType, request.mealType)
        
        # 解析日期
        try:
            record_date = datetime.strptime(request.recordDate, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式")
        
        # 创建饮食记录
        diet_record = DietRecord(
            user_id=request.userId,
            food_name=request.foodName,
            calories=request.calories,
            protein=request.protein,
            fat=request.fat,
            carbs=request.carbs,
            meal_type=meal_type,
            record_date=record_date
        )
        
        db.add(diet_record)
        db.commit()
        db.refresh(diet_record)
        
        print(f"✓ 已添加用户 {request.userId} 的饮食记录: {request.foodName}")
        
        return ApiResponse(
            code=200,
            message="记录成功",
            data=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"添加饮食记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加记录失败: {str(e)}")


@router.get("/records", response_model=DietRecordsByDateResponse)
async def get_diet_records(
    userId: int,
    db: Session = Depends(get_db)
):
    """
    获取用户所有饮食记录，按日期划分
    
    - **userId**: 用户ID
    """
    try:
        # 查询用户的所有饮食记录
        records = db.query(DietRecord).filter(
            DietRecord.user_id == userId
        ).order_by(desc(DietRecord.record_date), desc(DietRecord.created_at)).all()
        
        # 按日期分组
        records_by_date = defaultdict(list)
        for record in records:
            date_str = record.record_date.strftime("%Y-%m-%d")
            records_by_date[date_str].append({
                "id": record.id,
                "userId": record.user_id,
                "foodName": record.food_name,
                "calories": record.calories,
                "protein": record.protein or 0.0,
                "fat": record.fat or 0.0,
                "carbs": record.carbs or 0.0,
                "mealType": record.meal_type or "",
                "recordDate": date_str,
                "createdAt": record.created_at.strftime("%Y-%m-%dT%H:%M:%S") if record.created_at else ""
            })
        
        # 转换为普通字典并按日期排序（最新的在前）
        result = dict(sorted(records_by_date.items(), reverse=True))
        
        return DietRecordsByDateResponse(
            code=200,
            message="获取成功",
            data=result
        )
        
    except Exception as e:
        print(f"获取饮食记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.get("/records/today", response_model=DietRecordsByDateResponse)
async def get_today_diet_records(
    userId: int,
    db: Session = Depends(get_db)
):
    """
    获取用户今天的饮食记录
    
    - **userId**: 用户ID
    """
    try:
        today = date.today()
        
        # 查询今天的饮食记录
        records = db.query(DietRecord).filter(
            DietRecord.user_id == userId,
            DietRecord.record_date == today
        ).order_by(DietRecord.created_at).all()
        
        # 转换为列表格式
        records_list = [{
            "id": record.id,
            "userId": record.user_id,
            "foodName": record.food_name,
            "calories": record.calories,
            "protein": record.protein or 0.0,
            "fat": record.fat or 0.0,
            "carbs": record.carbs or 0.0,
            "mealType": record.meal_type or "",
            "recordDate": record.record_date.strftime("%Y-%m-%d"),
            "createdAt": record.created_at.strftime("%Y-%m-%dT%H:%M:%S") if record.created_at else ""
        } for record in records]
        
        # 按日期分组（虽然只有今天，但保持格式一致）
        date_str = today.strftime("%Y-%m-%d")
        result = {date_str: records_list}
        
        return DietRecordsByDateResponse(
            code=200,
            message="获取成功",
            data=result
        )
        
    except Exception as e:
        print(f"获取今日饮食记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


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
    try:
        # 查询记录是否存在
        record = db.query(DietRecord).filter(DietRecord.id == record_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"饮食记录不存在，record_id: {record_id}")
        
        # 权限校验：只能操作自己的记录
        if record.user_id != request.userId:
            raise HTTPException(status_code=403, detail="无权操作此记录，只能修改自己的饮食记录")
        
        # 更新字段（只更新非None的字段）
        if request.foodName is not None:
            record.food_name = request.foodName
        if request.calories is not None:
            record.calories = request.calories
        if request.protein is not None:
            record.protein = request.protein
        if request.fat is not None:
            record.fat = request.fat
        if request.carbs is not None:
            record.carbs = request.carbs
        if request.mealType is not None:
            # 转换餐次格式（中文转英文）
            meal_type_map = {
                "早餐": "breakfast",
                "午餐": "lunch",
                "晚餐": "dinner",
                "加餐": "snack",
                "breakfast": "breakfast",
                "lunch": "lunch",
                "dinner": "dinner",
                "snack": "snack"
            }
            record.meal_type = meal_type_map.get(request.mealType, request.mealType)
        if request.recordDate is not None:
            try:
                record.record_date = datetime.strptime(request.recordDate, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式")
        
        db.commit()
        db.refresh(record)
        
        print(f"✓ 已更新用户 {request.userId} 的饮食记录 {record_id}: {record.food_name}")
        
        return ApiResponse(
            code=200,
            message="更新成功",
            data={
                "id": record.id,
                "foodName": record.food_name,
                "calories": record.calories,
                "protein": record.protein or 0.0,
                "fat": record.fat or 0.0,
                "carbs": record.carbs or 0.0,
                "mealType": record.meal_type or "",
                "recordDate": record.record_date.strftime("%Y-%m-%d")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"更新饮食记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


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
    try:
        # 查询记录是否存在
        record = db.query(DietRecord).filter(DietRecord.id == record_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"饮食记录不存在，record_id: {record_id}")
        
        # 权限校验：只能操作自己的记录
        if record.user_id != userId:
            raise HTTPException(status_code=403, detail="无权操作此记录，只能删除自己的饮食记录")
        
        # 保存记录信息用于日志
        food_name = record.food_name
        
        # 删除记录
        db.delete(record)
        db.commit()
        
        print(f"✓ 已删除用户 {userId} 的饮食记录 {record_id}: {food_name}")
        
        return ApiResponse(
            code=200,
            message="删除成功",
            data=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"删除饮食记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


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
    try:
        # 调用过敏原检测服务
        result = allergen_service.check_allergens(
            food_name=request.food_name,
            ingredients=request.ingredients,
            user_allergens=request.user_allergens
        )
        
        print(f"✓ 过敏原检测完成: {request.food_name}, 检测到 {result['allergen_count']} 种过敏原")
        
        return AllergenCheckResponse(
            code=200,
            message="检测完成",
            data=result
        )
        
    except Exception as e:
        print(f"过敏原检测失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


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
    try:
        categories = allergen_service.get_all_categories()
        
        return AllergenCategoriesResponse(
            code=200,
            message="获取成功",
            data=categories
        )
        
    except Exception as e:
        print(f"获取过敏原类别失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


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
    try:
        recommendation_service = get_recommendation_service()
        result = recommendation_service.get_recommendations(
            db=db,
            user_id=user_id,
            meal_type=meal_type,
            limit=limit
        )
        
        print(f"✓ 用户 {user_id} 的{meal_type}推荐完成，共 {len(result.recommendations)} 道菜品")
        
        return RecommendationResponse(
            code=200,
            message="推荐成功",
            data=result
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"个性化推荐失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"推荐失败: {str(e)}")


# ==================== 餐前餐后对比接口 (Phase 11) ====================

# 图片上传目录配置
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "meal")


def ensure_upload_dir():
    """确保上传目录存在"""
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    return UPLOAD_DIR


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
    try:
        # 验证文件类型
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件（支持jpg, jpeg, png格式）")
        
        # 验证用户是否存在
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"用户不存在，user_id: {user_id}")
        
        # 确保上传目录存在
        upload_dir = ensure_upload_dir()
        
        # 生成唯一文件名
        file_ext = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
        if not file_ext:
            file_ext = ".jpg"
        unique_filename = f"before_{user_id}_{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # 读取图片内容
        if hasattr(image.file, 'seek'):
            image.file.seek(0)
        image_bytes = await image.read()
        
        # 保存图片到本地
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
        # 相对路径（用于存储到数据库）
        relative_path = f"/uploads/meal/{unique_filename}"
        
        # 将图片转换为base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # 调用AI服务提取餐前图片特征
        try:
            before_features = ai_service.extract_before_meal_features(image_base64)
        except Exception as ai_error:
            print(f"AI特征提取失败，使用默认值: {str(ai_error)}")
            # AI调用失败时返回空特征
            before_features = {
                "dishes": [],
                "total_estimated_calories": 0,
                "total_estimated_protein": 0,
                "total_estimated_fat": 0,
                "total_estimated_carbs": 0
            }
        
        # 创建MealComparison记录
        meal_comparison = MealComparison(
            user_id=user_id,
            before_image_url=relative_path,
            before_features=json_module.dumps(before_features, ensure_ascii=False),
            original_calories=before_features.get("total_estimated_calories", 0),
            original_protein=before_features.get("total_estimated_protein", 0),
            original_fat=before_features.get("total_estimated_fat", 0),
            original_carbs=before_features.get("total_estimated_carbs", 0),
            status="pending_after"
        )
        
        db.add(meal_comparison)
        db.commit()
        db.refresh(meal_comparison)
        
        print(f"✓ 已创建用户 {user_id} 的餐前对比记录，comparison_id: {meal_comparison.id}")
        
        return BeforeMealUploadResponse(
            code=200,
            message="餐前图片上传成功",
            data={
                "comparison_id": meal_comparison.id,
                "before_image_url": relative_path,
                "before_features": before_features,
                "status": "pending_after"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"餐前图片上传失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"餐前图片上传失败: {str(e)}")


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
    try:
        # 验证文件类型
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件（支持jpg, jpeg, png格式）")
        
        # 查询对比记录是否存在
        comparison = db.query(MealComparison).filter(MealComparison.id == comparison_id).first()
        if not comparison:
            raise HTTPException(status_code=404, detail=f"对比记录不存在，comparison_id: {comparison_id}")
        
        # 检查状态
        if comparison.status == "completed":
            raise HTTPException(status_code=400, detail="该对比记录已完成，请勿重复上传")
        
        if comparison.status != "pending_after":
            raise HTTPException(status_code=400, detail=f"对比记录状态异常: {comparison.status}")
        
        # 确保上传目录存在
        upload_dir = ensure_upload_dir()
        
        # 生成唯一文件名
        file_ext = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
        if not file_ext:
            file_ext = ".jpg"
        unique_filename = f"after_{comparison.user_id}_{comparison_id}_{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # 读取图片内容
        if hasattr(image.file, 'seek'):
            image.file.seek(0)
        after_image_bytes = await image.read()
        
        # 保存图片到本地
        with open(file_path, "wb") as f:
            f.write(after_image_bytes)
        
        # 相对路径
        after_relative_path = f"/uploads/meal/{unique_filename}"
        
        # 将餐后图片转换为base64
        after_image_base64 = base64.b64encode(after_image_bytes).decode('utf-8')
        
        # 读取餐前图片用于对比
        before_image_base64 = None
        before_features = {}
        
        if comparison.before_image_url:
            before_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                comparison.before_image_url.lstrip('/')
            )
            if os.path.exists(before_file_path):
                with open(before_file_path, "rb") as f:
                    before_image_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        # 解析餐前特征
        if comparison.before_features:
            try:
                before_features = json_module.loads(comparison.before_features)
            except json_module.JSONDecodeError:
                before_features = {}
        
        # 调用AI服务对比餐前餐后图片
        comparison_result = None
        try:
            if before_image_base64:
                comparison_result = ai_service.compare_before_after_meal(
                    before_image_base64,
                    after_image_base64,
                    before_features
                )
            else:
                # 如果没有餐前图片，默认假设吃掉了一半
                comparison_result = {
                    "dishes": [],
                    "overall_remaining_ratio": 0.5,
                    "consumption_ratio": 0.5,
                    "comparison_analysis": "无法读取餐前图片，默认估算您吃掉了约50%的食物。"
                }
        except Exception as ai_error:
            print(f"AI对比失败，使用默认值: {str(ai_error)}")
            comparison_result = {
                "dishes": [],
                "overall_remaining_ratio": 0.25,
                "consumption_ratio": 0.75,
                "comparison_analysis": "AI分析暂时不可用，默认估算您吃掉了约75%的食物。"
            }
        
        # 提取对比结果
        consumption_ratio = comparison_result.get("consumption_ratio", 0.75)
        after_features = {
            "dishes": comparison_result.get("dishes", []),
            "overall_remaining_ratio": comparison_result.get("overall_remaining_ratio", 0.25)
        }
        comparison_analysis = comparison_result.get("comparison_analysis", "对比完成")
        
        # 使用meal_comparison_service更新记录
        updated_comparison = meal_comparison_service.update_comparison_with_after_meal(
            db=db,
            comparison=comparison,
            after_image_url=after_relative_path,
            after_features=after_features,
            consumption_ratio=consumption_ratio,
            comparison_analysis=comparison_analysis
        )
        
        print(f"✓ 用户 {comparison.user_id} 的餐后对比完成，comparison_id: {comparison_id}, 消耗比例: {consumption_ratio:.2%}")
        
        # 构建响应
        return AfterMealUploadResponse(
            code=200,
            message="餐后图片上传成功，对比完成",
            data={
                "comparison_id": updated_comparison.id,
                "before_image_url": updated_comparison.before_image_url,
                "after_image_url": updated_comparison.after_image_url,
                "consumption_ratio": updated_comparison.consumption_ratio,
                "original_calories": updated_comparison.original_calories,
                "net_calories": updated_comparison.net_calories,
                "original_protein": updated_comparison.original_protein,
                "original_fat": updated_comparison.original_fat,
                "original_carbs": updated_comparison.original_carbs,
                "net_protein": updated_comparison.net_protein,
                "net_fat": updated_comparison.net_fat,
                "net_carbs": updated_comparison.net_carbs,
                "comparison_analysis": updated_comparison.comparison_analysis,
                "status": updated_comparison.status
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"餐后图片上传失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"餐后图片上传失败: {str(e)}")

