"""
行程相关API路由
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, date, time
from typing import Optional, List
from app.models.trip import (
    GenerateTripRequest,
    GenerateTripResponse,
    TripData,
    TripItemData,
    TripListResponse,
    TripSummary,
    TripDetailResponse
)
from app.database import get_db
from app.db_models.trip_plan import TripPlan
from app.db_models.trip_item import TripItem
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/trip", tags=["行程规划"])

# 初始化AI服务
ai_service = AIService()


@router.post("/generate", response_model=GenerateTripResponse)
async def generate_trip(
    request: GenerateTripRequest,
    db: Session = Depends(get_db)
):
    """
    生成行程计划
    
    - **userId**: 用户ID
    - **query**: 用户查询文本
    - **preferences**: 用户偏好（健康目标、过敏原等）
    """
    try:
        # 准备偏好数据
        preferences_dict = None
        if request.preferences:
            preferences_dict = {
                "healthGoal": request.preferences.healthGoal,
                "allergens": request.preferences.allergens or []
            }
        
        # 调用AI服务生成行程
        trip_data = ai_service.generate_trip(
            query=request.query,
            preferences=preferences_dict
        )
        
        # 解析日期
        start_date = datetime.strptime(trip_data["startDate"], "%Y-%m-%d").date()
        end_date = datetime.strptime(trip_data["endDate"], "%Y-%m-%d").date()
        
        # 创建行程计划记录
        trip_plan = TripPlan(
            user_id=request.userId,
            title=trip_data.get("title", "行程计划"),
            destination=trip_data.get("destination"),
            start_date=start_date,
            end_date=end_date,
            travelers=trip_data.get("travelers", ["本人"]),
            status="planning"
        )
        
        db.add(trip_plan)
        db.flush()  # 获取trip_plan.id
        
        # 创建行程节点
        items = trip_data.get("items", [])
        for index, item_data in enumerate(items):
            # 解析时间
            start_time_obj = None
            if item_data.get("startTime"):
                try:
                    time_parts = item_data["startTime"].split(":")
                    start_time_obj = time(int(time_parts[0]), int(time_parts[1]))
                except:
                    pass
            
            trip_item = TripItem(
                trip_id=trip_plan.id,
                day_index=item_data.get("dayIndex", 1),
                start_time=start_time_obj,
                place_name=item_data.get("placeName", ""),
                place_type=item_data.get("placeType"),
                duration=item_data.get("duration"),
                cost=item_data.get("cost"),
                notes=item_data.get("notes"),
                sort_order=index
            )
            db.add(trip_item)
        
        # 提交事务
        db.commit()
        db.refresh(trip_plan)
        
        # 构建响应数据
        trip_items = db.query(TripItem).filter(TripItem.trip_id == trip_plan.id).order_by(TripItem.sort_order).all()
        
        items_data = []
        for item in trip_items:
            start_time_str = None
            if item.start_time:
                start_time_str = item.start_time.strftime("%H:%M")
            
            items_data.append(TripItemData(
                dayIndex=item.day_index,
                startTime=start_time_str,
                placeName=item.place_name,
                placeType=item.place_type,
                duration=item.duration,
                cost=item.cost,
                notes=item.notes
            ))
        
        trip_response = TripData(
            tripId=trip_plan.id,
            title=trip_plan.title,
            destination=trip_plan.destination,
            startDate=trip_plan.start_date.strftime("%Y-%m-%d"),
            endDate=trip_plan.end_date.strftime("%Y-%m-%d"),
            items=items_data
        )
        
        return GenerateTripResponse(
            code=200,
            message="行程生成成功",
            data=trip_response
        )
        
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"请求参数错误: {str(e)}")
    except Exception as e:
        db.rollback()
        print(f"生成行程失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成行程失败: {str(e)}")


def _trip_plan_to_summary(trip_plan: TripPlan, item_count: int = 0) -> TripSummary:
    """将TripPlan转换为TripSummary"""
    return TripSummary(
        tripId=trip_plan.id,
        title=trip_plan.title,
        destination=trip_plan.destination,
        startDate=trip_plan.start_date.strftime("%Y-%m-%d"),
        endDate=trip_plan.end_date.strftime("%Y-%m-%d"),
        status=trip_plan.status,
        itemCount=item_count
    )


def _trip_plan_to_data(trip_plan: TripPlan, trip_items: List[TripItem]) -> TripData:
    """将TripPlan和TripItems转换为TripData"""
    items_data = []
    for item in trip_items:
        start_time_str = None
        if item.start_time:
            start_time_str = item.start_time.strftime("%H:%M")
        
        items_data.append(TripItemData(
            dayIndex=item.day_index,
            startTime=start_time_str,
            placeName=item.place_name,
            placeType=item.place_type,
            duration=item.duration,
            cost=item.cost,
            notes=item.notes
        ))
    
    return TripData(
        tripId=trip_plan.id,
        title=trip_plan.title,
        destination=trip_plan.destination,
        startDate=trip_plan.start_date.strftime("%Y-%m-%d"),
        endDate=trip_plan.end_date.strftime("%Y-%m-%d"),
        items=items_data
    )


@router.get("/list", response_model=TripListResponse)
async def get_trip_list(
    userId: int,
    db: Session = Depends(get_db)
):
    """
    获取用户全部行程规划列表
    
    - **userId**: 用户ID
    """
    try:
        # 查询用户的所有行程，按创建时间倒序
        trip_plans = db.query(TripPlan).filter(
            TripPlan.user_id == userId
        ).order_by(TripPlan.created_at.desc()).all()
        
        # 转换为摘要格式
        trip_summaries = []
        for trip_plan in trip_plans:
            # 统计节点数量
            item_count = db.query(TripItem).filter(
                TripItem.trip_id == trip_plan.id
            ).count()
            
            trip_summaries.append(_trip_plan_to_summary(trip_plan, item_count))
        
        return TripListResponse(
            code=200,
            message="获取成功",
            data=trip_summaries
        )
        
    except Exception as e:
        print(f"获取行程列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取行程列表失败: {str(e)}")


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
    try:
        # 查询用户最近的行程，按创建时间倒序，限制数量
        trip_plans = db.query(TripPlan).filter(
            TripPlan.user_id == userId
        ).order_by(TripPlan.created_at.desc()).limit(limit).all()
        
        # 转换为摘要格式
        trip_summaries = []
        for trip_plan in trip_plans:
            # 统计节点数量
            item_count = db.query(TripItem).filter(
                TripItem.trip_id == trip_plan.id
            ).count()
            
            trip_summaries.append(_trip_plan_to_summary(trip_plan, item_count))
        
        return TripListResponse(
            code=200,
            message="获取成功",
            data=trip_summaries
        )
        
    except Exception as e:
        print(f"获取最近行程失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取最近行程失败: {str(e)}")


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
    try:
        # 查询用户最近的行程，按创建时间倒序，限制数量
        trip_plans = db.query(TripPlan).filter(
            TripPlan.user_id == userId
        ).order_by(TripPlan.created_at.desc()).limit(limit).all()
        
        # 转换为摘要格式
        trip_summaries = []
        for trip_plan in trip_plans:
            # 统计节点数量
            item_count = db.query(TripItem).filter(
                TripItem.trip_id == trip_plan.id
            ).count()
            
            trip_summaries.append(_trip_plan_to_summary(trip_plan, item_count))
        
        return TripListResponse(
            code=200,
            message="获取成功",
            data=trip_summaries
        )
        
    except Exception as e:
        print(f"获取首页行程失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取首页行程失败: {str(e)}")


@router.get("/{tripId}", response_model=TripDetailResponse)
async def get_trip_detail(
    tripId: int,
    db: Session = Depends(get_db)
):
    """
    获取某个行程的具体信息
    
    - **tripId**: 行程ID
    """
    try:
        # 查询行程计划
        trip_plan = db.query(TripPlan).filter(TripPlan.id == tripId).first()
        
        if not trip_plan:
            raise HTTPException(status_code=404, detail=f"行程不存在，tripId: {tripId}")
        
        # 查询行程节点，按排序序号排序
        trip_items = db.query(TripItem).filter(
            TripItem.trip_id == tripId
        ).order_by(TripItem.sort_order, TripItem.day_index, TripItem.start_time).all()
        
        # 转换为数据格式
        trip_data = _trip_plan_to_data(trip_plan, trip_items)
        
        return TripDetailResponse(
            code=200,
            message="获取成功",
            data=trip_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取行程详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取行程详情失败: {str(e)}")

