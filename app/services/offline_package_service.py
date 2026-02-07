"""
离线运动包生成服务（Phase 46）

功能：
1. 地图瓦片区域计算与元数据生成
2. POI数据提取与打包
3. 运动方案文本生成
4. ZIP离线包打包与版本管理
"""
import os
import json
import uuid
import math
import zipfile
from datetime import datetime
from typing import List, Dict, Optional, Any


class OfflinePackageService:
    """离线运动包生成服务"""

    # 默认缓冲区（公里）
    DEFAULT_PADDING_KM = 0.5
    # 默认瓦片缩放级别范围
    DEFAULT_ZOOM_LEVELS = [14, 15, 16]

    def __init__(self, storage_dir: str = None):
        """
        初始化离线包服务

        Args:
            storage_dir: 离线包文件存储目录，默认为项目根目录下的 offline_packages/
        """
        if storage_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            storage_dir = os.path.join(base_dir, "offline_packages")
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

        # 包元数据索引（内存中维护，key=package_id）
        self._package_index: Dict[str, Dict[str, Any]] = {}
        # plan_id -> 版本计数
        self._plan_version_counter: Dict[int, int] = {}

    # ----------------------------------------------------------
    # 1. 运动方案文本生成
    # ----------------------------------------------------------
    def generate_plan_text(self, plan, items: list) -> dict:
        """
        将运动计划和运动项目转换为结构化文本数据

        Args:
            plan: TripPlan ORM 对象
            items: TripItem ORM 对象列表

        Returns:
            结构化的运动方案字典
        """
        total_duration = 0
        total_calories = 0.0
        items_data = []

        for item in items:
            duration = item.duration or 0
            cost = item.cost or 0.0
            total_duration += duration
            total_calories += cost

            start_time_str = None
            if item.start_time:
                start_time_str = item.start_time.strftime("%H:%M") if hasattr(item.start_time, 'strftime') else str(item.start_time)

            items_data.append({
                "day_index": item.day_index,
                "start_time": start_time_str,
                "place_name": item.place_name,
                "place_type": item.place_type,
                "duration": duration,
                "calories": cost,
                "notes": item.notes or "",
            })

        # 日期格式化
        start_date_str = ""
        if plan.start_date:
            start_date_str = plan.start_date.strftime("%Y-%m-%d") if hasattr(plan.start_date, 'strftime') else str(plan.start_date)

        return {
            "title": plan.title or "",
            "destination": plan.destination or "",
            "date": start_date_str,
            "total_duration": total_duration,
            "total_calories": round(total_calories, 1),
            "item_count": len(items_data),
            "items": items_data,
        }

    # ----------------------------------------------------------
    # 2. POI数据提取
    # ----------------------------------------------------------
    def extract_poi_data(self, items: list) -> list:
        """
        从运动项目中提取POI数据

        Args:
            items: TripItem ORM 对象列表

        Returns:
            POI字典列表
        """
        pois = []
        for item in items:
            poi = {
                "name": item.place_name or "",
                "type": item.place_type or "unknown",
                "latitude": item.latitude,
                "longitude": item.longitude,
                "duration": item.duration or 0,
                "notes": item.notes or "",
            }
            pois.append(poi)
        return pois

    # ----------------------------------------------------------
    # 3. 地图瓦片区域计算
    # ----------------------------------------------------------
    def calculate_tile_bounds(self, points: List[dict], padding_km: float = None) -> dict:
        """
        根据坐标点列表计算地图瓦片覆盖区域

        Args:
            points: 坐标点列表，每个元素含 latitude 和 longitude
            padding_km: 边界缓冲区（公里）

        Returns:
            瓦片元数据字典，包含 bounds、zoom_levels、tile_count_estimate
        """
        if padding_km is None:
            padding_km = self.DEFAULT_PADDING_KM

        # 过滤有效坐标
        valid_points = [
            p for p in points
            if p.get("latitude") is not None and p.get("longitude") is not None
        ]

        if not valid_points:
            return {
                "bounds": {"min_lat": 0, "max_lat": 0, "min_lng": 0, "max_lng": 0},
                "zoom_levels": self.DEFAULT_ZOOM_LEVELS,
                "tile_count_estimate": 0,
                "center": {"latitude": 0, "longitude": 0},
            }

        lats = [p["latitude"] for p in valid_points]
        lngs = [p["longitude"] for p in valid_points]

        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)

        # 添加缓冲区（1度纬度 ≈ 111km）
        lat_padding = padding_km / 111.0
        # 1度经度 ≈ 111 * cos(lat) km
        avg_lat = (min_lat + max_lat) / 2.0
        lng_padding = padding_km / (111.0 * max(math.cos(math.radians(avg_lat)), 0.01))

        bounds = {
            "min_lat": round(min_lat - lat_padding, 6),
            "max_lat": round(max_lat + lat_padding, 6),
            "min_lng": round(min_lng - lng_padding, 6),
            "max_lng": round(max_lng + lng_padding, 6),
        }

        center = {
            "latitude": round((min_lat + max_lat) / 2.0, 6),
            "longitude": round((min_lng + max_lng) / 2.0, 6),
        }

        # 估算瓦片数量
        tile_count = self._estimate_tile_count(bounds, self.DEFAULT_ZOOM_LEVELS)

        return {
            "bounds": bounds,
            "zoom_levels": self.DEFAULT_ZOOM_LEVELS,
            "tile_count_estimate": tile_count,
            "center": center,
        }

    def _estimate_tile_count(self, bounds: dict, zoom_levels: list) -> int:
        """估算指定区域和缩放级别下的瓦片数量"""
        total = 0
        for zoom in zoom_levels:
            n = 2 ** zoom
            # 将经纬度转换为瓦片坐标
            min_x = int((bounds["min_lng"] + 180.0) / 360.0 * n)
            max_x = int((bounds["max_lng"] + 180.0) / 360.0 * n)
            min_y = int((1.0 - math.log(math.tan(math.radians(max(bounds["max_lat"], -85))) +
                        1.0 / max(math.cos(math.radians(max(bounds["max_lat"], -85))), 1e-10)) / math.pi) / 2.0 * n)
            max_y = int((1.0 - math.log(math.tan(math.radians(max(bounds["min_lat"], -85))) +
                        1.0 / max(math.cos(math.radians(max(bounds["min_lat"], -85))), 1e-10)) / math.pi) / 2.0 * n)

            # 确保 min <= max
            if min_x > max_x:
                min_x, max_x = max_x, min_x
            if min_y > max_y:
                min_y, max_y = max_y, min_y

            width = max_x - min_x + 1
            height = max_y - min_y + 1
            total += width * height
        return total

    # ----------------------------------------------------------
    # 4. 离线包生成（ZIP打包）
    # ----------------------------------------------------------
    def generate_package(self, plan, items: list) -> dict:
        """
        生成完整的离线运动包（ZIP格式）

        Args:
            plan: TripPlan ORM 对象
            items: TripItem ORM 对象列表

        Returns:
            包信息字典: package_id, file_path, file_size, version
        """
        plan_id = plan.id

        # 版本管理
        current_version = self._plan_version_counter.get(plan_id, 0) + 1
        self._plan_version_counter[plan_id] = current_version

        # 生成唯一包ID
        package_id = f"pkg_{plan_id}_{current_version}_{uuid.uuid4().hex[:8]}"

        # 生成各部分数据
        plan_text = self.generate_plan_text(plan, items)
        pois = self.extract_poi_data(items)

        # 收集坐标点（含plan本身的坐标和items的坐标）
        coord_points = []
        if plan.latitude is not None and plan.longitude is not None:
            coord_points.append({"latitude": plan.latitude, "longitude": plan.longitude})
        for item in items:
            if item.latitude is not None and item.longitude is not None:
                coord_points.append({"latitude": item.latitude, "longitude": item.longitude})

        tiles_meta = self.calculate_tile_bounds(coord_points)

        # 元数据
        metadata = {
            "package_id": package_id,
            "plan_id": plan_id,
            "version": current_version,
            "created_at": datetime.now().isoformat(),
            "format_version": "1.0",
            "contents": ["plan.json", "pois.json", "tiles_meta.json"],
        }

        # 打包为ZIP
        # 使用安全的文件名
        safe_filename = f"{package_id}.zip"
        file_path = os.path.join(self.storage_dir, safe_filename)

        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
            zf.writestr("plan.json", json.dumps(plan_text, ensure_ascii=False, indent=2))
            zf.writestr("pois.json", json.dumps(pois, ensure_ascii=False, indent=2))
            zf.writestr("tiles_meta.json", json.dumps(tiles_meta, ensure_ascii=False, indent=2))

        file_size = os.path.getsize(file_path)

        # 更新索引
        package_info = {
            "package_id": package_id,
            "plan_id": plan_id,
            "version": current_version,
            "file_path": file_path,
            "file_size": file_size,
            "created_at": metadata["created_at"],
            "tile_bounds": tiles_meta.get("bounds"),
        }
        self._package_index[package_id] = package_info

        return {
            "package_id": package_id,
            "file_path": file_path,
            "file_size": file_size,
            "version": current_version,
        }

    # ----------------------------------------------------------
    # 5. 包信息查询
    # ----------------------------------------------------------
    def get_package_info(self, package_id: str) -> Optional[dict]:
        """获取离线包元数据"""
        return self._package_index.get(package_id)

    def get_package_file_path(self, package_id: str) -> Optional[str]:
        """获取离线包文件路径"""
        info = self._package_index.get(package_id)
        if info and os.path.exists(info["file_path"]):
            return info["file_path"]
        return None

    def list_packages_for_plan(self, plan_id: int) -> list:
        """列出某个计划的所有离线包（按版本排序）"""
        packages = [
            info for info in self._package_index.values()
            if info["plan_id"] == plan_id
        ]
        packages.sort(key=lambda x: x["version"])
        return packages
