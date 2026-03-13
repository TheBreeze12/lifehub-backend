"""
行程相关API路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
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
from app.database import get_db
from app.services import trip_service

router = APIRouter(prefix="/api/trip", tags=["运动规划"])


@router.post("/generate", response_model=GenerateTripResponse)
async def generate_trip(
    request: GenerateTripRequest,
    db: Session = Depends(get_db)
):
    """
    生成运动计划（餐后运动规划）

    - **userId**: 用户ID
    - **query**: 用户查询文本（如"规划餐后运动，消耗300卡路里"）
    - **preferences**: 用户偏好（健康目标、过敏原等）
    - **latitude**: 用户当前位置纬度（可选）
    - **longitude**: 用户当前位置经度（可选）
    """
    print(request)
    return trip_service.generate_trip(db, request)


_trip_plan_to_summary = trip_service._trip_plan_to_summary
_trip_plan_to_data = trip_service._trip_plan_to_data


@router.get("/list", response_model=TripListResponse)
async def get_trip_list(
    userId: int,
    db: Session = Depends(get_db)
):
    """
    获取用户全部行程规划列表

    - **userId**: 用户ID
    """
    return trip_service.get_trip_list(db, userId)


@router.get("/recent", response_model=TripListResponse)
async def get_recent_trips(
    userId: int,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """
    获取用户最近行程规划

    - **userId**: 用户ID
    - **limit**: 返回数量限制（默认5条）
    """
    return trip_service.get_recent_trips(db, userId, limit)


@router.get("/home", response_model=TripListResponse)
async def get_home_trips(
    userId: int,
    limit: int = 3,
    db: Session = Depends(get_db)
):
    """
    首页展示行程（最近的几个行程）

    - **userId**: 用户ID
    - **limit**: 返回数量限制（默认3条）
    """
    return trip_service.get_home_trips(db, userId, limit)


# ==================== Phase 32: 天气动态调整 Plan B 接口 ====================

@router.get("/plan-b/{plan_id}", response_model=PlanBResponse)
async def get_plan_b(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """
    获取运动计划的天气动态调整方案（Plan B）

    根据运动计划所在位置的当前天气，评估是否适合户外运动。
    如果天气恶劣（中雨、大雪、雷暴、极端温度、大风等），
    自动生成室内替代运动方案，保持热量消耗目标接近原计划。

    - **plan_id**: 运动计划ID
    """
    return trip_service.get_plan_b(db, plan_id)


@router.get("/{tripId}", response_model=TripDetailResponse)
async def get_trip_detail(
    tripId: int,
    db: Session = Depends(get_db)
):
    """
    获取某个行程的具体信息

    - **tripId**: 行程ID
    """
    return trip_service.get_trip_detail(db, tripId)


# ==================== Phase 22: 帕累托最优路径生成接口 ====================

@router.post("/routes", response_model=GenerateRoutesResponse)
async def generate_pareto_routes(
    request: GenerateRoutesRequest
):
    """
    生成帕累托最优运动路径（2-3条）

    基于NSGA-II多目标优化算法，同时优化：
    - 最短时间
    - 最大热量消耗
    - 最佳绿化评分

    - **start_lat**: 起点纬度
    - **start_lng**: 起点经度
    - **target_calories**: 目标热量消耗（kcal）
    - **max_time_minutes**: 最大运动时间（分钟，默认60）
    - **exercise_type**: 运动类型（walking/running/cycling/jogging/hiking）
    - **weight_kg**: 用户体重（kg，默认70）
    """
    return trip_service.generate_pareto_routes(request)


# ==================== Phase 46: 离线运动包接口 ====================

@router.post("/offline-package", response_model=OfflinePackageResponse)
async def generate_offline_package(
    request: OfflinePackageRequest,
    db: Session = Depends(get_db)
):
    """
    生成离线运动包

    根据运动计划ID，打包运动方案文本、POI数据、地图瓦片元数据为ZIP离线包。
    支持同一计划多次生成（版本递增）。

    - **plan_id**: 运动计划ID（必须大于0）
    """
    return trip_service.generate_offline_package(db, request)


@router.get("/offline-package/{package_id}")
async def download_offline_package(package_id: str):
    """
    下载离线运动包

    根据离线包ID下载对应的ZIP文件。

    - **package_id**: 离线包唯一标识
    """
    return trip_service.download_offline_package(package_id)
