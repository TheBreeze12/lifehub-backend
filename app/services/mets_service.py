"""
METs (Metabolic Equivalent of Task) 精准热量计算服务

METs值表基于《中国成人身体活动能量消耗参考手册》和《Compendium of Physical Activities》

公式：消耗热量(kcal) = METs × 体重(kg) × 时间(h)

Phase 19 实现
"""

from typing import Dict, List, Optional, Any


class METsService:
    """
    METs热量计算服务
    
    提供基于METs值的精准运动热量消耗计算
    """
    
    # 默认体重（kg），当用户未设置体重时使用
    DEFAULT_WEIGHT_KG = 70.0
    
    # METs值表：基于科学文献的运动代谢当量
    # 数据来源：Compendium of Physical Activities 和 中国成人身体活动能量消耗参考手册
    METS_TABLE: Dict[str, Dict[str, Any]] = {
        # 步行类
        "walking": {
            "mets": 3.5,
            "name_cn": "步行",
            "name_en": "Walking",
            "description": "普通速度步行（约4-5km/h）",
            "intensity": "light"
        },
        "brisk_walking": {
            "mets": 4.3,
            "name_cn": "快走",
            "name_en": "Brisk Walking",
            "description": "快速步行（约5.5-6.5km/h）",
            "intensity": "moderate"
        },
        "hiking": {
            "mets": 5.3,
            "name_cn": "徒步",
            "name_en": "Hiking",
            "description": "野外徒步、登山",
            "intensity": "moderate"
        },
        
        # 跑步类
        "running": {
            "mets": 8.0,
            "name_cn": "跑步",
            "name_en": "Running",
            "description": "中等速度跑步（约8km/h）",
            "intensity": "vigorous"
        },
        "jogging": {
            "mets": 7.0,
            "name_cn": "慢跑",
            "name_en": "Jogging",
            "description": "轻松慢跑（约6-7km/h）",
            "intensity": "moderate"
        },
        "sprint": {
            "mets": 12.0,
            "name_cn": "冲刺跑",
            "name_en": "Sprint",
            "description": "高强度冲刺跑",
            "intensity": "vigorous"
        },
        
        # 骑行类
        "cycling": {
            "mets": 6.0,
            "name_cn": "骑行",
            "name_en": "Cycling",
            "description": "普通速度骑自行车（约15-20km/h）",
            "intensity": "moderate"
        },
        "cycling_leisure": {
            "mets": 4.0,
            "name_cn": "休闲骑行",
            "name_en": "Leisure Cycling",
            "description": "休闲慢骑（约10-15km/h）",
            "intensity": "light"
        },
        "cycling_fast": {
            "mets": 10.0,
            "name_cn": "快速骑行",
            "name_en": "Fast Cycling",
            "description": "快速骑行（约25km/h以上）",
            "intensity": "vigorous"
        },
        
        # 游泳类
        "swimming": {
            "mets": 7.0,
            "name_cn": "游泳",
            "name_en": "Swimming",
            "description": "中等强度游泳",
            "intensity": "moderate"
        },
        "swimming_leisure": {
            "mets": 5.0,
            "name_cn": "休闲游泳",
            "name_en": "Leisure Swimming",
            "description": "轻松游泳/戏水",
            "intensity": "light"
        },
        "swimming_fast": {
            "mets": 10.0,
            "name_cn": "快速游泳",
            "name_en": "Fast Swimming",
            "description": "竞速游泳",
            "intensity": "vigorous"
        },
        
        # 健身房运动
        "gym": {
            "mets": 5.0,
            "name_cn": "健身房训练",
            "name_en": "Gym Workout",
            "description": "综合健身房训练",
            "intensity": "moderate"
        },
        "weight_training": {
            "mets": 5.0,
            "name_cn": "力量训练",
            "name_en": "Weight Training",
            "description": "举重/器械训练",
            "intensity": "moderate"
        },
        "aerobics": {
            "mets": 6.5,
            "name_cn": "有氧操",
            "name_en": "Aerobics",
            "description": "有氧健身操",
            "intensity": "moderate"
        },
        "yoga": {
            "mets": 2.5,
            "name_cn": "瑜伽",
            "name_en": "Yoga",
            "description": "瑜伽练习",
            "intensity": "light"
        },
        
        # 球类运动
        "basketball": {
            "mets": 6.5,
            "name_cn": "篮球",
            "name_en": "Basketball",
            "description": "打篮球",
            "intensity": "moderate"
        },
        "football": {
            "mets": 7.0,
            "name_cn": "足球",
            "name_en": "Football",
            "description": "踢足球",
            "intensity": "vigorous"
        },
        "badminton": {
            "mets": 5.5,
            "name_cn": "羽毛球",
            "name_en": "Badminton",
            "description": "打羽毛球",
            "intensity": "moderate"
        },
        "tennis": {
            "mets": 7.0,
            "name_cn": "网球",
            "name_en": "Tennis",
            "description": "打网球",
            "intensity": "moderate"
        },
        "table_tennis": {
            "mets": 4.0,
            "name_cn": "乒乓球",
            "name_en": "Table Tennis",
            "description": "打乒乓球",
            "intensity": "light"
        },
        
        # 场地类型（默认活动强度）
        "park": {
            "mets": 3.5,
            "name_cn": "公园活动",
            "name_en": "Park Activity",
            "description": "公园散步/活动",
            "intensity": "light"
        },
        "indoor": {
            "mets": 4.0,
            "name_cn": "室内运动",
            "name_en": "Indoor Activity",
            "description": "一般室内运动",
            "intensity": "light"
        },
        "outdoor": {
            "mets": 4.5,
            "name_cn": "室外运动",
            "name_en": "Outdoor Activity",
            "description": "一般室外运动",
            "intensity": "moderate"
        },
        
        # 其他运动
        "dancing": {
            "mets": 5.0,
            "name_cn": "跳舞",
            "name_en": "Dancing",
            "description": "一般舞蹈",
            "intensity": "moderate"
        },
        "stair_climbing": {
            "mets": 8.0,
            "name_cn": "爬楼梯",
            "name_en": "Stair Climbing",
            "description": "爬楼梯运动",
            "intensity": "vigorous"
        },
        "jumping_rope": {
            "mets": 11.0,
            "name_cn": "跳绳",
            "name_en": "Jumping Rope",
            "description": "跳绳运动",
            "intensity": "vigorous"
        },
        "tai_chi": {
            "mets": 3.0,
            "name_cn": "太极拳",
            "name_en": "Tai Chi",
            "description": "太极拳练习",
            "intensity": "light"
        },
        "stretching": {
            "mets": 2.3,
            "name_cn": "拉伸",
            "name_en": "Stretching",
            "description": "拉伸运动",
            "intensity": "light"
        },
    }
    
    # 中文到英文的映射
    CHINESE_MAPPING: Dict[str, str] = {
        "步行": "walking",
        "散步": "walking",
        "走路": "walking",
        "快走": "brisk_walking",
        "徒步": "hiking",
        "登山": "hiking",
        "跑步": "running",
        "慢跑": "jogging",
        "冲刺": "sprint",
        "骑行": "cycling",
        "骑车": "cycling",
        "骑自行车": "cycling",
        "游泳": "swimming",
        "健身": "gym",
        "健身房": "gym",
        "力量训练": "weight_training",
        "举重": "weight_training",
        "有氧": "aerobics",
        "瑜伽": "yoga",
        "篮球": "basketball",
        "足球": "football",
        "羽毛球": "badminton",
        "网球": "tennis",
        "乒乓球": "table_tennis",
        "公园": "park",
        "室内": "indoor",
        "室外": "outdoor",
        "户外": "outdoor",
        "跳舞": "dancing",
        "舞蹈": "dancing",
        "爬楼梯": "stair_climbing",
        "跳绳": "jumping_rope",
        "太极": "tai_chi",
        "太极拳": "tai_chi",
        "拉伸": "stretching",
    }
    
    # 默认METs值（用于未知运动类型）
    DEFAULT_METS = 3.5
    
    def __init__(self):
        """初始化METs服务"""
        # 构建完整的METs表（包含中英文键）
        self.mets_table = dict(self.METS_TABLE)
        
    def _normalize_exercise_type(self, exercise_type: str) -> str:
        """
        标准化运动类型名称
        
        Args:
            exercise_type: 运动类型（中文或英文）
            
        Returns:
            标准化后的英文运动类型
        """
        if not exercise_type:
            return "walking"
            
        # 转小写并去除空格
        normalized = exercise_type.lower().strip()
        
        # 检查是否是中文
        if normalized in self.CHINESE_MAPPING:
            return self.CHINESE_MAPPING[normalized]
            
        # 检查是否直接匹配英文
        if normalized in self.METS_TABLE:
            return normalized
            
        # 尝试部分匹配中文
        for cn_key, en_key in self.CHINESE_MAPPING.items():
            if cn_key in normalized or normalized in cn_key:
                return en_key
                
        # 尝试部分匹配英文
        for en_key in self.METS_TABLE.keys():
            if en_key in normalized or normalized in en_key:
                return en_key
                
        # 未找到匹配，返回原值
        return normalized
        
    def get_mets_value(self, exercise_type: str) -> float:
        """
        获取指定运动类型的METs值
        
        Args:
            exercise_type: 运动类型（支持中英文）
            
        Returns:
            METs值，未找到则返回默认值
        """
        normalized = self._normalize_exercise_type(exercise_type)
        
        if normalized in self.METS_TABLE:
            return self.METS_TABLE[normalized]["mets"]
            
        # 返回默认METs值
        return self.DEFAULT_METS
        
    def calculate_calories(
        self,
        exercise_type: str,
        weight_kg: Optional[float],
        duration_minutes: int
    ) -> float:
        """
        计算运动消耗的热量
        
        公式：消耗(kcal) = METs × 体重(kg) × 时间(h)
        
        Args:
            exercise_type: 运动类型
            weight_kg: 体重（kg），None时使用默认值
            duration_minutes: 运动时长（分钟）
            
        Returns:
            消耗热量（kcal）
        """
        # 处理无效时长
        if duration_minutes is None or duration_minutes <= 0:
            return 0.0
            
        # 使用默认体重如果未提供
        weight = weight_kg if weight_kg and weight_kg > 0 else self.DEFAULT_WEIGHT_KG
        
        # 获取METs值
        mets = self.get_mets_value(exercise_type)
        
        # 转换时间为小时
        duration_hours = duration_minutes / 60.0
        
        # 计算热量：METs × 体重(kg) × 时间(h)
        calories = mets * weight * duration_hours
        
        return round(calories, 1)
        
    def calculate_duration_for_target(
        self,
        exercise_type: str,
        weight_kg: Optional[float],
        target_calories: float
    ) -> int:
        """
        计算达到目标热量消耗所需的运动时长
        
        Args:
            exercise_type: 运动类型
            weight_kg: 体重（kg）
            target_calories: 目标消耗热量（kcal）
            
        Returns:
            所需时长（分钟）
        """
        if target_calories <= 0:
            return 0
            
        weight = weight_kg if weight_kg and weight_kg > 0 else self.DEFAULT_WEIGHT_KG
        mets = self.get_mets_value(exercise_type)
        
        # 反推时间：时间(h) = 热量 / (METs × 体重)
        duration_hours = target_calories / (mets * weight)
        duration_minutes = int(round(duration_hours * 60))
        
        return max(1, duration_minutes)  # 至少1分钟
        
    def get_all_exercise_types(self) -> List[str]:
        """
        获取所有支持的运动类型
        
        Returns:
            运动类型列表（英文）
        """
        return list(self.METS_TABLE.keys())
        
    def get_exercise_info(self, exercise_type: str) -> Dict[str, Any]:
        """
        获取运动类型的详细信息
        
        Args:
            exercise_type: 运动类型
            
        Returns:
            包含METs值、名称、描述等的字典
        """
        normalized = self._normalize_exercise_type(exercise_type)
        
        if normalized in self.METS_TABLE:
            info = dict(self.METS_TABLE[normalized])
            info["type"] = normalized
            return info
            
        # 返回默认信息
        return {
            "type": exercise_type,
            "mets": self.DEFAULT_METS,
            "name_cn": exercise_type,
            "name_en": exercise_type,
            "description": "未知运动类型",
            "intensity": "moderate"
        }
        
    def calculate_for_trip_item(
        self,
        trip_item: Dict[str, Any],
        weight_kg: Optional[float] = None
    ) -> float:
        """
        为运动计划项目计算热量消耗
        
        Args:
            trip_item: 运动项目数据，包含placeType、duration、notes等
            weight_kg: 用户体重
            
        Returns:
            热量消耗（kcal）
        """
        # 从placeType获取运动类型
        exercise_type = trip_item.get("placeType") or trip_item.get("place_type")
        duration = trip_item.get("duration")
        
        # 如果没有明确的运动类型，尝试从notes推断
        if not exercise_type:
            notes = trip_item.get("notes", "")
            exercise_type = self._infer_exercise_from_notes(notes)
            
        # 如果还是没有，使用默认
        if not exercise_type:
            exercise_type = "walking"
            
        return self.calculate_calories(exercise_type, weight_kg, duration or 0)
        
    def _infer_exercise_from_notes(self, notes: str) -> Optional[str]:
        """
        从notes字段推断运动类型
        
        Args:
            notes: 备注文本
            
        Returns:
            推断出的运动类型，未找到返回None
        """
        if not notes:
            return None
            
        notes_lower = notes.lower()
        
        # 关键词匹配
        keywords_map = {
            "running": ["跑步", "慢跑", "跑", "running", "jogging", "run"],
            "walking": ["散步", "步行", "走", "walking", "walk"],
            "cycling": ["骑行", "骑车", "自行车", "cycling", "bike"],
            "swimming": ["游泳", "swimming", "swim"],
            "gym": ["健身", "训练", "gym", "workout"],
            "yoga": ["瑜伽", "yoga"],
        }
        
        for exercise_type, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in notes_lower or keyword in notes:
                    return exercise_type
                    
        return None
        
    def recalculate_trip_items_calories(
        self,
        items: List[Dict[str, Any]],
        weight_kg: Optional[float]
    ) -> List[Dict[str, Any]]:
        """
        使用METs重新计算运动计划中所有项目的热量消耗
        
        Args:
            items: 运动项目列表
            weight_kg: 用户体重
            
        Returns:
            更新了热量的运动项目列表
        """
        result = []
        for item in items:
            item_copy = dict(item)
            # 使用METs计算热量
            calories = self.calculate_for_trip_item(item_copy, weight_kg)
            item_copy["cost"] = calories
            # 添加计算依据
            exercise_type = item_copy.get("placeType") or item_copy.get("place_type") or "walking"
            mets = self.get_mets_value(exercise_type)
            item_copy["mets_value"] = mets
            item_copy["calculation_basis"] = f"METs={mets} × {weight_kg or self.DEFAULT_WEIGHT_KG}kg × {(item_copy.get('duration') or 0)/60:.2f}h"
            result.append(item_copy)
        return result


# 单例实例
_mets_service_instance: Optional[METsService] = None


def get_mets_service() -> METsService:
    """获取METs服务单例"""
    global _mets_service_instance
    if _mets_service_instance is None:
        _mets_service_instance = METsService()
    return _mets_service_instance
