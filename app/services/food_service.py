"""
Food API application services.
"""
import base64
import json
import os
import uuid
from collections import defaultdict
from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.crud import (
    diet_record_crud,
    meal_comparison_crud,
    menu_recognition_crud,
    user_crud,
)
from app.db_models.diet_record import DietRecord
from app.db_models.meal_comparison import MealComparison
from app.models.food import (
    FoodRequest,
    FoodResponse,
    FoodData,
    RecognizeMenuResponse,
    AddDietRecordRequest,
    UpdateDietRecordRequest,
    DietRecordsByDateResponse,
    ApiResponse,
    AllergenCheckRequest,
    AllergenCheckResponse,
    AllergenCategoriesResponse,
    RecommendationResponse,
)
from app.models.meal_comparison import BeforeMealUploadResponse, AfterMealUploadResponse
from app.services.ai_service import AIService
from app.services.allergen_service import allergen_service
from app.services.meal_comparison_service import meal_comparison_service
from app.services.recommendation_service import get_recommendation_service

# Initialize AI service
ai_service = AIService()

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "uploads",
    "meal",
)


def ensure_upload_dir() -> str:
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    return UPLOAD_DIR


def analyze_food(request: FoodRequest) -> FoodResponse:
    try:
        nutrition_data = ai_service.analyze_food_nutrition(request.food_name)
        food_data = FoodData(**nutrition_data)
        return FoodResponse(success=True, message="分析成功", data=food_data)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"服务配置错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


def recognize_menu(
    db: Session,
    image: UploadFile,
    user_id: Optional[str] = None,
) -> RecognizeMenuResponse:
    try:
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="请上传图片文件")

        health_goal = None
        user_id_int = None
        if user_id:
            try:
                user_id_int = int(user_id)
                user = user_crud.get_user_by_id(db, user_id_int)
                if user:
                    health_goal = user.health_goal
            except ValueError:
                pass

        dishes = ai_service.recognize_menu_image(image.file, health_goal)

        if user_id_int:
            try:
                menu_recognition_crud.create_menu_recognition(db, user_id_int, dishes)
            except Exception as e:
                db.rollback()
                print(f"警告: 保存识别结果失败: {str(e)}")

        return RecognizeMenuResponse(
            code=200,
            message="识别成功",
            data={"dishes": dishes},
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"请求参数错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别菜单失败: {str(e)}")


def get_latest_recognition(
    db: Session, user_id: Optional[int] = None
) -> RecognizeMenuResponse:
    try:
        latest = menu_recognition_crud.get_latest_menu_recognition(db, user_id)
        if not latest:
            return RecognizeMenuResponse(
                code=404,
                message="未找到识别记录",
                data={"dishes": []},
            )

        return RecognizeMenuResponse(
            code=200,
            message="获取成功",
            data={"dishes": latest.dishes},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


def add_diet_record(db: Session, request: AddDietRecordRequest) -> ApiResponse:
    try:
        user = user_crud.get_user_by_id(db, request.userId)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        meal_type_map = {
            "早餐": "breakfast",
            "午餐": "lunch",
            "晚餐": "dinner",
            "加餐": "snack",
            "breakfast": "breakfast",
            "lunch": "lunch",
            "dinner": "dinner",
            "snack": "snack",
        }
        meal_type = meal_type_map.get(request.mealType, request.mealType)

        try:
            record_date = datetime.strptime(request.recordDate, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式"
            )

        diet_record = DietRecord(
            user_id=request.userId,
            food_name=request.foodName,
            calories=request.calories,
            protein=request.protein,
            fat=request.fat,
            carbs=request.carbs,
            meal_type=meal_type,
            record_date=record_date,
        )

        diet_record_crud.create_diet_record(db, diet_record)

        return ApiResponse(code=200, message="记录成功", data=None)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加记录失败: {str(e)}")


def get_diet_records(db: Session, user_id: int) -> DietRecordsByDateResponse:
    try:
        records = diet_record_crud.get_diet_records_by_user(db, user_id)

        records_by_date = defaultdict(list)
        for record in records:
            date_str = record.record_date.strftime("%Y-%m-%d")
            records_by_date[date_str].append(
                {
                    "id": record.id,
                    "userId": record.user_id,
                    "foodName": record.food_name,
                    "calories": record.calories,
                    "protein": record.protein or 0.0,
                    "fat": record.fat or 0.0,
                    "carbs": record.carbs or 0.0,
                    "mealType": record.meal_type or "",
                    "recordDate": date_str,
                    "createdAt": record.created_at.strftime("%Y-%m-%dT%H:%M:%S")
                    if record.created_at
                    else "",
                }
            )

        result = dict(sorted(records_by_date.items(), reverse=True))

        return DietRecordsByDateResponse(code=200, message="获取成功", data=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


def get_today_diet_records(db: Session, user_id: int) -> DietRecordsByDateResponse:
    try:
        today = date.today()
        records = diet_record_crud.get_diet_records_by_user_and_date(
            db, user_id, today
        )

        records_list = [
            {
                "id": record.id,
                "userId": record.user_id,
                "foodName": record.food_name,
                "calories": record.calories,
                "protein": record.protein or 0.0,
                "fat": record.fat or 0.0,
                "carbs": record.carbs or 0.0,
                "mealType": record.meal_type or "",
                "recordDate": record.record_date.strftime("%Y-%m-%d"),
                "createdAt": record.created_at.strftime("%Y-%m-%dT%H:%M:%S")
                if record.created_at
                else "",
            }
            for record in records
        ]

        date_str = today.strftime("%Y-%m-%d")
        result = {date_str: records_list}

        return DietRecordsByDateResponse(code=200, message="获取成功", data=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


def update_diet_record(
    db: Session, record_id: int, request: UpdateDietRecordRequest
) -> ApiResponse:
    try:
        record = diet_record_crud.get_diet_record_by_id(db, record_id)
        if not record:
            raise HTTPException(
                status_code=404, detail=f"饮食记录不存在，record_id: {record_id}"
            )

        if record.user_id != request.userId:
            raise HTTPException(status_code=403, detail="无权操作此记录，只能修改自己的饮食记录")

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
            meal_type_map = {
                "早餐": "breakfast",
                "午餐": "lunch",
                "晚餐": "dinner",
                "加餐": "snack",
                "breakfast": "breakfast",
                "lunch": "lunch",
                "dinner": "dinner",
                "snack": "snack",
            }
            record.meal_type = meal_type_map.get(request.mealType, request.mealType)
        if request.recordDate is not None:
            try:
                record.record_date = datetime.strptime(
                    request.recordDate, "%Y-%m-%d"
                ).date()
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式"
                )

        diet_record_crud.save_diet_record(db, record)

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
                "recordDate": record.record_date.strftime("%Y-%m-%d"),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


def delete_diet_record(db: Session, record_id: int, user_id: int) -> ApiResponse:
    try:
        record = diet_record_crud.get_diet_record_by_id(db, record_id)
        if not record:
            raise HTTPException(
                status_code=404, detail=f"饮食记录不存在，record_id: {record_id}"
            )

        if record.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权操作此记录，只能删除自己的饮食记录")

        diet_record_crud.delete_diet_record(db, record)

        return ApiResponse(code=200, message="删除成功", data=None)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


def check_allergens(request: AllergenCheckRequest) -> AllergenCheckResponse:
    try:
        result = allergen_service.check_allergens(
            food_name=request.food_name,
            ingredients=request.ingredients,
            user_allergens=request.user_allergens,
        )
        return AllergenCheckResponse(code=200, message="检测完成", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


def get_allergen_categories() -> AllergenCategoriesResponse:
    try:
        categories = allergen_service.get_all_categories()
        return AllergenCategoriesResponse(code=200, message="获取成功", data=categories)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


def get_food_recommendations(
    db: Session, user_id: int, meal_type: str, limit: int
) -> RecommendationResponse:
    try:
        recommendation_service = get_recommendation_service()
        result = recommendation_service.get_recommendations(
            db=db, user_id=user_id, meal_type=meal_type, limit=limit
        )
        return RecommendationResponse(code=200, message="推荐成功", data=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推荐失败: {str(e)}")


async def upload_before_meal_image(
    db: Session, image: UploadFile, user_id: int
) -> BeforeMealUploadResponse:
    try:
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, detail="请上传图片文件（支持jpg, jpeg, png格式）"
            )

        user = user_crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"用户不存在，user_id: {user_id}")

        upload_dir = ensure_upload_dir()

        file_ext = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
        if not file_ext:
            file_ext = ".jpg"
        unique_filename = f"before_{user_id}_{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)

        if hasattr(image.file, "seek"):
            image.file.seek(0)
        image_bytes = await image.read()

        with open(file_path, "wb") as f:
            f.write(image_bytes)

        relative_path = f"/uploads/meal/{unique_filename}"
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        try:
            before_features = ai_service.extract_before_meal_features(image_base64)
        except Exception as ai_error:
            print(f"AI特征提取失败，使用默认值: {str(ai_error)}")
            before_features = {
                "dishes": [],
                "total_estimated_calories": 0,
                "total_estimated_protein": 0,
                "total_estimated_fat": 0,
                "total_estimated_carbs": 0,
            }

        meal_comparison = MealComparison(
            user_id=user_id,
            before_image_url=relative_path,
            before_features=json.dumps(before_features, ensure_ascii=False),
            original_calories=before_features.get("total_estimated_calories", 0),
            original_protein=before_features.get("total_estimated_protein", 0),
            original_fat=before_features.get("total_estimated_fat", 0),
            original_carbs=before_features.get("total_estimated_carbs", 0),
            status="pending_after",
        )
        meal_comparison = meal_comparison_crud.create_meal_comparison(
            db, meal_comparison
        )

        return BeforeMealUploadResponse(
            code=200,
            message="餐前图片上传成功",
            data={
                "comparison_id": meal_comparison.id,
                "before_image_url": relative_path,
                "before_features": before_features,
                "status": "pending_after",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"餐前图片上传失败: {str(e)}")


async def upload_after_meal_image(
    db: Session, comparison_id: int, image: UploadFile
) -> AfterMealUploadResponse:
    try:
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, detail="请上传图片文件（支持jpg, jpeg, png格式）"
            )

        comparison = meal_comparison_crud.get_meal_comparison_by_id(
            db, comparison_id
        )
        if not comparison:
            raise HTTPException(
                status_code=404, detail=f"对比记录不存在，comparison_id: {comparison_id}"
            )

        if comparison.status == "completed":
            raise HTTPException(status_code=400, detail="该对比记录已完成，请勿重复上传")
        if comparison.status != "pending_after":
            raise HTTPException(
                status_code=400, detail=f"对比记录状态异常: {comparison.status}"
            )

        upload_dir = ensure_upload_dir()

        file_ext = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
        if not file_ext:
            file_ext = ".jpg"
        unique_filename = (
            f"after_{comparison.user_id}_{comparison_id}_{uuid.uuid4().hex}{file_ext}"
        )
        file_path = os.path.join(upload_dir, unique_filename)

        if hasattr(image.file, "seek"):
            image.file.seek(0)
        after_image_bytes = await image.read()

        with open(file_path, "wb") as f:
            f.write(after_image_bytes)

        after_relative_path = f"/uploads/meal/{unique_filename}"
        after_image_base64 = base64.b64encode(after_image_bytes).decode("utf-8")

        before_image_base64 = None
        before_features = {}
        if comparison.before_image_url:
            before_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                comparison.before_image_url.lstrip("/"),
            )
            if os.path.exists(before_file_path):
                with open(before_file_path, "rb") as f:
                    before_image_base64 = base64.b64encode(f.read()).decode("utf-8")

        if comparison.before_features:
            try:
                before_features = json.loads(comparison.before_features)
            except json.JSONDecodeError:
                before_features = {}

        comparison_result = None
        try:
            if before_image_base64:
                comparison_result = ai_service.compare_before_after_meal(
                    before_image_base64, after_image_base64, before_features
                )
            else:
                comparison_result = {
                    "dishes": [],
                    "overall_remaining_ratio": 0.5,
                    "consumption_ratio": 0.5,
                    "comparison_analysis": "无法读取餐前图片，默认估算您吃掉了约50%的食物。",
                }
        except Exception as ai_error:
            print(f"AI对比失败，使用默认值: {str(ai_error)}")
            comparison_result = {
                "dishes": [],
                "overall_remaining_ratio": 0.25,
                "consumption_ratio": 0.75,
                "comparison_analysis": "AI分析暂时不可用，默认估算您吃掉了约75%的食物。",
            }

        consumption_ratio = comparison_result.get("consumption_ratio", 0.75)
        after_features = {
            "dishes": comparison_result.get("dishes", []),
            "overall_remaining_ratio": comparison_result.get("overall_remaining_ratio", 0.25),
        }
        comparison_analysis = comparison_result.get("comparison_analysis", "对比完成")

        updated_comparison = meal_comparison_service.update_comparison_with_after_meal(
            db=db,
            comparison=comparison,
            after_image_url=after_relative_path,
            after_features=after_features,
            consumption_ratio=consumption_ratio,
            comparison_analysis=comparison_analysis,
        )

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
                "status": updated_comparison.status,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"餐后图片上传失败: {str(e)}")
