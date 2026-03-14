"""
Trip API application services.
"""
from datetime import datetime, date, time
from typing import List, Dict, Any, Tuple, Optional
import os
import math
import logging
from pathlib import Path

from fastapi import HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import requests

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
    PlaceInfo,
    TripListResponse,
    TripSummary,
    TripDetailResponse,
    GenerateRoutesRequest,
    GenerateRoutesResponse,
    RoutesResponseData,
    ParetoRoute,
    RouteWaypoint,
    NavigationStep,
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
from app.services.weather_service import get_weather_service
from app.services.offline_package_service import OfflinePackageService

logger = logging.getLogger(__name__)
ROUTE_DEBUG_LOG_PATH = Path(__file__).resolve().parents[2] / "route_debug.log"


def _route_debug(message: str, level: str = "info") -> None:
    """同时写标准 logger 和 route_debug.log，避免日志配置导致看不到输出。"""
    log_method = getattr(logger, level, logger.info)
    try:
        log_method(message)
    except Exception:
        pass

    try:
        ROUTE_DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with ROUTE_DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{timestamp} [{level.upper()}] {message}\n")
    except Exception:
        pass

ai_service = AIService()
mets_service = METsService()
weather_service = get_weather_service()
offline_package_service = OfflinePackageService()

AMAP_WALKING_API = "https://restapi.amap.com/v3/direction/walking"


def generate_trip(db: Session, request: GenerateTripRequest) -> GenerateTripResponse:
    try:
        preferences_dict = None
        user = user_crud.get_user_by_id(db, request.userId)
        if not request.preferences:
            preferences_dict={
                "healthGoal":user.health_goal,
                "allergens":user.allergens
            }
        else:
            preferences_dict = {
                "healthGoal": request.preferences.healthGoal,
                "allergens": request.preferences.allergens or [],
            }

        print(preferences_dict)
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

            place_data = item_data.get("place")
            item_lat = None
            item_lng = None
            item_address = None
            item_poi_id = None
            if isinstance(place_data, dict):
                item_lat = place_data.get("latitude")
                item_lng = place_data.get("longitude")
                item_address = place_data.get("address")
                item_poi_id = place_data.get("poi_id")

            trip_item = TripItem(
                trip_id=trip_plan.id,
                day_index=item_data.get("dayIndex", 1),
                start_time=start_time_obj,
                place_name=item_data.get("placeName", ""),
                place_type=item_data.get("placeType"),
                duration=item_data.get("duration"),
                cost=calories_burned,
                latitude=item_lat,
                longitude=item_lng,
                place_address=item_address,
                poi_id=item_poi_id,
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

            place_info = None
            if item.latitude is not None and item.longitude is not None:
                place_info = PlaceInfo(
                    poiId=item.poi_id,
                    name=item.place_name,
                    address=item.place_address,
                    latitude=item.latitude,
                    longitude=item.longitude,
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
                    place=place_info,
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

        place_info = None
        if item.latitude is not None and item.longitude is not None:
            place_info = PlaceInfo(
                poiId=item.poi_id,
                name=item.place_name,
                address=item.place_address,
                latitude=item.latitude,
                longitude=item.longitude,
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
                place=place_info,
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

def delete_trip_by_id(db:Session,plan_id:int):
    try:
        trip_plan=trip_plan_crud.get_trip_plan_by_id(db,plan_id)
        if not trip_plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f'运动计划不存在,plan_id:{plan_id}')
        result=trip_plan_crud.delete_trip_plans_by_id(db,plan_id)
        return {
            "msg":"success",
            "code":200,
            "data":result
        }
    except Exception as e :
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f'删除行程失败：{str(e)}')



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
                weather_data = weather_service.get_weather_by_coords(
                    trip_plan.latitude,
                    trip_plan.longitude,
                    address_hint=trip_plan.destination,
                )
            elif trip_plan.destination:
                weather_data = weather_service.get_weather_by_address(trip_plan.destination)
        except Exception as weather_err:
            print(f"获取天气失败: {weather_err}")
        print(weather_data)
        weather_eval = weather_service.evaluate_weather(weather_data)
        print(weather_eval)

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


def _normalize_exercise_type(exercise_type: Optional[str]) -> str:
    normalized = (exercise_type or "walking").strip().lower()
    if normalized in {"running", "jogging", "hiking"}:
        return "walking"
    return normalized or "walking"


def _haversine_distance_meters(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    radius = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


"""
已下线旧版 generate_pareto_routes 复杂候选路线逻辑（多候选环路/POI补点/曲线兜底）。
根据当前需求，改为简单顺序导航：
trip_plan 起点 -> 按 trip_items 顺序逐点步行导航。
"""


def _parse_amap_polyline(polyline: str) -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    if not polyline:
        return points
    for raw in polyline.split(";"):
        parts = raw.split(",")
        if len(parts) != 2:
            continue
        try:
            lng = float(parts[0])
            lat = float(parts[1])
            points.append((lat, lng))
        except ValueError:
            continue
    return points


def _first_point_from_polyline(polyline: str) -> Optional[Tuple[float, float]]:
    points = _parse_amap_polyline(polyline)
    if not points:
        return None
    return points[0]


def _query_amap_walking_segment(
    origin: Tuple[float, float],
    destination: Tuple[float, float],
) -> Optional[Dict[str, Any]]:
    amap_key = os.getenv("AMAP_KEY", "")
    if not amap_key:
        logger.warning("AMAP_KEY 未设置，无法调用高德步行导航 API")
        return None

    origin_str = f"{origin[1]},{origin[0]}"
    dest_str = f"{destination[1]},{destination[0]}"

    try:
        resp = requests.get(
            AMAP_WALKING_API,
            params={"key": amap_key, "origin": origin_str, "destination": dest_str},
            timeout=8,
        )
        payload = resp.json()
        success = payload.get("infocode") == "10000" or payload.get("status") == "1"
        if not success:
            logger.warning(
                "高德步行 API 异常: infocode=%s status=%s info=%s origin=%s dest=%s",
                payload.get("infocode"), payload.get("status"), payload.get("info", ""), origin_str, dest_str,
            )
            return None

        route = payload.get("route", {})
        paths = route.get("paths") or []
        if isinstance(paths, dict):
            paths = [paths]
        if not paths:
            logger.warning("高德步行 API 无路径: origin=%s dest=%s", origin_str, dest_str)
            return None

        path = paths[0]
        steps = path.get("steps") or []
        polyline_points: List[Tuple[float, float]] = [origin]
        step_instructions: List[Dict[str, Any]] = []
        for step in steps:
            first_point = _first_point_from_polyline(step.get("polyline", ""))
            if first_point is not None:
                if polyline_points[-1] != first_point:
                    polyline_points.append(first_point)

            step_distance = None
            try:
                if step.get("distance") is not None:
                    step_distance = float(step.get("distance"))
            except (TypeError, ValueError):
                step_distance = None

            step_duration = None
            try:
                if step.get("duration") is not None:
                    step_duration = float(step.get("duration"))
            except (TypeError, ValueError):
                step_duration = None

            step_instructions.append(
                {
                    "instruction": step.get("instruction") or "",
                    "orientation": step.get("orientation"),
                    "road": step.get("road") if isinstance(step.get("road"), str) else None,
                    "distance_meters": step_distance,
                    "duration_seconds": step_duration,
                }
            )

        if not polyline_points:
            polyline_points = [origin, destination]
        elif polyline_points[-1] != destination:
            polyline_points.append(destination)

        distance = float(path.get("distance", 0) or 0)
        duration = float(path.get("duration", 0) or 0)
        if duration <= 0:
            duration = float((path.get("cost") or {}).get("duration", 0) or 0)
        if duration <= 0:
            duration = distance / 1.4 if distance > 0 else 0

        return {
            "distance_meters": distance,
            "duration_seconds": duration,
            "polyline": polyline_points,
            "steps": step_instructions,
        }
    except requests.exceptions.Timeout:
        logger.warning("高德步行 API 超时: origin=%s dest=%s", origin_str, dest_str)
        return None
    except Exception as exc:
        logger.warning("高德步行 API 异常: %s origin=%s dest=%s", exc, origin_str, dest_str)
        return None


def _fallback_walking_segment(
    origin: Tuple[float, float],
    destination: Tuple[float, float],
) -> Dict[str, Any]:
    """高德分段失败时的简易兜底：两点直连+步行速度估算。"""
    speed_mps = 1.4
    distance = _haversine_distance_meters(origin[0], origin[1], destination[0], destination[1])
    duration = distance / speed_mps if speed_mps > 0 else 0
    return {
        "distance_meters": distance,
        "duration_seconds": duration,
        "polyline": [origin, destination],
    }


def _compact_points(points: List[Tuple[float, float]], max_points: int = 200) -> List[Tuple[float, float]]:
    _route_debug(f"[_compact_points] 输入点数: {len(points)}, max_points: {max_points}")
    if points:
        _route_debug(f"[_compact_points] 首尾点: {points[0]} -> {points[-1]}")

    if len(points) <= max_points:
        return points

    step = max(1, len(points) // max_points)
    _route_debug(f"[_compact_points] 采样步长: {step}")
    compacted = points[::step]

    _route_debug(f"[_compact_points] 采样后点数: {len(compacted)}")
    if compacted:
        _route_debug(f"[_compact_points] 采样后首尾点: {compacted[0]} -> {compacted[-1]}")

    if compacted and points and compacted[-1] != points[-1]:
        compacted.append(points[-1])
        _route_debug(f"[_compact_points] 追加末尾点，最终点数: {len(compacted)}")

    return compacted


def _dominant_exercise_type(items: List[TripItem], default: str = "walking") -> str:
    counter: Dict[str, int] = {}
    for item in items:
        et = (item.place_type or "").strip().lower()
        if not et:
            continue
        counter[et] = counter.get(et, 0) + 1
    if not counter:
        return default
    return sorted(counter.items(), key=lambda x: x[1], reverse=True)[0][0]


def _extract_ordered_nodes(trip_items: List[TripItem]) -> Tuple[List[Dict[str, Any]], List[str]]:
    ordered_items = sorted(
        trip_items,
        key=lambda i: (
            i.day_index or 0,
            1 if i.start_time is None else 0,
            i.start_time or time(0, 0),
            i.sort_order or 0,
            i.id or 0,
        ),
    )

    nodes: List[Dict[str, Any]] = []
    unresolved: List[str] = []
    for item in ordered_items:
        if item.latitude is None or item.longitude is None:
            unresolved.append(item.place_name or f"item-{item.id}")
            continue
        nodes.append(
            {
                "item_id": item.id,
                "name": item.place_name,
                "lat": float(item.latitude),
                "lng": float(item.longitude),
                "exercise_type": item.place_type or "walking",
            }
        )
    return nodes, unresolved


def _format_waypoints(polyline: List[Tuple[float, float]]) -> List[RouteWaypoint]:
    if not polyline:
        return []
    waypoints: List[RouteWaypoint] = []
    for idx, p in enumerate(polyline):
        waypoint_type = "waypoint"
        if idx == 0:
            waypoint_type = "start"
        elif idx == len(polyline) - 1:
            waypoint_type = "end"
        waypoints.append(RouteWaypoint(lat=p[0], lng=p[1], order=idx, type=waypoint_type))
    return waypoints


def _dump_model_json(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


def _validate_generate_routes_response(payload: Any) -> GenerateRoutesResponse:
    if hasattr(GenerateRoutesResponse, "model_validate"):
        return GenerateRoutesResponse.model_validate(payload)
    return GenerateRoutesResponse.parse_obj(payload)


def _is_degenerate_waypoints(routes: List[ParetoRoute]) -> bool:
    """检测缓存路线是否退化为“多点同坐标”。"""
    for route in routes or []:
        waypoints = route.waypoints or []
        if len(waypoints) <= 1:
            continue
        coords = {(round(wp.lat, 7), round(wp.lng, 7)) for wp in waypoints}
        if len(coords) == 1:
            return True
    return False


def _log_return_waypoint_preview(source: str, routes: List[ParetoRoute]) -> None:
    if not routes:
        _route_debug(f"[Route][Return] {source}: routes为空")
        return

    route = routes[0]
    ordered = sorted(route.waypoints or [], key=lambda wp: wp.order)
    preview = ordered[:3]
    _route_debug(
        f"[Route][Return] {source}: route_id={route.route_id}, waypoints={len(ordered)}"
    )
    for wp in preview:
        _route_debug(
            f"[Route][Return] {source}: order={wp.order}, type={wp.type}, lat={wp.lat:.10f}, lng={wp.lng:.10f}"
        )


def _try_get_cached_routes_response(
    trip_plan: TripPlan, force_regenerate: bool
) -> Optional[GenerateRoutesResponse]:
    if force_regenerate or not trip_plan.route_cache:
        return None

    try:
        cached = _validate_generate_routes_response(trip_plan.route_cache)
        routes = (cached.data.routes if cached.data and cached.data.routes else [])
        if _is_degenerate_waypoints(routes):
            _route_debug(
                f"[Route][Cache] 检测到退化缓存，自动失效并重算，plan_id={trip_plan.id}",
                level="warning",
            )
            return None

        if cached.data:
            cached.data.cache_hit = True
        cached.message = f"{cached.message}（命中缓存）"
        _route_debug(f"[Route][Cache] 命中有效缓存，plan_id={trip_plan.id}")
        _log_return_waypoint_preview("cache", routes)
        return cached
    except Exception as cache_err:
        logger.warning("trip_plan路线缓存解析失败，plan_id=%s err=%s", trip_plan.id, cache_err)
        return None


def _save_routes_response_cache(
    db: Session, trip_plan: TripPlan, response: GenerateRoutesResponse
) -> None:
    payload = _dump_model_json(response)
    data_obj = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data_obj, dict):
        data_obj["cache_hit"] = False

    trip_plan.route_cache = payload
    trip_plan.route_cache_updated_at = datetime.now()
    db.commit()
    db.refresh(trip_plan)


def _generate_simple_routes_from_trip_plan(
    db: Session, request: GenerateRoutesRequest
) -> GenerateRoutesResponse:
    _route_debug(
        f"[Route] generate_routes 请求: plan_id={request.plan_id}, force_regenerate={request.force_regenerate}"
    )
    if not request.plan_id:
        raise HTTPException(status_code=400, detail="缺少plan_id，无法基于trip_plan生成路线")

    trip_plan = trip_plan_crud.get_trip_plan_by_id(db, request.plan_id)
    if not trip_plan:
        raise HTTPException(status_code=404, detail=f"运动计划不存在，plan_id: {request.plan_id}")

    cached_response = _try_get_cached_routes_response(
        trip_plan, request.force_regenerate
    )
    if cached_response is not None:
        return cached_response

    _route_debug(f"[Route][Cache] 本次未命中缓存，开始实时重算，plan_id={request.plan_id}")

    trip_items = trip_item_crud.get_trip_items_by_trip_id_simple(db, request.plan_id)
    if not trip_items:
        raise HTTPException(status_code=400, detail="该运动计划没有可用于路线规划的节点")

    start_lat = trip_plan.latitude
    start_lng = trip_plan.longitude
    if start_lat is None or start_lng is None:
        raise HTTPException(status_code=400, detail="trip_plan缺少起点坐标，无法按计划顺序导航")

    start_point = (float(start_lat), float(start_lng))

    inferred_exercise_type = _dominant_exercise_type(trip_items, default="walking")
    exercise_type = request.exercise_type or inferred_exercise_type

    user_weight = request.weight_kg
    if user_weight is None:
        user = user_crud.get_user_by_id(db, trip_plan.user_id)
        user_weight = user.weight if user and user.weight else mets_service.DEFAULT_WEIGHT_KG

    max_time_minutes = request.max_time_minutes or max(
        15,
        sum((item.duration or 0) for item in trip_items),
    )
    target_calories = request.target_calories or max(
        50.0,
        sum((item.cost or 0.0) for item in trip_items),
    )

    nodes, unresolved_names = _extract_ordered_nodes(trip_items)
    if not nodes:
        raise HTTPException(status_code=400, detail="trip_items均无坐标，无法顺序导航")

    total_distance = 0.0
    total_duration = 0.0
    polyline: List[Tuple[float, float]] = [start_point]
    navigation_steps: List[NavigationStep] = []
    amap_fail = 0
    cursor = start_point

    _route_debug(f"[Route] 开始生成路线，起点: {start_point}, 节点数: {len(nodes)}")

    for node_idx, node in enumerate(nodes):
        destination = (node["lat"], node["lng"])
        _route_debug(f"[Route] 节点{node_idx}: {node['name']} -> 目标坐标: {destination}")

        seg = _query_amap_walking_segment(cursor, destination)
        if seg is None:
            amap_fail += 1
            seg = _fallback_walking_segment(cursor, destination)
            _route_debug(f"[Route] 高德API失败，使用兜底方案，polyline点数: {len(seg.get('polyline', []))}")
        else:
            _route_debug(f"[Route] 高德API成功，polyline点数: {len(seg.get('polyline', []))}")

        total_distance += float(seg.get("distance_meters", 0.0) or 0.0)
        total_duration += float(seg.get("duration_seconds", 0.0) or 0.0)

        for raw_step in seg.get("steps") or []:
            try:
                navigation_steps.append(
                    NavigationStep(
                        instruction=raw_step.get("instruction") or "",
                        orientation=raw_step.get("orientation"),
                        road=raw_step.get("road"),
                        distance_meters=raw_step.get("distance_meters"),
                        duration_seconds=raw_step.get("duration_seconds"),
                    )
                )
            except Exception:
                continue

        seg_poly = seg.get("polyline") or [cursor, destination]
        _route_debug(f"[Route] seg_poly类型: {type(seg_poly)}, 点数: {len(seg_poly)}")
        if seg_poly:
            _route_debug(f"[Route] seg_poly首尾: {seg_poly[0]} -> {seg_poly[-1]}")

        if polyline and seg_poly and polyline[-1] == seg_poly[0]:
            _route_debug(f"[Route] 首点相同，跳过重复")
            polyline.extend(seg_poly[1:])
        else:
            _route_debug(f"[Route] 首点不同，全部添加")
            polyline.extend(seg_poly)

        cursor = destination
        _route_debug(f"[Route] 累计polyline点数: {len(polyline)}")

    _route_debug(f"[Route] 路线构建完成，原始polyline点数: {len(polyline)}")
    if polyline:
        _route_debug(f"[Route] polyline首尾: {polyline[0]} -> {polyline[-1]}")

    duration_minutes = total_duration / 60.0
    calories_burn = mets_service.calculate_calories(
        exercise_type=exercise_type,
        weight_kg=user_weight,
        duration_minutes=max(1, int(round(duration_minutes))),
    )

    routes_data = [
        ParetoRoute(
            route_id=1,
            route_name="顺序步行导航",
            time_minutes=round(duration_minutes, 1),
            calories_burn=round(calories_burn, 1),
            greenery_score=55.0,
            distance_meters=round(total_distance, 1),
            waypoints=_format_waypoints(_compact_points(polyline)),
            navigation_steps=navigation_steps,
            exercise_type=exercise_type,
            intensity=0.75,
        )
    ]

    message = "运动路线生成成功"
    tips: List[str] = []
    if unresolved_names:
        preview = "、".join(unresolved_names[:3])
        suffix = "等" if len(unresolved_names) > 3 else ""
        tips.append(f"跳过无坐标节点: {preview}{suffix}")
    if amap_fail > 0:
        tips.append(f"{amap_fail}段高德步行导航失败，已使用直线兜底")
    if tips:
        message = f"{message}（{'；'.join(tips)}）"

    response = GenerateRoutesResponse(
        code=200,
        message=message,
        data=RoutesResponseData(
            routes=routes_data,
            start_point=RouteWaypoint(lat=start_point[0], lng=start_point[1], order=0, type="start"),
            target_calories=float(target_calories),
            max_time_minutes=int(max_time_minutes),
            exercise_type=exercise_type,
            weight_kg=float(user_weight),
            n_routes=len(routes_data),
            cache_hit=False,
        ),
    )

    try:
        _save_routes_response_cache(db, trip_plan, response)
    except Exception as cache_save_err:
        logger.warning("路线缓存写入失败，plan_id=%s err=%s", trip_plan.id, cache_save_err)

    _log_return_waypoint_preview("fresh", routes_data)

    return response


def generate_pareto_routes(db: Session, request: GenerateRoutesRequest) -> GenerateRoutesResponse:
    try:
        if not request.plan_id:
            raise HTTPException(
                status_code=400,
                detail="新路线逻辑仅支持 plan_id：起点使用trip_plan坐标，并按trip_items顺序导航",
            )

        return _generate_simple_routes_from_trip_plan(db, request)

    except HTTPException:
        raise
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

        result = offline_package_service.generate_package(
            trip_plan,
            trip_items,
            route_cache=trip_plan.route_cache,
        )

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
