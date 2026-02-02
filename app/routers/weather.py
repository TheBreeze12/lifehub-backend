"""
天气相关API路由
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.ai_service import AIService
from app.database import get_db
from app.db_models.trip_plan import TripPlan

router = APIRouter(prefix="/api/weather", tags=["天气"])

# 初始化AI服务（复用地理编码能力）
ai_service = AIService()


@router.get("/by-address")
async def get_weather_by_address(address: str):
    """
    根据地址获取当前天气信息（使用 Open-Meteo）

    - **address**: 地址文本，例如 "北京市朝阳区望京"、"上海市浦东新区世纪公园"
    """
    try:
        weather = ai_service.get_weather_by_address(address)
        return {
            "code": 200,
            "message": "获取成功",
            "data": weather
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取天气失败: {str(e)}")


@router.get("/by-plan")
async def get_weather_by_plan(planId: int, db: Session = Depends(get_db)):
    """
    根据计划ID查询天气：
    - 若 `trip_plan.latitude/longitude` 存在，按坐标查询
    - 否则按 `trip_plan.destination` 地址查询
    """
    try:
        plan = db.query(TripPlan).filter(TripPlan.id == planId).first()
        if not plan:
            raise HTTPException(status_code=404, detail=f"行程不存在，planId: {planId}")

        if plan.latitude is not None and plan.longitude is not None:
            weather = ai_service.get_weather_by_coords(plan.latitude, plan.longitude, address_hint=plan.destination)
        else:
            if not plan.destination:
                raise HTTPException(status_code=400, detail="该计划无坐标且目的地为空，无法查询天气")
            weather = ai_service.get_weather_by_address(plan.destination)

        return {
            "code": 200,
            "message": "获取成功",
            "data": weather
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取天气失败: {str(e)}")
