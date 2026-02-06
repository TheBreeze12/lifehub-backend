"""
天气动态调整服务 - Phase 32

根据天气状况评估是否适合户外运动，并在恶劣天气时生成室内替代方案（Plan B）。

天气数据来源：Open-Meteo API（WMO天气代码）
室内运动热量计算：基于METs公式（复用mets_service）
"""

from typing import Dict, List, Optional, Any
from app.services.mets_service import METsService


class WeatherService:
    """
    天气评估与Plan B生成服务
    
    职责：
    1. 根据WMO天气代码评估天气严重程度
    2. 综合温度、风速等因素判断是否适合户外运动
    3. 在恶劣天气时生成室内替代运动方案
    """

    # 默认体重（kg）
    DEFAULT_WEIGHT_KG = 70.0

    # 极端温度阈值
    EXTREME_COLD_THRESHOLD = -10.0  # ℃
    EXTREME_HEAT_THRESHOLD = 38.0   # ℃
    # 大风阈值（km/h）
    HIGH_WIND_THRESHOLD = 50.0

    # WMO天气代码分类
    # severity: good / mild / moderate / severe
    WEATHER_CODE_MAP: Dict[int, Dict[str, str]] = {
        # 晴朗/多云
        0:  {"severity": "good",     "description": "晴天"},
        1:  {"severity": "good",     "description": "大部晴朗"},
        2:  {"severity": "good",     "description": "局部多云"},
        3:  {"severity": "good",     "description": "阴天"},
        # 雾
        45: {"severity": "mild",     "description": "雾"},
        48: {"severity": "mild",     "description": "雾凇"},
        # 毛毛雨
        51: {"severity": "mild",     "description": "小毛毛雨"},
        53: {"severity": "moderate", "description": "中毛毛雨"},
        55: {"severity": "moderate", "description": "密集毛毛雨"},
        # 冻毛毛雨
        56: {"severity": "moderate", "description": "轻度冻毛毛雨"},
        57: {"severity": "severe",   "description": "重度冻毛毛雨"},
        # 降雨
        61: {"severity": "mild",     "description": "小雨"},
        63: {"severity": "moderate", "description": "中雨"},
        65: {"severity": "severe",   "description": "大雨"},
        # 冻雨
        66: {"severity": "severe",   "description": "轻度冻雨"},
        67: {"severity": "severe",   "description": "重度冻雨"},
        # 降雪
        71: {"severity": "mild",     "description": "小雪"},
        73: {"severity": "moderate", "description": "中雪"},
        75: {"severity": "severe",   "description": "大雪"},
        # 霰
        77: {"severity": "moderate", "description": "霰（雪粒）"},
        # 阵雨
        80: {"severity": "mild",     "description": "小阵雨"},
        81: {"severity": "moderate", "description": "中阵雨"},
        82: {"severity": "severe",   "description": "暴雨"},
        # 阵雪
        85: {"severity": "moderate", "description": "小阵雪"},
        86: {"severity": "severe",   "description": "大阵雪"},
        # 雷暴
        95: {"severity": "severe",   "description": "雷暴"},
        96: {"severity": "severe",   "description": "雷暴伴冰雹（轻）"},
        99: {"severity": "severe",   "description": "雷暴伴冰雹（重）"},
    }

    # 室内替代运动数据库
    INDOOR_EXERCISES: List[Dict[str, Any]] = [
        {
            "name": "室内跳绳",
            "type": "jumping_rope",
            "mets": 11.0,
            "description": "高效室内有氧运动，燃脂效果好",
        },
        {
            "name": "有氧健身操",
            "type": "aerobics",
            "mets": 6.5,
            "description": "跟随视频进行有氧健身操训练",
        },
        {
            "name": "瑜伽",
            "type": "yoga",
            "mets": 2.5,
            "description": "瑜伽练习，适合放松与柔韧性训练",
        },
        {
            "name": "力量训练",
            "type": "weight_training",
            "mets": 5.0,
            "description": "哑铃或自重力量训练",
        },
        {
            "name": "室内骑行（动感单车）",
            "type": "cycling",
            "mets": 6.0,
            "description": "使用动感单车进行室内骑行训练",
        },
        {
            "name": "爬楼梯",
            "type": "stair_climbing",
            "mets": 8.0,
            "description": "在楼梯间进行爬楼梯运动",
        },
        {
            "name": "健身房综合训练",
            "type": "gym",
            "mets": 5.0,
            "description": "健身房器械+有氧综合训练",
        },
        {
            "name": "拉伸运动",
            "type": "stretching",
            "mets": 2.3,
            "description": "全身拉伸放松，适合低强度需求",
        },
        {
            "name": "室内跑步机",
            "type": "running",
            "mets": 8.0,
            "description": "跑步机上中速跑步",
        },
        {
            "name": "太极拳",
            "type": "tai_chi",
            "mets": 3.0,
            "description": "太极拳练习，适合舒缓运动",
        },
        {
            "name": "舞蹈",
            "type": "dancing",
            "mets": 5.0,
            "description": "跟随音乐进行舞蹈运动",
        },
        {
            "name": "室内乒乓球",
            "type": "table_tennis",
            "mets": 4.0,
            "description": "室内乒乓球运动",
        },
    ]

    def __init__(self):
        """初始化天气服务"""
        self.mets_service = METsService()

    def evaluate_weather_code(self, weathercode: int) -> Dict[str, str]:
        """
        评估单个WMO天气代码

        Args:
            weathercode: WMO天气代码

        Returns:
            包含 severity 和 description 的字典
        """
        if weathercode in self.WEATHER_CODE_MAP:
            return dict(self.WEATHER_CODE_MAP[weathercode])
        # 未知代码默认好天气
        return {"severity": "good", "description": f"未知天气（代码{weathercode}）"}

    def is_bad_weather(self, weathercode: int) -> bool:
        """
        快速判断是否为恶劣天气（moderate 或 severe）

        Args:
            weathercode: WMO天气代码

        Returns:
            True 表示恶劣天气，需要Plan B
        """
        info = self.evaluate_weather_code(weathercode)
        return info["severity"] in ("moderate", "severe")

    def evaluate_weather(self, weather_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        综合评估天气状况（天气代码 + 温度 + 风速）

        Args:
            weather_data: Open-Meteo返回的天气数据字典，包含：
                - weathercode: WMO天气代码
                - temperature: 温度（℃）
                - windspeed: 风速（km/h）

        Returns:
            评估结果字典，包含：
                - is_bad_weather: 是否恶劣天气
                - severity: good/mild/moderate/severe/unknown
                - description: 中文天气描述
                - recommendation: 建议
                - temperature_warning: 温度警告（可选）
                - wind_warning: 风速警告（可选）
        """
        if weather_data is None:
            return {
                "is_bad_weather": False,
                "severity": "unknown",
                "description": "无法获取天气数据",
                "recommendation": "建议出门前查看天气情况",
            }

        weathercode = weather_data.get("weathercode")
        temperature = weather_data.get("temperature")
        windspeed = weather_data.get("windspeed")

        # 1. 评估天气代码
        if weathercode is not None:
            code_eval = self.evaluate_weather_code(weathercode)
        else:
            code_eval = {"severity": "good", "description": "天气信息不完整"}

        severity = code_eval["severity"]
        description = code_eval["description"]
        warnings = []

        # 2. 温度评估
        if temperature is not None:
            if temperature <= self.EXTREME_COLD_THRESHOLD:
                severity = self._max_severity(severity, "severe")
                warnings.append(f"极端低温（{temperature}℃），不适合户外运动")
            elif temperature >= self.EXTREME_HEAT_THRESHOLD:
                severity = self._max_severity(severity, "severe")
                warnings.append(f"极端高温（{temperature}℃），有中暑风险")

        # 3. 风速评估
        if windspeed is not None:
            if windspeed >= self.HIGH_WIND_THRESHOLD:
                severity = self._max_severity(severity, "moderate")
                warnings.append(f"大风（{windspeed}km/h），户外运动有安全隐患")

        # 4. 生成建议
        is_bad = severity in ("moderate", "severe")
        if severity == "severe":
            recommendation = "天气恶劣，强烈建议改为室内运动"
        elif severity == "moderate":
            recommendation = "天气不佳，建议改为室内运动"
        elif severity == "mild":
            recommendation = "天气尚可，建议根据自身情况决定是否户外运动"
        else:
            recommendation = "天气良好，适合户外运动"

        result = {
            "is_bad_weather": is_bad,
            "severity": severity,
            "description": description,
            "recommendation": recommendation,
        }

        if warnings:
            result["warnings"] = warnings
            # 有温度或风速警告时也标记为恶劣
            if any("温" in w for w in warnings):
                result["temperature_warning"] = next(w for w in warnings if "温" in w)
            if any("风" in w for w in warnings):
                result["wind_warning"] = next(w for w in warnings if "风" in w)

        return result

    def get_indoor_exercises(self) -> List[Dict[str, Any]]:
        """
        获取所有室内替代运动列表

        Returns:
            室内运动列表，每项包含 name, type, mets, description
        """
        return list(self.INDOOR_EXERCISES)

    def generate_plan_b(
        self,
        original_items: List[Dict[str, Any]],
        weight_kg: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        根据原运动计划生成室内替代方案（Plan B）

        策略：
        1. 计算原计划总热量目标
        2. 从室内运动库中选择合适的替代运动
        3. 计算每项替代运动的时长使其总热量接近原计划

        Args:
            original_items: 原运动项目列表（包含 place_type, duration, cost 等）
            weight_kg: 用户体重（kg）

        Returns:
            包含 alternatives 列表的字典
        """
        weight = weight_kg if weight_kg and weight_kg > 0 else self.DEFAULT_WEIGHT_KG

        # 计算原计划总热量（取cost字段作为热量）
        total_target_calories = 0.0
        for item in original_items:
            cost = item.get("cost", 0)
            if cost and cost > 0:
                total_target_calories += cost

        # 如果原计划无有效热量，给一个默认目标（30分钟步行的热量）
        if total_target_calories <= 0:
            total_target_calories = self.mets_service.calculate_calories("walking", weight, 30)

        # 从室内运动库中选择替代方案
        alternatives = self._select_indoor_alternatives(total_target_calories, weight)

        return {
            "original_total_calories": round(total_target_calories, 1),
            "alternatives": alternatives,
            "plan_b_total_calories": round(
                sum(alt["calories"] for alt in alternatives), 1
            ),
        }

    def _select_indoor_alternatives(
        self,
        target_calories: float,
        weight_kg: float,
    ) -> List[Dict[str, Any]]:
        """
        选择室内替代运动，使总热量接近目标

        策略：
        - 选择2-3种不同运动类型以增加多样性
        - 优先选择中等强度运动
        - 确保总时长合理

        Args:
            target_calories: 目标热量（kcal）
            weight_kg: 体重（kg）

        Returns:
            替代运动列表
        """
        if target_calories <= 0:
            return []

        # 按METs从中等到高排序，优先选中等强度
        sorted_exercises = sorted(
            self.INDOOR_EXERCISES,
            key=lambda x: abs(x["mets"] - 5.0),  # 优先选METs接近5的中等强度
        )

        alternatives = []
        remaining_calories = target_calories
        used_types = set()

        for exercise in sorted_exercises:
            if remaining_calories <= 0:
                break
            if exercise["type"] in used_types:
                continue
            if len(alternatives) >= 3:
                break

            # 计算达到剩余热量所需时长
            mets = exercise["mets"]
            # 时间(h) = 热量 / (METs × 体重)
            needed_hours = remaining_calories / (mets * weight_kg)
            needed_minutes = round(needed_hours * 60)

            # 限制单项运动时长为10-90分钟
            needed_minutes = max(10, min(90, needed_minutes))

            # 实际消耗热量
            actual_calories = round(mets * weight_kg * (needed_minutes / 60.0), 1)

            alternatives.append({
                "exercise_name": exercise["name"],
                "exercise_type": exercise["type"],
                "duration": needed_minutes,
                "calories": actual_calories,
                "is_indoor": True,
                "description": exercise["description"],
                "mets_value": mets,
            })

            used_types.add(exercise["type"])
            remaining_calories -= actual_calories

        return alternatives

    @staticmethod
    def _max_severity(a: str, b: str) -> str:
        """返回两个严重度中较高的一个"""
        order = {"good": 0, "mild": 1, "moderate": 2, "severe": 3, "unknown": 0}
        return a if order.get(a, 0) >= order.get(b, 0) else b


# 单例
_weather_service_instance: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    """获取天气服务单例"""
    global _weather_service_instance
    if _weather_service_instance is None:
        _weather_service_instance = WeatherService()
    return _weather_service_instance
