"""
POI检索服务 - 使用高德地图Web API进行真实地点检索

需要环境变量: AMAP_KEY (高德地图Web服务API Key)
申请地址: https://console.amap.com/dev/key/app
"""

import os
import math
import logging
from typing import List, Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)

EXERCISE_TYPE_TO_POI_KEYWORDS: Dict[str, List[str]] = {
    "walking":  ["公园", "步道", "广场", "绿道"],
    "running":  ["跑步道", "体育场", "运动公园", "田径场"],
    "cycling":  ["骑行道", "绿道", "自行车", "环湖路"],
    "park":     ["公园", "森林公园", "湿地公园"],
    "gym":      ["健身房", "健身中心", "体育馆"],
    "indoor":   ["体育馆", "健身房", "羽毛球馆", "游泳馆"],
    "outdoor":  ["公园", "广场", "步道"],
    "jogging":  ["公园", "步道", "体育场"],
    "hiking":   ["登山步道", "森林公园", "风景区"],
    "swimming": ["游泳馆", "游泳池"],
    "yoga":     ["瑜伽馆", "健身中心"],
}

EXERCISE_TYPE_TO_POI_TYPES: Dict[str, str] = {
    "walking":  "110101|110102|110104",
    "running":  "080102|080104|110101",
    "cycling":  "110101|110102",
    "park":     "110101|110102|110104",
    "gym":      "080301|080302|080303",
    "indoor":   "080301|080302|080303|080600",
    "outdoor":  "110101|110102|110104",
    "jogging":  "110101|080102",
    "hiking":   "110101|110200",
    "swimming": "080600",
    "yoga":     "080301|080302",
}


class POIResult:
    """单个POI检索结果"""

    def __init__(
        self,
        poi_id: str,
        name: str,
        address: str,
        latitude: float,
        longitude: float,
        city: str = "",
        district: str = "",
        type_name: str = "",
        distance: Optional[float] = None,
    ):
        self.poi_id = poi_id
        self.name = name
        self.address = address
        self.latitude = latitude
        self.longitude = longitude
        self.city = city
        self.district = district
        self.type_name = type_name
        self.distance = distance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "poi_id": self.poi_id,
            "name": self.name,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "city": self.city,
            "district": self.district,
            "type_name": self.type_name,
            "distance": self.distance,
        }


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点间距离（米）"""
    R = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class POIService:
    """高德地图POI检索服务"""

    NEARBY_API = "https://restapi.amap.com/v3/place/around"
    TEXT_API = "https://restapi.amap.com/v3/place/text"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("AMAP_KEY", "")
        if not self.api_key:
            logger.warning("AMAP_KEY 未设置，POI检索功能不可用")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def search_nearby(
        self,
        latitude: float,
        longitude: float,
        keywords: Optional[str] = None,
        poi_types: Optional[str] = None,
        radius: int = 3000,
        limit: int = 5,
    ) -> List[POIResult]:
        """周边检索"""
        if not self.available:
            return []

        params: Dict[str, Any] = {
            "key": self.api_key,
            "location": f"{longitude},{latitude}",
            "radius": radius,
            "offset": limit,
            "page": 1,
            "extensions": "base",
            "output": "json",
        }
        if keywords:
            params["keywords"] = keywords
        if poi_types:
            params["types"] = poi_types

        try:
            resp = requests.get(self.NEARBY_API, params=params, timeout=5)
            data = resp.json()
            if data.get("status") != "1":
                logger.warning(f"高德POI检索失败: {data.get('info')}")
                return []
            return self._parse_pois(data.get("pois", []), latitude, longitude)
        except Exception as e:
            logger.error(f"POI检索异常: {e}")
            return []

    def search_for_exercise(
        self,
        latitude: float,
        longitude: float,
        exercise_type: str = "walking",
        radius: int = 3000,
        limit: int = 3,
    ) -> List[POIResult]:
        """根据运动类型检索附近适合的运动地点"""
        keywords_list = EXERCISE_TYPE_TO_POI_KEYWORDS.get(exercise_type, ["公园", "步道", "广场"])
        poi_types = EXERCISE_TYPE_TO_POI_TYPES.get(exercise_type)

        all_results: List[POIResult] = []
        seen_ids: set = set()

        for kw in keywords_list:
            results = self.search_nearby(
                latitude=latitude,
                longitude=longitude,
                keywords=kw,
                poi_types=poi_types,
                radius=radius,
                limit=limit,
            )
            for r in results:
                if r.poi_id not in seen_ids:
                    seen_ids.add(r.poi_id)
                    all_results.append(r)

        all_results.sort(key=lambda x: x.distance or float("inf"))
        return all_results[:limit]

    def search_diverse_for_plan(
        self,
        latitude: float,
        longitude: float,
        items: List[Dict[str, Any]],
        radius: int = 5000,
    ) -> List[Dict[str, Any]]:
        """为运动计划的多个节点批量检索POI，保证地点多样性。

        Args:
            latitude, longitude: 用户位置
            items: LLM生成的items列表（含placeName, placeType等）
            radius: 搜索半径（米）

        Returns:
            增强后的items列表，每个item新增place字段
        """
        if not self.available:
            return items

        used_poi_ids: set = set()
        enriched = []

        for item in items:
            exercise_type = item.get("placeType") or "walking"

            candidates = self.search_for_exercise(
                latitude=latitude,
                longitude=longitude,
                exercise_type=exercise_type,
                radius=radius,
                limit=8,
            )

            chosen = None
            for c in candidates:
                if c.poi_id not in used_poi_ids:
                    chosen = c
                    break

            if chosen is None and candidates:
                chosen = candidates[0]

            if chosen:
                used_poi_ids.add(chosen.poi_id)
                item["place"] = chosen.to_dict()
                item["placeName"] = chosen.name
            else:
                item["place"] = None

            enriched.append(item)

        return enriched

    def _parse_pois(
        self, pois: list, ref_lat: float, ref_lng: float
    ) -> List[POIResult]:
        results = []
        for poi in pois:
            try:
                loc = poi.get("location", "")
                if not loc or "," not in loc:
                    continue
                lng_str, lat_str = loc.split(",")
                lat = float(lat_str)
                lng = float(lng_str)
                dist = _haversine(ref_lat, ref_lng, lat, lng)
                results.append(
                    POIResult(
                        poi_id=poi.get("id", ""),
                        name=poi.get("name", ""),
                        address=poi.get("address", "") if isinstance(poi.get("address"), str) else "",
                        latitude=lat,
                        longitude=lng,
                        city=poi.get("cityname", ""),
                        district=poi.get("adname", ""),
                        type_name=poi.get("type", ""),
                        distance=round(dist, 1),
                    )
                )
            except (ValueError, TypeError):
                continue
        return results


_singleton: Optional[POIService] = None


def get_poi_service() -> POIService:
    global _singleton
    if _singleton is None:
        _singleton = POIService()
    return _singleton
