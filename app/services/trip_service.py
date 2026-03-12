"""
Trip API application services.
"""
from datetime import datetime, date, time
from typing import List

from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.crud import (
    diet_record_crud,
    trip_item_crud,
    trip_plan_crud,
    user_crud,
)
from app.db_models.trip_plan import TripPlan
from app.db_models.trip_item import TripItem
from app.models.trip import (
    GenerateTripRequest,
    GenerateTripResponse,
    TripData,
    TripItemData,
    TripListResponse,
    TripSummary,
    TripDetailResponse,
    GenerateRoutesRequest,
    GenerateRoutesResponse,
    RoutesResponseData,
    ParetoRoute,
    RouteWaypoint,
    PlanBResponse,
    PlanBData,
    PlanBAlternative,
    WeatherAssessment,
    OfflinePackageRequest,
    OfflinePackageResponse,
    OfflinePackageData,
    TileBounds,
)
from app.services.ai_service import AIService
from app.services.mets_service import METsService
from app.services.route_optimization_service import get_route_optimization_service
from app.services.weather_service import WeatherService,get_weather_service
from app.services.offline_package_service import OfflinePackageService

ai_service = AIService()
mets_service = METsService()
weather_service = get_weather_service()
offline_package_service = OfflinePackageService()


def generate_trip(db: Session, request: GenerateTripRequest) -> GenerateTripResponse:
    try:
        preferences_dict = None
        if request.preferences:
            preferences_dict = {
                "healthGoal": request.preferences.healthGoal,
                "allergens": request.preferences.allergens or [],
            }

        user = user_crud.get_user_by_id(db, request.userId)
        user_weight = (
            user.weight if user and user.weight else mets_service.DEFAULT_WEIGHT_KG
        )

        today = date.today()
        today_records = diet_record_crud.get_diet_records_by_user_and_date(
            db, request.userId, today
        )
        total_calories_intake = sum(record.calories for record in today_records)

        user_location = None
        if request.latitude is not None and request.longitude is not None:
            user_location = {"latitude": request.latitude, "longitude": request.longitude}

        trip_data = ai_service.generate_trip(
            query=request.query,
            preferences=preferences_dict,
            calories_intake=total_calories_intake,
            user_location=user_location,
        )

        start_date = datetime.strptime(trip_data["startDate"], "%Y-%m-%d").date()
        end_date = datetime.strptime(trip_data["endDate"], "%Y-%m-%d").date()

        trip_plan = TripPlan(
            user_id=request.userId,
            title=trip_data.get("title", "行程计划"),
            destination=trip_data.get("destination"),
            latitude=user_location.get("latitude") if user_location else None,
            longitude=user_location.get("longitude") if user_location else None,
            start_date=start_date,
            end_date=end_date,
            travelers=trip_data.get("travelers", ["本人"]),
            status="planning",
        )

        trip_plan = trip_plan_crud.create_trip_plan(db, trip_plan)

        items = trip_data.get("items", [])
        for index, item_data in enumerate(items):
            start_time_obj = None
            if item_data.get("startTime"):
                try:
                    time_parts = item_data["startTime"].split(":")
                    start_time_obj = time(int(time_parts[0]), int(time_parts[1]))
                except Exception:
                    pass

            exercise_type = item_data.get("placeType") or "walking"
            duration_minutes = item_data.get("duration") or 0

            calories_burned = mets_service.calculate_calories(
                exercise_type=exercise_type,
                weight_kg=user_weight,
                duration_minutes=duration_minutes,
            )

            mets_value = mets_service.get_mets_value(exercise_type)
            original_notes = item_data.get("notes") or ""
            mets_note = (
                f"[METs={mets_value}, 体重={user_weight}kg, 时长={duration_minutes}分钟]"
            )
            enhanced_notes = f"{original_notes} {mets_note}" if original_notes else mets_note

            trip_item = TripItem(
                trip_id=trip_plan.id,
                day_index=item_data.get("dayIndex", 1),
                start_time=start_time_obj,
                place_name=item_data.get("placeName", ""),
                place_type=item_data.get("placeType"),
                duration=item_data.get("duration"),
                cost=calories_burned,
                notes=enhanced_notes,
                sort_order=index,
            )
            trip_item_crud.create_trip_item(db, trip_item)
        trip_plan = trip_plan_crud.save_trip_plan(db, trip_plan)

        trip_items = trip_item_crud.get_trip_items_by_trip_id_simple(db, trip_plan.id)

        items_data = []
        for item in trip_items:
            start_time_str = item.start_time.strftime("%H:%M") if item.start_time else None

            exercise_type = item.place_type or "walking"
            mets_value = mets_service.get_mets_value(exercise_type)
            duration_hours = (item.duration or 0) / 60.0
            calculation_basis = (
                f"METs={mets_value} × {user_weight}kg × {duration_hours:.2f}h"
            )

            items_data.append(
                TripItemData(
                    dayIndex=item.day_index,
                    startTime=start_time_str,
                    placeName=item.place_name,
                    placeType=item.place_type,
                    duration=item.duration,
                    cost=item.cost,
                    notes=item.notes,
                    metsValue=mets_value,
                    calculationBasis=calculation_basis,
                )
            )

        trip_response = TripData(
            tripId=trip_plan.id,
            title=trip_plan.title,
            destination=trip_plan.destination,
            startDate=trip_plan.start_date.strftime("%Y-%m-%d"),
            endDate=trip_plan.end_date.strftime("%Y-%m-%d"),
            items=items_data,
        )

        return GenerateTripResponse(code=200, message="运动计划生成成功", data=trip_response)

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"请求参数错误: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"生成运动计划失败: {str(e)}")


def _trip_plan_to_summary(trip_plan: TripPlan, item_count: int = 0) -> TripSummary:
    return TripSummary(
        tripId=trip_plan.id,
        title=trip_plan.title,
        destination=trip_plan.destination,
        startDate=trip_plan.start_date.strftime("%Y-%m-%d"),
        endDate=trip_plan.end_date.strftime("%Y-%m-%d"),
        status=trip_plan.status,
        itemCount=item_count,
    )


def _trip_plan_to_data(
    trip_plan: TripPlan, trip_items: List[TripItem], user_weight: float = 70.0
) -> TripData:
    items_data = []
    for item in trip_items:
        start_time_str = item.start_time.strftime("%H:%M") if item.start_time else None

        exercise_type = item.place_type or "walking"
        mets_value = mets_service.get_mets_value(exercise_type)
        duration_hours = (item.duration or 0) / 60.0
        calculation_basis = (
            f"METs={mets_value} × {user_weight}kg × {duration_hours:.2f}h"
        )

        items_data.append(
            TripItemData(
                dayIndex=item.day_index,
                startTime=start_time_str,
                placeName=item.place_name,
                placeType=item.place_type,
                duration=item.duration,
                cost=item.cost,
                notes=item.notes,
                metsValue=mets_value,
                calculationBasis=calculation_basis,
            )
        )

    return TripData(
        tripId=trip_plan.id,
        title=trip_plan.title,
        destination=trip_plan.destination,
        startDate=trip_plan.start_date.strftime("%Y-%m-%d"),
        endDate=trip_plan.end_date.strftime("%Y-%m-%d"),
        items=items_data,
    )


def get_trip_list(db: Session, user_id: int) -> TripListResponse:
    try:
        trip_plans = trip_plan_crud.get_trip_plans_by_user(db, user_id)

        trip_summaries = []
        for trip_plan in trip_plans:
            item_count = trip_item_crud.count_trip_items_by_trip_id(db, trip_plan.id)
            trip_summaries.append(_trip_plan_to_summary(trip_plan, item_count))

        return TripListResponse(code=200, message="获取成功", data=trip_summaries)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取行程列表失败: {str(e)}")


def get_recent_trips(db: Session, user_id: int, limit: int = 5) -> TripListResponse:
    try:
        trip_plans = trip_plan_crud.get_trip_plans_by_user_limit(db, user_id, limit)

        trip_summaries = []
        for trip_plan in trip_plans:
            item_count = trip_item_crud.count_trip_items_by_trip_id(db, trip_plan.id)
            trip_summaries.append(_trip_plan_to_summary(trip_plan, item_count))

        return TripListResponse(code=200, message="获取成功", data=trip_summaries)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最近行程失败: {str(e)}")


def get_home_trips(db: Session, user_id: int, limit: int = 3) -> TripListResponse:
    try:
        trip_plans = trip_plan_crud.get_trip_plans_by_user_limit(db, user_id, limit)

        trip_summaries = []
        for trip_plan in trip_plans:
            item_count = trip_item_crud.count_trip_items_by_trip_id(db, trip_plan.id)
            trip_summaries.append(_trip_plan_to_summary(trip_plan, item_count))

        return TripListResponse(code=200, message="获取成功", data=trip_summaries)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取首页行程失败: {str(e)}")


def get_plan_b(db: Session, plan_id: int) -> PlanBResponse:
    try:
        trip_plan = trip_plan_crud.get_trip_plan_by_id(db, plan_id)
        if not trip_plan:
            raise HTTPException(status_code=404, detail=f"运动计划不存在，plan_id: {plan_id}")

        user = user_crud.get_user_by_id(db, trip_plan.user_id)
        user_weight = (
            user.weight if user and user.weight else mets_service.DEFAULT_WEIGHT_KG
        )

        weather_data = None
        try:
            if trip_plan.latitude is not None and trip_plan.longitude is not None:
                weather_data = ai_service.get_weather_by_coords(
                    trip_plan.latitude,
                    trip_plan.longitude,
                    address_hint=trip_plan.destination,
                )
            elif trip_plan.destination:
                weather_data = ai_service.get_weather_by_address(trip_plan.destination)
        except Exception as weather_err:
            print(f"获取天气失败: {weather_err}")

        weather_eval = weather_service.evaluate_weather(weather_data)

        weather_assessment = WeatherAssessment(
            is_bad_weather=weather_eval["is_bad_weather"],
            severity=weather_eval["severity"],
            description=weather_eval.get("description", ""),
            temperature=weather_data.get("temperature") if weather_data else None,
            windspeed=weather_data.get("windspeed") if weather_data else None,
            weathercode=weather_data.get("weathercode") if weather_data else None,
            recommendation=weather_eval.get("recommendation", ""),
            warnings=weather_eval.get("warnings"),
        )

        trip_items = trip_item_crud.get_trip_items_by_trip_id_simple(db, plan_id)

        original_items = []
        original_total_calories = 0.0
        for item in trip_items:
            item_dict = {
                "place_name": item.place_name,
                "place_type": item.place_type,
                "duration": item.duration or 0,
                "cost": item.cost or 0.0,
            }
            original_items.append(item_dict)
            original_total_calories += item.cost or 0.0

        need_plan_b = weather_eval["is_bad_weather"]
        alternatives = []
        plan_b_total_calories = 0.0
        reason = ""

        if need_plan_b:
            plan_b_result = weather_service.generate_plan_b(
                original_items, weight_kg=user_weight
            )
            reason = (
                f"当前天气：{weather_eval.get('description', '不佳')}，"
                f"{weather_eval.get('recommendation', '建议改为室内运动')}"
            )

            for alt in plan_b_result.get("alternatives", []):
                alternatives.append(
                    PlanBAlternative(
                        exercise_name=alt["exercise_name"],
                        exercise_type=alt["exercise_type"],
                        duration=alt["duration"],
                        calories=alt["calories"],
                        is_indoor=alt["is_indoor"],
                        description=alt["description"],
                        mets_value=alt.get("mets_value"),
                    )
                )
            plan_b_total_calories = plan_b_result.get("plan_b_total_calories", 0.0)
        else:
            reason = "当前天气适合户外运动，无需替代方案"

        plan_b_data = PlanBData(
            plan_id=plan_id,
            weather=weather_assessment,
            need_plan_b=need_plan_b,
            original_calories=round(original_total_calories, 1),
            alternatives=alternatives,
            plan_b_total_calories=round(plan_b_total_calories, 1),
            reason=reason,
        )

        message = "已生成室内替代方案" if need_plan_b else "天气良好，无需替代方案"
        return PlanBResponse(code=200, message=message, data=plan_b_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Plan B失败: {str(e)}")


def get_trip_detail(db: Session, trip_id: int) -> TripDetailResponse:
    try:
        trip_plan = trip_plan_crud.get_trip_plan_by_id(db, trip_id)
        if not trip_plan:
            raise HTTPException(status_code=404, detail=f"行程不存在，tripId: {trip_id}")

        user = user_crud.get_user_by_id(db, trip_plan.user_id)
        user_weight = (
            user.weight if user and user.weight else mets_service.DEFAULT_WEIGHT_KG
        )

        trip_items = trip_item_crud.get_trip_items_by_trip_id(db, trip_id)

        trip_data = _trip_plan_to_data(trip_plan, trip_items, user_weight)

        return TripDetailResponse(code=200, message="获取成功", data=trip_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取行程详情失败: {str(e)}")


def generate_pareto_routes(request: GenerateRoutesRequest) -> GenerateRoutesResponse:
    try:
        route_service = get_route_optimization_service()
        result = route_service.generate_pareto_routes(
            start_point=(request.start_lat, request.start_lng),
            target_calories=request.target_calories,
            max_time_minutes=request.max_time_minutes or 60,
            exercise_type=request.exercise_type or "walking",
            weight_kg=request.weight_kg or 70.0,
        )

        routes_data = []
        for route in result.get("routes", []):
            waypoints = []
            for wp in route.get("waypoints", []):
                waypoints.append(
                    RouteWaypoint(
                        lat=wp["lat"],
                        lng=wp["lng"],
                        order=wp.get("order", 0),
                        type=wp.get("type", "waypoint"),
                    )
                )

            routes_data.append(
                ParetoRoute(
                    route_id=route["route_id"],
                    route_name=route["route_name"],
                    time_minutes=route["time_minutes"],
                    calories_burn=route["calories_burn"],
                    greenery_score=min(route["greenery_score"], 100),
                    distance_meters=route["distance_meters"],
                    waypoints=waypoints,
                    exercise_type=route.get("exercise_type"),
                    intensity=route.get("intensity"),
                )
            )

        response_data = RoutesResponseData(
            routes=routes_data,
            start_point=RouteWaypoint(
                lat=request.start_lat, lng=request.start_lng, order=0, type="start"
            ),
            target_calories=request.target_calories,
            max_time_minutes=request.max_time_minutes or 60,
            exercise_type=request.exercise_type or "walking",
            weight_kg=request.weight_kg or 70.0,
            n_routes=len(routes_data),
        )

        return GenerateRoutesResponse(
            code=200, message="帕累托最优路径生成成功", data=response_data
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"请求参数错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成帕累托路径失败: {str(e)}")


def generate_offline_package(
    db: Session, request: OfflinePackageRequest
) -> OfflinePackageResponse:
    try:
        trip_plan = trip_plan_crud.get_trip_plan_by_id(db, request.plan_id)
        if not trip_plan:
            raise HTTPException(
                status_code=404, detail=f"运动计划不存在，plan_id: {request.plan_id}"
            )

        trip_items = trip_item_crud.get_trip_items_by_trip_id_simple(
            db, request.plan_id
        )

        result = offline_package_service.generate_package(trip_plan, trip_items)

        trip_plan.is_offline = 1
        trip_plan.offline_size = result["file_size"]
        trip_plan_crud.save_trip_plan(db, trip_plan)

        pkg_info = offline_package_service.get_package_info(result["package_id"])
        tile_bounds_data = None
        if pkg_info and pkg_info.get("tile_bounds"):
            tb = pkg_info["tile_bounds"]
            if tb.get("min_lat") != 0 or tb.get("max_lat") != 0:
                tile_bounds_data = TileBounds(
                    min_lat=tb["min_lat"],
                    max_lat=tb["max_lat"],
                    min_lng=tb["min_lng"],
                    max_lng=tb["max_lng"],
                )

        package_data = OfflinePackageData(
            plan_id=request.plan_id,
            package_id=result["package_id"],
            version=result["version"],
            file_size=result["file_size"],
            created_at=pkg_info["created_at"] if pkg_info else "",
            tile_bounds=tile_bounds_data,
        )

        return OfflinePackageResponse(
            code=200, message="离线包生成成功", data=package_data
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"生成离线包失败: {str(e)}")


def download_offline_package(package_id: str) -> FileResponse:
    try:
        file_path = offline_package_service.get_package_file_path(package_id)
        if not file_path:
            raise HTTPException(
                status_code=404, detail=f"离线包不存在或已过期，package_id: {package_id}"
            )

        return FileResponse(
            path=file_path,
            media_type="application/zip",
            filename=f"{package_id}.zip",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载离线包失败: {str(e)}")
