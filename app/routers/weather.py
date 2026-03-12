"""
天气相关API路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import weather_service

router = APIRouter(prefix="/api/weather", tags=["天气"])


@router.get("/by-address")
async def get_weather_by_address(address: str):
    """
    根据地址获取当前天气信息（使用 Open-Meteo）

    - **address**: 地址文本，例如 "北京市朝阳区望京"、"上海市浦东新区世纪公园"
    """
    return weather_service.get_weather_by_address(address)


@router.get("/by-plan")
async def get_weather_by_plan(planId: int, db: Session = Depends(get_db)):
    """
    根据计划ID查询天气：
    - 若 `trip_plan.latitude/longitude` 存在，按坐标查询
    - 否则按 `trip_plan.destination` 地址查询
    """
    return weather_service.get_weather_by_plan(db, planId)
