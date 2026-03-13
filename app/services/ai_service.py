"""
AI服务 - 调用通义千问API（行程生成）和火山引擎豆包AI（菜品识别和分析）
"""
import os
import json
import re
import base64
import time
import tempfile
import logging
from typing import List, Optional, Tuple, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import dashscope
from dashscope import Generation

logger = logging.getLogger(__name__)

# Phase 57: Few-shot Prompt模板服务（延迟导入，避免循环依赖）
_prompt_template_service = None
def _get_prompt_tpl_service():
    """延迟获取Prompt模板服务单例"""
    global _prompt_template_service
    if _prompt_template_service is None:
        try:
            from app.services.prompt_template_service import get_prompt_template_service
            _prompt_template_service = get_prompt_template_service()
        except Exception as e:
            logger.warning(f"Prompt模板服务初始化失败，将使用硬编码Prompt: {e}")
    return _prompt_template_service

# 尝试导入地理编码库（可选）
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    GEOCODING_AVAILABLE = True
except ImportError:
    GEOCODING_AVAILABLE = False
    print("警告: 未安装geopy，地理编码功能将不可用，将使用经纬度坐标")

# 尝试导入火山引擎SDK（可选）
try:
    from volcenginesdkarkruntime import Ark
    ARK_AVAILABLE = True
except ImportError:
    try:
        # 尝试备用导入方式
        from volcengine.ark import Ark
        ARK_AVAILABLE = True
    except ImportError:
        ARK_AVAILABLE = False
        print("警告: 未安装volcengine-python-sdk[ark]，菜单识别功能将不可用")


class AIService:
    """AI服务类，封装AI API调用"""
    
    def __init__(self):
        """初始化AI服务"""
        # 初始化通义千问（用于行程生成等）
        dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        if not dashscope_api_key:
            raise ValueError("未设置DASHSCOPE_API_KEY环境变量")
        dashscope.api_key = dashscope_api_key
        
        # 初始化火山引擎豆包AI（用于菜单识别和菜品分析）
        self.ark_client = None
        if ARK_AVAILABLE:
            ark_api_key = os.getenv("ARK_API_KEY")
            if ark_api_key:
                try:
                    self.ark_client = Ark(
                        base_url='https://ark.cn-beijing.volces.com/api/v3',
                        api_key=ark_api_key,
                    )
                    print("✓ 火山引擎豆包AI初始化成功")
                except Exception as e:
                    print(f"警告: 火山引擎豆包AI初始化失败: {e}")
                    print("菜品识别和分析功能将不可用")
            else:
                print("警告: 未设置ARK_API_KEY，菜单识别功能将不可用")
        
        # 初始化地理编码器（用于将经纬度转换为地理位置）
        self.geocoder = None
        if GEOCODING_AVAILABLE:
            try:
                # 使用Nominatim服务（免费，无需API key）
                self.geocoder = Nominatim(user_agent="lifehub_app")
                print("✓ 地理编码服务初始化成功")
            except Exception as e:
                print(f"警告: 地理编码服务初始化失败: {e}")
                print("将使用经纬度坐标，不进行地理编码")

    def _log_ai_call(
        self,
        call_type: str,
        model_name: str,
        input_summary: str,
        success: bool,
        latency_ms: int,
        user_id: Optional[int] = None,
        output_summary: Optional[str] = None,
        error_message: Optional[str] = None,
        token_usage: Optional[int] = None,
    ) -> None:
        """Phase 56: 记录AI调用日志（使用独立DB会话，不影响主流程）"""
        try:
            from app.database import SessionLocal
            from app.services.ai_log_service import get_ai_log_service
            db = SessionLocal()
            try:
                ai_log_service = get_ai_log_service()
                ai_log_service.log_ai_call(
                    db=db,
                    call_type=call_type,
                    model_name=model_name,
                    input_summary=input_summary,
                    success=success,
                    latency_ms=latency_ms,
                    user_id=user_id,
                    output_summary=output_summary,
                    error_message=error_message,
                    token_usage=token_usage,
                )
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"AI调用日志记录失败: {e}")

    def geocode_address(self, address: str) -> Optional[Dict[str, float]]:
        """将地址文本转为经纬度坐标"""
        if not address:
            return None
        try:
            if self.geocoder:
                loc = self.geocoder.geocode(address, timeout=5, language='zh')
                if loc:
                    return {"latitude": loc.latitude, "longitude": loc.longitude}
            # geopy不可用或失败时返回None
            return None
        except Exception as e:
            print(f"地址地理编码失败: {str(e)}")
            return None

    def get_weather_by_address(self, address: str) -> dict:
        """根据地址获取当前天气，使用 Open-Meteo（无需API Key）"""
        if not address:
            raise ValueError("地址不能为空")
        coords = self.geocode_address(address)
        if not coords:
            raise ValueError("无法解析地址为坐标，请提供更精确的地址")
        print(coords)
        lat = coords["latitude"]
        lon = coords["longitude"]
        return self.get_weather_by_coords(lat, lon, address_hint=address)

    def get_weather_by_coords(self, latitude: float, longitude: float, address_hint: str | None = None) -> dict:
        """根据经纬度获取当前天气，使用 Open-Meteo（无需API Key）"""
        import requests
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}&longitude={longitude}&current_weather=true&hourly=temperature_2m,precipitation"
        )
        try:
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            current = data.get("current_weather", {})
            result = {
                "address": address_hint,
                "latitude": latitude,
                "longitude": longitude,
                "temperature": current.get("temperature"),
                "windspeed": current.get("windspeed"),
                "winddirection": current.get("winddirection"),
                "weathercode": current.get("weathercode"),
                "time": current.get("time"),
            }
            hourly = data.get("hourly", {})
            result["hourly"] = {
                "time": hourly.get("time", [])[:6],
                "temperature_2m": hourly.get("temperature_2m", [])[:6],
                "precipitation": hourly.get("precipitation", [])[:6],
            }
            return result
        except Exception as e:
            print(f"天气API请求失败: {str(e)}")
            raise
    
    def analyze_food_nutrition(self, food_name: str) -> dict:
        """
        分析菜品营养成分（使用豆包AI + RAG检索增强）
        
        Phase 38增强：先通过RAG检索《中国食物成分表》获取参考数据，
        将检索结果作为上下文注入LLM Prompt，减少幻觉，提升准确性。
        
        Args:
            food_name: 菜品名称
            
        Returns:
            包含营养数据的字典
            
        Raises:
            ValueError: 如果豆包AI未初始化或调用失败
        """
        if not self.ark_client:
            raise ValueError("豆包AI未初始化，请检查ARK_API_KEY环境变量")
        
        # Phase 38: RAG检索营养知识上下文
        rag_context = ""
        try:
            from app.services.nutrition_rag_service import get_nutrition_rag_service
            rag_service = get_nutrition_rag_service()
            rag_context = rag_service.get_nutrition_context(food_name, top_k=3)
            if rag_context:
                print(f"✓ RAG检索到营养知识上下文: {food_name}")
        except Exception as e:
            print(f"警告: RAG检索失败，将仅使用LLM分析: {e}")
            rag_context = ""
        
        return self._analyze_food_nutrition_with_ark(food_name, rag_context=rag_context)
    
    def _analyze_food_nutrition_with_ark(self, food_name: str, rag_context: str = "") -> dict:
        """使用豆包AI分析菜品营养（Phase 38: 支持RAG上下文注入）"""
        prompt = self._build_nutrition_prompt(food_name, rag_context=rag_context)
        
        start_time = time.time()
        try:
            response = self.ark_client.responses.create(
                model="doubao-seed-1-6-251015",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            # 解析响应 - 从output列表项的content[0].text获取内容
            content = None
            
            if hasattr(response, 'output') and response.output:
                output = response.output
                # 如果output是列表，从列表项的content[0].text获取
                if isinstance(output, list) and len(output) > 0:
                    for item in output:
                        if hasattr(item, 'content') and item.content:
                            item_content = item.content
                            # 如果content是列表，从第一个元素的text字段获取
                            if isinstance(item_content, list) and len(item_content) > 0:
                                sub_item = item_content[0]
                                if hasattr(sub_item, 'text') and sub_item.text:
                                    content = sub_item.text
                                    break
                            # 如果content是字符串，直接使用
                            elif isinstance(item_content, str):
                                content = item_content
                                break
            
            latency_ms = int((time.time() - start_time) * 1000)
            if content:
                result = self._parse_nutrition_response(content, food_name)
                # Phase 56: 记录成功的AI调用
                self._log_ai_call(
                    call_type="food_analysis",
                    model_name="doubao-seed-1-6-251015",
                    input_summary=food_name,
                    success=True,
                    latency_ms=latency_ms,
                    output_summary=f"calories={result.get('calories')}, protein={result.get('protein')}",
                )
                return result
            else:
                raise Exception("豆包AI返回空响应")
                
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            # Phase 56: 记录失败的AI调用
            self._log_ai_call(
                call_type="food_analysis",
                model_name="doubao-seed-1-6-251015",
                input_summary=food_name,
                success=False,
                latency_ms=latency_ms,
                error_message=str(e),
            )
            print(f"豆包AI调用失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _build_nutrition_prompt(self, food_name: str, rag_context: str = "") -> str:
        """
        构建营养分析Prompt（含过敏原推理 + RAG上下文）
        
        Phase 7增强：在营养分析中同时进行隐性过敏原AI推理
        Phase 38增强：注入RAG检索的营养知识上下文，提升数据准确性
        Phase 57增强：使用Few-shot Prompt模板服务构建prompt
        """
        # Phase 57: 尝试使用模板服务构建prompt
        tpl_svc = _get_prompt_tpl_service()
        if tpl_svc is not None:
            try:
                rag_section = ""
                if rag_context:
                    rag_section = f"\n\n{rag_context}\n\n重要：请优先参考以上《中国食物成分表》数据给出营养分析，确保数据尽量准确。\n"
                rendered = tpl_svc.render_prompt("food_analysis", variables={
                    "food_name": food_name,
                    "rag_context": rag_section,
                })
                # 将few-shot示例内联到prompt文本中（豆包AI使用单prompt模式）
                parts = [rendered["system_prompt"], ""]
                for i in range(0, len(rendered["few_shot_messages"]), 2):
                    user_msg = rendered["few_shot_messages"][i]["content"]
                    asst_msg = rendered["few_shot_messages"][i + 1]["content"] if i + 1 < len(rendered["few_shot_messages"]) else ""
                    parts.append(f"示例输入：{user_msg}")
                    parts.append(f"示例输出：{asst_msg}")
                    parts.append("")
                parts.append(rendered["user_prompt"])
                return "\n".join(parts)
            except Exception as e:
                logger.warning(f"模板服务渲染food_analysis失败，回退硬编码: {e}")

        # 回退：原始硬编码prompt
        rag_section = ""
        if rag_context:
            rag_section = f"""\n\n{rag_context}\n\n重要：请优先参考以上《中国食物成分表》数据给出营养分析，确保数据尽量准确。\n"""
        
        prompt = f"""请分析菜品"{food_name}"的营养成分和可能的过敏原，并以JSON格式返回。
{rag_section}
要求：
1. 估算每100克的营养数据
2. 给出减脂人群的饮食建议
3. 分析该菜品可能包含的八大类过敏原（乳制品、鸡蛋、鱼类、甲壳类、花生、树坚果、小麦、大豆）
4. 特别注意推理隐性过敏原
5. 只返回JSON，不要其他解释
6. 如果有参考数据，营养数值应与参考数据接近
7. 列出该食材/菜品在2-4种不同烹饪方式下的热量和脂肪对比

八大类过敏原代码对照：
- milk: 乳制品  - egg: 鸡蛋  - fish: 鱼类  - shellfish: 甲壳类
- peanut: 花生  - tree_nut: 树坚果  - wheat: 小麦  - soy: 大豆

返回格式：
{{
    "calories": 热量数值, "protein": 蛋白质数值, "fat": 脂肪数值, "carbs": 碳水数值,
    "recommendation": "建议", "allergens": ["代码"], "allergen_reasoning": "推理说明",
    "cooking_method_comparisons": [{{"method": "方式", "calories": 数值, "fat": 数值, "description": "说明"}}]
}}

现在请分析"{food_name}"："""
        
        return prompt
    
    def _parse_nutrition_response(self, content: str, food_name: str) -> dict:
        """
        解析AI返回的营养数据（含过敏原推理）
        
        Phase 7增强：解析AI返回的过敏原推理结果
        """
        try:
            # 尝试从内容中提取JSON
            # 有时AI会返回带有额外文字的内容，需要提取JSON部分
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                # 确保所有必需字段存在（包括过敏原字段）
                result = {
                    "name": food_name,
                    "calories": float(data.get("calories", 150.0)),
                    "protein": float(data.get("protein", 10.0)),
                    "fat": float(data.get("fat", 8.0)),
                    "carbs": float(data.get("carbs", 15.0)),
                    "recommendation": data.get("recommendation", "营养数据仅供参考"),
                    # Phase 7: 过敏原推理字段
                    "allergens": data.get("allergens", []),
                    "allergen_reasoning": data.get("allergen_reasoning", ""),
                    # Phase 50: 烹饪方式热量差异对比
                    "cooking_method_comparisons": data.get("cooking_method_comparisons", [])
                }
                
                # 验证过敏原代码是否为有效的八大类
                valid_allergen_codes = {"milk", "egg", "fish", "shellfish", "peanut", "tree_nut", "wheat", "soy"}
                if result["allergens"]:
                    # 过滤掉无效的过敏原代码
                    result["allergens"] = [
                        a for a in result["allergens"] 
                        if isinstance(a, str) and a.lower() in valid_allergen_codes
                    ]
                    # 统一转为小写
                    result["allergens"] = [a.lower() for a in result["allergens"]]
                
                return result
            else:
                raise ValueError("未找到JSON数据")
                
        except Exception as e:
            print(f"解析AI响应失败: {str(e)}")
            print(f"原始内容: {content}")
            return self._get_default_nutrition(food_name)
    
    def _get_default_nutrition(self, food_name: str) -> dict:
        """返回默认营养数据（当AI调用失败时）"""
        return {
            "name": food_name,
            "calories": 0.0,
            "protein": 0.0,
            "fat": 0.0,
            "carbs": 0.0,
            "recommendation": f"{food_name}的营养数据暂时无法获取，建议适量食用。",
            # Phase 7: 过敏原推理字段（默认值）
            "allergens": [],
            "allergen_reasoning": "",
            # Phase 50: 烹饪方式对比（默认值）
            "cooking_method_comparisons": []
        }
    
    def generate_trip(self, query: str, preferences: dict = None, calories_intake: float = 0.0, user_location: dict = None) -> dict:
        """
        生成运动计划（餐后运动规划）
        
        Args:
            query: 用户查询文本（如"规划餐后运动，消耗300卡路里"）
            preferences: 用户偏好（健康目标、过敏原等）
            calories_intake: 今日已摄入卡路里
            user_location: 用户位置信息 {"latitude": float, "longitude": float}
            
        Returns:
            包含运动计划数据的字典
        """
        # 第一步：提取运动意图
        intent = self._extract_exercise_intent(query, preferences, calories_intake, user_location)
        
        # 第二步：生成运动计划
        trip_data = self._generate_exercise_plan(intent, preferences, calories_intake, user_location, query)
        
        # 第三步：POI增强 - 用真实地点替换LLM虚构地点
        trip_data = self._enrich_plan_with_poi(trip_data, user_location)
        
        return trip_data
    
    def _reverse_geocode(self, latitude: float, longitude: float) -> Optional[Dict[str, str]]:
        """逆地理编码：优先高德，失败后回退 Nominatim。"""
        amap_key = os.getenv("AMAP_KEY", "")

        # 1) 优先高德逆地理编码（与POI来源一致，稳定性更高）
        if amap_key:
            try:
                import requests
                url = "https://restapi.amap.com/v3/geocode/regeo"
                params = {
                    "key": amap_key,
                    "location": f"{longitude},{latitude}",
                    "extensions": "base",
                    "output": "json",
                }
                resp = requests.get(url, params=params, timeout=8)
                data = resp.json()
                if data.get("status") == "1":
                    regeocode = data.get("regeocode", {}) or {}
                    addr = regeocode.get("addressComponent", {}) or {}
                    city_value = addr.get("city")
                    if isinstance(city_value, list):
                        city_value = city_value[0] if city_value else ""
                    city = city_value or addr.get("province") or ""
                    district = addr.get("district") or ""
                    province = addr.get("province") or ""
                    full_address = regeocode.get("formatted_address") or ""
                    return {
                        "city": city,
                        "district": district,
                        "province": province,
                        "country": "中国",
                        "full_address": full_address,
                    }
                logger.warning(f"高德逆地理编码失败: {data.get('info')}")
            except Exception as e:
                logger.warning(f"高德逆地理编码异常: {e}")

        # 2) 回退到Nominatim
        if not self.geocoder:
            return None

        try:
            location = self.geocoder.reverse((latitude, longitude), timeout=8, language="zh")
            if location:
                raw = getattr(location, "raw", {}) or {}
                address = raw.get("address", {}) if isinstance(raw.get("address", {}), dict) else {}
                city = address.get("city") or address.get("town") or address.get("village") or address.get("municipality") or ""
                district = address.get("suburb") or address.get("district") or address.get("county") or ""
                province = address.get("state") or address.get("province") or address.get("region") or ""
                country = address.get("country") or ""
                full_address = location.address or (raw.get("display_name") or "")
                return {
                    "city": city,
                    "district": district,
                    "province": province,
                    "country": country,
                    "full_address": full_address,
                }
        except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
            logger.warning(f"Nominatim逆地理编码失败: {e}")
            return None

        return None

    def _build_exercise_location_hint(self, user_location: Optional[dict]) -> Tuple[str, Optional[Dict[str, str]]]:
        """构建运动意图提取阶段的位置信息提示，并返回geo_info。"""
        if not user_location:
            return "", None

        lat = user_location.get("latitude")
        lon = user_location.get("longitude")
        if lat is None or lon is None:
            return "", None

        geo_info = self._reverse_geocode(lat, lon)
        if geo_info:
            location_parts = [
                geo_info.get("city"),
                geo_info.get("district"),
                geo_info.get("province"),
            ]
            location_desc = "、".join([part for part in location_parts if part]) or geo_info.get("full_address", "")
            hint = f"""
用户GPS位置：纬度 {lat:.6f}, 经度 {lon:.6f}
逆地理编码结果：{location_desc}
"""
            return hint, geo_info

        hint = f"""
用户GPS位置：纬度 {lat:.6f}, 经度 {lon:.6f}
逆地理编码结果不可用，请根据经纬度推断运动区域。
"""
        return hint, None

    def _destination_from_geo_info(self, geo_info: Optional[Dict[str, str]]) -> Optional[str]:
        """根据geo_info生成稳定的destination（不依赖LLM）。"""
        if not geo_info:
            return None
        city = (geo_info.get("city") or "").strip()
        district = (geo_info.get("district") or "").strip()
        province = (geo_info.get("province") or "").strip()
        full_address = (geo_info.get("full_address") or "").strip()
        if city and district:
            return f"{city}{district}"
        if city:
            return city
        if district:
            return district
        if province:
            return province
        return full_address or None

    def _build_default_exercise_intent(self, calories_intake: float, user_location: Optional[dict]) -> dict:
        """构建意图提取失败时的默认值。"""
        from datetime import datetime

        today = datetime.now().date()
        calories_target = int(calories_intake * 0.4) if calories_intake > 0 else 200
        default_destination = "当前位置附近" if user_location else "附近"
        return {
            "destination": default_destination,
            "startDate": today.strftime("%Y-%m-%d"),
            "endDate": today.strftime("%Y-%m-%d"),
            "days": 1,
            "calories_target": calories_target,
            "exercise_type": None,
            "duration_minutes": None,
            "intensity": None,
        }

    @staticmethod
    def _parse_total_duration_from_query(query: str) -> Optional[int]:
        """从 query 中解析所有时长并求和。

        支持格式：X分钟 / Xmin / X小时 / X个小时 / Xh
        """
        if not query:
            return None
        total = 0
        for m in re.finditer(r"(\d+)\s*(?:分钟|min(?:ute)?s?)", query, re.IGNORECASE):
            total += int(m.group(1))
        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:小时|个小时|h(?:our)?s?)", query, re.IGNORECASE):
            total += int(float(m.group(1)) * 60)
        return total if total > 0 else None

    def _normalize_exercise_intent(
        self,
        intent: dict,
        calories_intake: float,
        query: str,
        user_location: Optional[dict],
    ) -> dict:
        """对模型返回的运动意图进行规则化，提升稳定性。"""
        intent = self._fix_date_and_days(intent)

        if not intent.get("calories_target"):
            intent["calories_target"] = int(calories_intake * 0.4) if calories_intake > 0 else 200

        if not intent.get("destination"):
            intent["destination"] = None

        duration = intent.get("duration_minutes")
        if isinstance(duration, str):
            m = re.search(r"(\d+)", duration)
            duration = int(m.group(1)) if m else None
        if not isinstance(duration, int) or duration <= 0:
            duration = self._parse_total_duration_from_query(query)
        intent["duration_minutes"] = duration

        intensity = intent.get("intensity")
        if intensity not in {"低", "中", "高"}:
            et = (intent.get("exercise_type") or "").lower()
            if et in {"walking", "tai_chi"}:
                intensity = "低"
            elif et in {"jogging", "cycling", "yoga"}:
                intensity = "中"
            elif et in {"running", "swimming", "hiit"}:
                intensity = "高"
            else:
                intensity = None
        intent["intensity"] = intensity

        return intent
    
    def _extract_exercise_intent(self, query: str, preferences: dict = None, calories_intake: float = 0.0, user_location: dict = None) -> dict:
        """提取运动意图（简化版：经纬度优先 + 规则校验兜底）。"""
        calories_info = f"\n用户今日已摄入卡路里：{calories_intake:.1f} kcal"
        from datetime import datetime
        today_str = datetime.now().date().strftime("%Y-%m-%d")

        # 仅依赖GPS上下文，并将geo_info传递给下一阶段，避免LLM生成destination造成幻觉
        location_hint, geo_info = self._build_exercise_location_hint(user_location)
        stable_destination = self._destination_from_geo_info(geo_info)
        
        prompt = f"""请从以下用户查询中提取餐后运动规划的关键信息，并以JSON格式返回。

用户查询："{query}"
{calories_info}
{location_hint}

系统当前日期：{today_str}

要求提取的信息：
1. startDate: 运动开始日期（YYYY-MM-DD格式）
2. endDate: 运动结束日期（YYYY-MM-DD格式）
3. days: 运动天数（整数）
4. calories_target: 目标消耗卡路里（整数，单位：kcal，如果未指定则根据已摄入卡路里推算）
5. exercise_type: 运动类型偏好（如"散步"、"跑步"、"骑行"、"游泳"等，如果未指定则为null）
6. duration_minutes: 期望运动时长（整数，分钟，如"30分钟"→30，未指定则为null）
7. intensity: 运动强度（"低"/"中"/"高"，根据运动类型和用户描述推断，未指定则为null）

强度推断规则：
- 散步/太极 → 低强度
- 慢跑/骑行/瑜伽 → 中强度
- 跑步/游泳/HIIT → 高强度
- 用户明确说"中等强度"、"高强度"等，直接使用

仅返回JSON对象，不要其他解释或Markdown。

严格禁止抄写任何示例值（尤其是日期）。startDate/endDate 必须根据用户查询或当前系统日期 {today_str} 计算。
"""
        
        # Phase 57: 尝试使用模板服务构建意图提取prompt
        tpl_svc = _get_prompt_tpl_service()
        if tpl_svc is not None:
            try:
                rendered = tpl_svc.render_prompt("exercise_intent", variables={
                    "query": query,
                    "calories_info": calories_info,
                    "explicit_place_hint": "",
                    "location_hint": location_hint,
                    "today_date": today_str,
                })
                # 将few-shot示例内联到prompt文本中（qwen-turbo使用单prompt模式）
                parts = [rendered["system_prompt"], ""]
                for i in range(0, len(rendered["few_shot_messages"]), 2):
                    user_msg = rendered["few_shot_messages"][i]["content"]
                    asst_msg = rendered["few_shot_messages"][i + 1]["content"] if i + 1 < len(rendered["few_shot_messages"]) else ""
                    parts.append(f"示例输入：{user_msg}")
                    parts.append(f"示例输出：{asst_msg}")
                    parts.append("")
                parts.append(rendered["user_prompt"])
                prompt = "\n".join(parts)
            except Exception as e:
                logger.warning(f"模板服务渲染exercise_intent失败，回退硬编码: {e}")

        _intent_start = time.time()
        try:
            response = Generation.call(
                model="qwen-turbo",
                prompt=prompt,
                result_format='message'
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                # 提取JSON
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    intent = json.loads(json_str)
                    intent = self._normalize_exercise_intent(intent, calories_intake, query, user_location)
                    intent["geo_info"] = geo_info
                    intent["destination"] = stable_destination
                    
                    # Phase 56: 记录成功的AI调用
                    _intent_latency = int((time.time() - _intent_start) * 1000)
                    self._log_ai_call(
                        call_type="exercise_intent",
                        model_name="qwen-turbo",
                        input_summary=query,
                        success=True,
                        latency_ms=_intent_latency,
                        output_summary=f"destination={intent.get('destination')}, calories_target={intent.get('calories_target')}",
                    )
                    return intent
                else:
                    raise ValueError("未找到JSON数据")
            else:
                raise Exception(f"API调用失败: {response.message}")
                
        except Exception as e:
            # Phase 56: 记录失败的AI调用
            _intent_latency = int((time.time() - _intent_start) * 1000)
            self._log_ai_call(
                call_type="exercise_intent",
                model_name="qwen-turbo",
                input_summary=query,
                success=False,
                latency_ms=_intent_latency,
                error_message=str(e),
            )
            print(f"提取运动意图失败: {str(e)}")
            fallback_intent = self._build_default_exercise_intent(calories_intake, user_location)
            fallback_intent["geo_info"] = geo_info
            fallback_intent["destination"] = stable_destination
            return fallback_intent
    
    def _generate_exercise_plan(self, intent: dict, preferences: dict = None, calories_intake: float = 0.0, user_location: dict = None, query: str = "") -> dict:
        """生成运动计划"""
        geo_info = intent.get("geo_info") if isinstance(intent.get("geo_info"), dict) else None
        destination = intent.get("destination") or self._destination_from_geo_info(geo_info) or "运动场所"
        
        days = intent.get("days", 1)
        calories_target = intent.get("calories_target", 200)
        exercise_type = intent.get("exercise_type")
        
        # 构建Prompt
        preference_text = ""
        if preferences:
            health_goal = preferences.get("healthGoal")
            if health_goal:
                health_goal_map = {
                    "reduce_fat": "减脂",
                    "gain_muscle": "增肌",
                    "control_sugar": "控糖",
                    "balanced": "均衡"
                }
                preference_text += f"健康目标：{health_goal_map.get(health_goal, health_goal)}。"
        
        calories_context = ""
        if calories_intake > 0:
            calories_context = f"\n用户今日已摄入卡路里：{calories_intake:.1f} kcal，建议通过运动消耗约 {calories_target} kcal。"
        
        # 仅使用上游传入的geo_info，避免重复逆地理编码
        final_city = (geo_info or {}).get("city")
        location_context = ""
        if geo_info:
            location_parts = [
                geo_info.get("city"),
                geo_info.get("district"),
                geo_info.get("province"),
            ]
            location_desc = "、".join([part for part in location_parts if part]) or geo_info.get("full_address", "")
            city_name = geo_info.get("city") or "该城市"
            location_context = f"""
用户地理定位信息：{location_desc}
重要提示：
1. 请根据用户所在城市和区域，在placeName字段中生成具体、真实的地点名称（如"{city_name}中央公园"、"{city_name}滨江健身步道"、"{city_name}XX体育中心"等）
2. 不要使用"附近公园"、"附近步道"这样的模糊描述，要生成具体的地点名称，并包含城市信息
3. 可以根据用户所在城市和区域特征生成合理的地点名称
4. **地点多样性**：如果有多个运动节点，每个节点的placeName必须不同，要推荐不同的运动地点
5. 所有地点名称都应该包含城市信息，例如"{city_name}XX公园"、"{city_name}XX健身步道"等
"""
        elif user_location and user_location.get("latitude") is not None and user_location.get("longitude") is not None:
            lat = user_location["latitude"]
            lon = user_location["longitude"]
            location_context = f"""
用户GPS位置：纬度 {lat:.6f}, 经度 {lon:.6f}
重要提示：
1. 请根据用户位置信息，在placeName字段中生成具体、真实的地点名称（如"XX公园"、"XX健身步道"、"XX体育中心"等）
2. 不要使用"附近公园"、"附近步道"这样的模糊描述，要生成具体的地点名称
3. **地点多样性**：如果有多个运动节点，每个节点的placeName必须不同，要推荐不同的运动地点
"""
        
        # 如果没有提供日期，使用今天的日期
        from datetime import datetime, timedelta
        today = datetime.now().date()
        if "startDate" not in intent or not intent.get("startDate"):
            start_date = today.strftime("%Y-%m-%d")
        else:
            start_date = intent.get("startDate")
        
        if "endDate" not in intent or not intent.get("endDate"):
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = (start_date_obj + timedelta(days=days - 1)).strftime("%Y-%m-%d")
        else:
            end_date = intent.get("endDate")
        
        exercise_type_text = f"运动类型：{exercise_type}。" if exercise_type else ""
        
        # 生成个性化标题提示
        title_hint = f"""
重要：title字段必须根据用户查询内容生成个性化、有意义的标题，不要总是使用"餐后运动计划"。
标题应该：
- 反映运动类型（如"周末慢跑计划"、"散步健身计划"）
- 反映时间特征（如"周末运动计划"、"三日运动计划"）
- 反映地点特征（如"公园健走计划"、"健身房训练计划"）
- 简洁明了，10-15个字左右
示例：如果用户查询"周末慢跑"，标题可以是"周末慢跑健身计划"；如果查询"餐后散步30分钟"，标题可以是"餐后散步计划"
"""
        
        duration_minutes = intent.get("duration_minutes")
        duration_hint = f"用户期望总运动时长：{duration_minutes} 分钟。" if isinstance(duration_minutes, int) and duration_minutes > 0 else ""

        prompt = f"""请为以下餐后运动需求生成详细的运动计划，并以JSON格式返回。

用户原始需求："{query}"

运动区域：{destination}
运动日期：{start_date} 至 {end_date}（共{days}天）
目标消耗卡路里：{calories_target} kcal
{duration_hint}
{exercise_type_text}
{preference_text}
{title_hint}
{location_context}
{calories_context}

核心规则：
1. **严格按照用户需求中提到的每一项运动分别生成独立节点**。
   例如用户说"先散步15分钟，再慢跑20分钟，最后骑行1小时"，则必须生成3个节点：散步(15min) + 慢跑(20min) + 骑行(60min)。
2. 每个节点的duration必须严格遵循用户指定的时长，不要自行更改。
3. 如果用户没指定具体运动，根据目标卡路里自行合理拆分多个节点。
4. 如果days>1，每天至少1个节点，dayIndex从1递增。
5. 每个节点包含：
   - dayIndex: 第几天（从1开始）
   - startTime: 开始时间（HH:mm格式）
   - placeName: 运动地点名称（具体名称，禁止"附近"等模糊词）
   - placeType: walking/running/cycling/jogging/park/gym/indoor/outdoor
   - duration: 运动时长（分钟，必须与用户指定一致）
   - cost: 预计消耗卡路里（kcal）
   - notes: 运动建议
6. title个性化，反映运动内容。
7. 不同节点的placeName应各不相同。

仅返回JSON，不要其他解释。

返回格式：
{{
    "title": "个性化标题",
    "destination": "{destination}",
    "startDate": "{start_date}",
    "endDate": "{end_date}",
    "items": [
        {{
            "dayIndex": 1,
            "startTime": "19:00",
            "placeName": "具体地点A",
            "placeType": "walking",
            "duration": 15,
            "cost": 50,
            "notes": "运动建议"
        }}
    ]
}}"""
        
        # Phase 57: 尝试使用模板服务构建运动计划prompt
        tpl_svc = _get_prompt_tpl_service()
        if tpl_svc is not None:
            try:
                rendered = tpl_svc.render_prompt("trip_generation", variables={
                    "query": query,
                    "destination": destination,
                    "start_date": start_date,
                    "end_date": end_date,
                    "days": str(days),
                    "calories_target": str(calories_target),
                    "duration_hint": duration_hint,
                    "exercise_type_text": exercise_type_text,
                    "preference_text": preference_text,
                    "title_hint": title_hint,
                    "calories_context": calories_context,
                    "location_context": location_context,
                })
                # 将few-shot示例内联到prompt文本中（qwen-turbo使用单prompt模式）
                parts = [rendered["system_prompt"], ""]
                for i in range(0, len(rendered["few_shot_messages"]), 2):
                    user_msg = rendered["few_shot_messages"][i]["content"]
                    asst_msg = rendered["few_shot_messages"][i + 1]["content"] if i + 1 < len(rendered["few_shot_messages"]) else ""
                    parts.append(f"示例输入：{user_msg}")
                    parts.append(f"示例输出：{asst_msg}")
                    parts.append("")
                parts.append(rendered["user_prompt"])
                prompt = "\n".join(parts)
            except Exception as e:
                logger.warning(f"模板服务渲染trip_generation失败，回退硬编码: {e}")

        _plan_start = time.time()
        try:
            response = Generation.call(
                model="qwen-turbo",
                prompt=prompt,
                result_format='message'
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                # 提取JSON
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    trip_data = json.loads(json_str)
                    logger.info(
                        f"[PlanGen] LLM原始返回 items={len(trip_data.get('items', []))}, "
                        f"durations={[it.get('duration') for it in trip_data.get('items', [])]}, "
                        f"types={[it.get('placeType') for it in trip_data.get('items', [])]}"
                    )
                    trip_data["destination"] = destination
                    # 确保有travelers字段（兼容性）
                    if "travelers" not in trip_data:
                        trip_data["travelers"] = ["本人"]
                    
                    trip_data = self._ensure_specific_locations(trip_data, user_location, city_prefix=final_city)
                    logger.info(f"[PlanGen] after _ensure_specific_locations: items={len(trip_data.get('items', []))}")
                    trip_data = self._normalize_plan_locations(trip_data, city_prefix=final_city)
                    logger.info(f"[PlanGen] after _normalize_plan_locations: items={len(trip_data.get('items', []))}")
                    trip_data = self._ensure_location_diversity(trip_data)
                    logger.info(f"[PlanGen] after _ensure_location_diversity: items={len(trip_data.get('items', []))}")
                    trip_data = self._adjust_plan_durations(trip_data, intent, query)
                    logger.info(f"[PlanGen] after _adjust_plan_durations: items={len(trip_data.get('items', []))}, durations={[it.get('duration') for it in trip_data.get('items', [])]}")
                    trip_data = self._adjust_plan_times(trip_data, intent, query)
                    logger.info(f"[PlanGen] after _adjust_plan_times: items={len(trip_data.get('items', []))}")
                    
                    # Phase 56: 记录成功的AI调用
                    _plan_latency = int((time.time() - _plan_start) * 1000)
                    self._log_ai_call(
                        call_type="trip_generation",
                        model_name="qwen-turbo",
                        input_summary=query[:200] if query else destination,
                        success=True,
                        latency_ms=_plan_latency,
                        output_summary=f"title={trip_data.get('title')}, items={len(trip_data.get('items', []))}",
                    )
                    
                    return trip_data
                else:
                    raise ValueError("未找到JSON数据")
            else:
                raise Exception(f"API调用失败: {response.message}")
                
        except Exception as e:
            # Phase 56: 记录失败的AI调用
            _plan_latency = int((time.time() - _plan_start) * 1000)
            self._log_ai_call(
                call_type="trip_generation",
                model_name="qwen-turbo",
                input_summary=query[:200] if query else destination,
                success=False,
                latency_ms=_plan_latency,
                error_message=str(e),
            )
            print(f"生成运动计划失败: {str(e)}")
            # 返回默认运动计划
            return self._get_default_exercise_plan(intent, calories_target)
    
    def _fix_date_and_days(self, intent: dict) -> dict:
        """修复日期和天数，处理周末、多天等情况"""
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        start_date_str = intent.get("startDate")
        end_date_str = intent.get("endDate")
        days = intent.get("days", 1)

        # 如果模型抄了固定示例日期（如 2026-01-27），或缺失，则用今天纠正
        try:
            if (not start_date_str) or (start_date_str.strip() in {"2026-01-27", "1970-01-01"}):
                intent["startDate"] = today.strftime("%Y-%m-%d")
                start_date_str = intent["startDate"]
                if not end_date_str:
                    intent["endDate"] = start_date_str
                    end_date_str = start_date_str
        except Exception:
            intent["startDate"] = today.strftime("%Y-%m-%d")
            start_date_str = intent["startDate"]
            if not end_date_str:
                intent["endDate"] = start_date_str
                end_date_str = start_date_str
        
        # 如果startDate和endDate都存在，计算实际天数
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                actual_days = (end_date - start_date).days + 1
                if actual_days > 0:
                    intent["days"] = actual_days
            except:
                pass
        
        # 如果只有startDate，根据days计算endDate
        if start_date_str and not end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = start_date + timedelta(days=days - 1)
                intent["endDate"] = end_date.strftime("%Y-%m-%d")
            except:
                if not end_date_str:
                    intent["endDate"] = start_date_str
        
        # 如果只有days，计算endDate
        if start_date_str and days > 1:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = start_date + timedelta(days=days - 1)
                intent["endDate"] = end_date.strftime("%Y-%m-%d")
            except:
                pass
        
        return intent
    
    def _ensure_location_diversity(self, trip_data: dict) -> dict:
        """确保多个运动节点使用不同的地点，增加地点多样性"""
        if "items" not in trip_data or len(trip_data["items"]) <= 1:
            return trip_data
        
        items = trip_data["items"]
        used_places = set()
        place_variations = [
            "中央公园", "世纪公园", "奥林匹克公园", "滨江健身步道", "社区健身广场",
            "体育中心", "健身步道", "森林公园", "文化公园", "运动公园",
            "健身中心", "体育场", "运动场", "健身广场", "健康步道"
        ]
        
        for i, item in enumerate(items):
            place_name = item.get("placeName", "")
            place_type = item.get("placeType", "walking")
            
            # 清洗不合理/虚构名称
            place_name = self._sanitize_place_name(place_name)
            item["placeName"] = place_name

            # 如果地点名称已使用，生成一个新的
            if place_name in used_places:
                # 根据运动类型选择合适的地点
                if place_type == "walking":
                    new_places = ["健身步道", "公园", "社区广场", "健康步道"]
                elif place_type == "running":
                    new_places = ["跑步道", "健身步道", "运动场", "体育场"]
                elif place_type == "cycling":
                    new_places = ["骑行道", "自行车道", "绿道", "健身步道"]
                elif place_type == "park":
                    new_places = ["公园", "森林公园", "文化公园", "运动公园"]
                elif place_type == "gym":
                    new_places = ["健身房", "健身中心", "体育中心", "运动中心"]
                else:
                    new_places = place_variations
                
                # 选择一个未使用的地点
                for new_place in new_places:
                    if new_place not in used_places:
                        # 如果有城市前缀，保留城市前缀
                        if place_name and any(city in place_name for city in ["北京", "上海", "广州", "深圳", "杭州", "成都"]):
                            city_prefix = ""
                            for city in ["北京", "上海", "广州", "深圳", "杭州", "成都"]:
                                if city in place_name:
                                    city_prefix = city
                                    break
                            cleaned_new = self._sanitize_place_name(f"{city_prefix}{new_place}") if city_prefix else self._sanitize_place_name(new_place)
                            item["placeName"] = cleaned_new
                        else:
                            item["placeName"] = self._sanitize_place_name(new_place)
                        used_places.add(item["placeName"])
                        break
            else:
                used_places.add(place_name)
        
        return trip_data

    def _adjust_plan_durations(self, trip_data: dict, intent: dict, query: str) -> dict:
        """根据query/intent动态修正节点时长。

        规则：
        1) 优先使用 intent.duration_minutes（由query提取而来）
        2) 若query明确出现“XX分钟”，作为兜底
        3) 多节点按权重分配总时长，保证每个节点>=10分钟
        """
        items = trip_data.get("items") or []
        if not items:
            return trip_data

        if self._query_has_per_activity_durations(query):
            for item in items:
                d = item.get("duration")
                if not isinstance(d, int) or d <= 0:
                    item["duration"] = 20
            return trip_data

        total_minutes = intent.get("duration_minutes")
        if not isinstance(total_minutes, int) or total_minutes <= 0:
            total_minutes = self._parse_total_duration_from_query(query)

        if not isinstance(total_minutes, int) or total_minutes <= 0:
            for item in items:
                d = item.get("duration")
                if not isinstance(d, int) or d <= 0:
                    item["duration"] = 20
            return trip_data

        n = len(items)
        if n == 1:
            items[0]["duration"] = max(10, total_minutes)
            return trip_data

        raw_durations = []
        for item in items:
            d = item.get("duration")
            raw_durations.append(d if isinstance(d, int) and d > 0 else 0)

        sum_raw = sum(raw_durations)
        if sum_raw <= 0:
            # 均分并保证最后一个吸收余数
            base = max(10, total_minutes // n)
            assigned = [base] * n
            diff = total_minutes - sum(assigned)
            assigned[-1] = max(10, assigned[-1] + diff)
        else:
            assigned = []
            allocated = 0
            for i, d in enumerate(raw_durations):
                if i == n - 1:
                    val = max(10, total_minutes - allocated)
                else:
                    ratio_val = round(total_minutes * (d / sum_raw))
                    val = max(10, int(ratio_val))
                    allocated += val
                assigned.append(val)
            # 若因最小值约束超出总时长，做一次压缩（不低于10）
            over = sum(assigned) - total_minutes
            i = n - 1
            while over > 0 and i >= 0:
                reducible = max(0, assigned[i] - 10)
                dec = min(reducible, over)
                assigned[i] -= dec
                over -= dec
                i -= 1

        for item, d in zip(items, assigned):
            item["duration"] = d
        return trip_data

    @staticmethod
    def _query_has_per_activity_durations(query: str) -> bool:
        """判断 query 是否为每个活动分别指定了时长（>=2 段独立时长描述）。"""
        if not query:
            return False
        pattern = r"\d+(?:\.\d+)?\s*(?:分钟|min(?:ute)?s?|小时|个小时|h(?:our)?s?)"
        matches = re.findall(pattern, query, re.IGNORECASE)
        return len(matches) >= 2

    def _adjust_plan_times(self, trip_data: dict, intent: dict, query: str) -> dict:
        """根据提示词、日期与节点时长动态排程startTime，避免多个节点同一时间。"""
        try:
            from datetime import datetime, timedelta, time
        except Exception:
            return trip_data

        # 简单解析提示词
        q = (query or "").strip()
        def _hint_from_query(q: str) -> str | None:
            if not q:
                return None
            if any(k in q for k in ["早餐", "早饭", "早上", "上午"]):
                return "breakfast"
            if any(k in q for k in ["午餐", "午饭", "中午"]):
                return "lunch"
            if any(k in q for k in ["晚餐", "晚饭", "傍晚", "晚上", "夜间"]):
                return "dinner"
            if "下午" in q:
                return "afternoon"
            return None

        hint = _hint_from_query(q)
        start_date_str = trip_data.get("startDate") or intent.get("startDate")
        today = datetime.now().date()
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else today
        except Exception:
            start_date = today

        def _day_base_time(day_index: int) -> time:
            if hint == "breakfast":
                return time(8, 0)
            if hint == "lunch":
                return time(12, 30)
            if hint == "dinner":
                return time(19, 0)
            if hint == "afternoon":
                return time(16, 0)
            # 默认：首日今天则从当前+30分钟开始，否则 19:00
            if day_index == 1 and start_date == today:
                now_plus = datetime.now() + timedelta(minutes=30)
                return time(now_plus.hour, now_plus.minute)
            return time(19, 0)

        items = trip_data.get("items") or []
        if not items:
            return trip_data

        # 按day分组，组内按原顺序排程
        day_buckets: Dict[int, List[dict]] = {}
        for item in items:
            di = item.get("dayIndex")
            if isinstance(di, int):
                day_index = di
            elif isinstance(di, str) and di.isdigit():
                day_index = int(di)
            else:
                day_index = 1
            day_buckets.setdefault(day_index, []).append(item)

        min_dt = datetime.combine(today, time(6, 30))
        max_dt = datetime.combine(today, time(22, 30))

        for day_index, day_items in day_buckets.items():
            cursor = datetime.combine(today, _day_base_time(day_index))
            if cursor < min_dt:
                cursor = min_dt
            if cursor > max_dt:
                cursor = max_dt

            for idx, item in enumerate(day_items):
                item["startTime"] = f"{cursor.hour:02d}:{cursor.minute:02d}"
                duration = item.get("duration")
                if not isinstance(duration, int) or duration <= 0:
                    duration = 20
                # 节点间留10分钟换场缓冲，防止同一时间
                cursor = cursor + timedelta(minutes=duration + 10 + (idx % 2) * 5)
                if cursor > max_dt:
                    cursor = max_dt

        return trip_data
    
    def _ensure_specific_locations(self, trip_data: dict, user_location: dict = None, city_prefix: Optional[str] = None) -> dict:
        """确保destination和placeName都是具体的地点名称，而不是模糊描述"""
        # 模糊描述的常见模式
        vague_patterns = ["附近", "当前位置附近", "附近公园", "附近步道", "附近健身房", "小区周边"]
        
        destination = trip_data.get("destination", "")
        # 如果destination包含"附近"等模糊词汇，移除它们
        if "附近" in destination:
            destination = destination.replace("附近", "").strip()
            if not destination:
                destination = "运动场所"
            trip_data["destination"] = destination
        elif destination in vague_patterns or not destination:
            if user_location:
                trip_data["destination"] = "运动场所"
            else:
                trip_data["destination"] = "运动场所"
        
        # 城市前缀规范
        if city_prefix:
            trip_data["destination"] = self._sanitize_place_name(trip_data["destination"], city_prefix=city_prefix)
        
        # 处理items中的placeName
        if "items" in trip_data:
            for item in trip_data["items"]:
                place_name = item.get("placeName", "")
                # 如果placeName包含"附近"等模糊词汇，移除它们
                if "附近" in place_name:
                    place_name = place_name.replace("附近", "").strip()
                    if not place_name:
                        # 根据placeType生成一个具体名称
                        place_type = item.get("placeType", "walking")
                        type_name_map = {
                            "walking": "健身步道",
                            "running": "跑步道",
                            "cycling": "骑行道",
                            "park": "中央公园",
                            "gym": "健身房",
                            "indoor": "室内运动场",
                            "outdoor": "户外运动场"
                        }
                        place_name = type_name_map.get(place_type, "运动场所")
                    item["placeName"] = self._sanitize_place_name(place_name, city_prefix=city_prefix)
                elif place_name in vague_patterns or not place_name:
                    if destination and destination not in vague_patterns and "附近" not in destination:
                        item["placeName"] = self._sanitize_place_name(destination, city_prefix=city_prefix)
                    else:
                        # 根据placeType生成一个具体名称
                        place_type = item.get("placeType", "walking")
                        type_name_map = {
                            "walking": "健身步道",
                            "running": "跑步道",
                            "cycling": "骑行道",
                            "park": "中央公园",
                            "gym": "健身房",
                            "indoor": "室内运动场",
                            "outdoor": "户外运动场"
                        }
                        item["placeName"] = self._sanitize_place_name(type_name_map.get(place_type, "运动场所"), city_prefix=city_prefix)
                else:
                    item["placeName"] = self._sanitize_place_name(place_name, city_prefix=city_prefix)
        
        return trip_data

    def _sanitize_place_name(self, name: str, city_prefix: Optional[str] = None) -> str:
        """清洗地点名称，避免模糊/虚构词，规范城市前缀"""
        if not name:
            return "运动场所"
        name = name.strip()
        # 过滤常见虚构/模糊词
        forbidden_tokens = ["附近", "示例", "测试", "随机", "XX", "虚构", "虚空", "unknown", "N/A", "位置"]
        for tok in forbidden_tokens:
            name = name.replace(tok, "").strip()
        if not name:
            name = "运动场所"
        
        # 如果提供城市前缀且名称未包含城市，添加前缀
        if city_prefix and city_prefix not in name:
            name = f"{city_prefix}{name}"
        
        # 限制长度，避免过长
        if len(name) > 30:
            name = name[:30]
        return name

    def _extract_explicit_place_from_query(self, query: str) -> Optional[Dict[str, str]]:
        """从查询文本中提取显式地点/地址（简单启发式）"""
        if not query:
            return None
        query = query.strip()
        # 识别常见城市后缀/行政区关键词
        admin_keywords = ["省", "市", "区", "县", "镇", "街道"]
        place_keywords = [
            "公园", "步道", "健身房", "体育中心", "运动中心", "健身广场",
            "跑步道", "骑行道", "自行车道", "绿道", "体育场", "运动场", "健身步道"
        ]
        detected_city = None
        # 尝试匹配显式城市（如 北京市/上海市/杭州）
        for kw in ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "南京", "重庆", "天津", "苏州", "长沙", "郑州", "东莞", "青岛", "沈阳", "宁波", "昆明", "大连"]:
            if kw in query:
                detected_city = kw
                break
        # 查找包含地点后缀的片段
        best = None
        for pk in place_keywords:
            idx = query.find(pk)
            if idx != -1:
                # 取前后窗口作为地点名称（避免过长）
                start = max(0, idx - 8)
                end = min(len(query), idx + len(pk))
                candidate = query[start:end].strip()
                # 清理语气词
                candidate = candidate.replace("去", "").replace("在", "").replace("到", "").replace("吧", "").strip()
                if candidate:
                    best = candidate
                    break
        if best or detected_city:
            return {"city": detected_city, "placeName": best or ""}
        return None

    def _normalize_plan_locations(self, trip_data: dict, city_prefix: Optional[str] = None) -> dict:
        """规范与去重 items 中的地点名称，避免重复与不合理名称"""
        if "items" not in trip_data:
            return trip_data
        seen = set()
        for item in trip_data["items"]:
            name = item.get("placeName", "")
            cleaned = self._sanitize_place_name(name, city_prefix=city_prefix)
            # 保证唯一性：如重复，尝试添加类型后缀
            if cleaned in seen:
                place_type = item.get("placeType", "")
                alt = self._sanitize_place_name(f"{cleaned}-{place_type}" if place_type else f"{cleaned}-A", city_prefix=None)
                cleaned = alt if alt not in seen else f"{cleaned}-B"
            item["placeName"] = cleaned
            seen.add(cleaned)
        return trip_data
    
    def _enrich_plan_with_poi(self, trip_data: dict, user_location: Optional[dict]) -> dict:
        """用高德POI真实地点替换LLM生成的placeName，确保地点真实可标注。"""
        if not user_location:
            return trip_data
        lat = user_location.get("latitude")
        lng = user_location.get("longitude")
        if lat is None or lng is None:
            return trip_data

        try:
            from app.services.poi_service import get_poi_service
            poi_svc = get_poi_service()
            if not poi_svc.available:
                logger.info("POI服务不可用（AMAP_KEY未设置），跳过地点增强")
                return trip_data

            items = trip_data.get("items", [])
            if not items:
                return trip_data

            logger.info(f"[PlanGen] before POI enrich: items={len(items)}")
            enriched_items = poi_svc.search_diverse_for_plan(lat, lng, items, radius=5000)
            logger.info(f"[PlanGen] after POI enrich: items={len(enriched_items)}")
            trip_data["items"] = enriched_items
        except Exception as e:
            logger.warning(f"POI地点增强失败，保留原始数据: {e}")

        return trip_data

    def _get_default_exercise_plan(self, intent: dict, calories_target: int = 200) -> dict:
        """返回默认运动计划（当AI调用失败时）"""
        destination = intent.get("destination", "附近")
        start_date = intent.get("startDate")
        end_date = intent.get("endDate")
        from datetime import datetime
        if not start_date:
            start_date = datetime.now().date().strftime("%Y-%m-%d")
        if not end_date:
            end_date = start_date
        
        # 根据目标卡路里生成运动计划
        # 散步：约5 kcal/分钟，慢跑：约10 kcal/分钟
        items = []
        remaining_calories = calories_target
        
        if remaining_calories >= 150:
            # 慢跑20分钟，消耗约200卡路里
            items.append({
                "dayIndex": 1,
                "startTime": "19:30",
                "placeName": "健身步道",
                "placeType": "running",
                "duration": 20,
                "cost": min(remaining_calories, 200),
                "notes": "餐后慢跑，注意控制强度"
            })
            remaining_calories -= 200
        
        if remaining_calories > 0:
            # 散步补充剩余卡路里
            walk_duration = max(10, int(remaining_calories / 5))
            items.append({
                "dayIndex": 1,
                "startTime": "20:00",
                "placeName": "社区公园",
                "placeType": "walking",
                "duration": walk_duration,
                "cost": remaining_calories,
                "notes": "餐后散步"
            })
        
        return {
            "title": f"餐后运动计划（消耗{calories_target}卡路里）",
            "destination": destination,
            "startDate": start_date,
            "endDate": end_date,
            "travelers": ["本人"],
            "items": items if items else [
                {
                    "dayIndex": 1,
                    "startTime": "19:00",
                    "placeName": "附近公园",
                    "placeType": "walking",
                    "duration": 30,
                    "cost": calories_target,
                    "notes": "餐后散步"
                }
            ]
        }
    
    def recognize_menu_image(self, image_file, health_goal: Optional[str] = None) -> List[dict]:
        """
        识别菜单图片中的菜品
        
        Args:
            image_file: 图片文件对象
            health_goal: 用户健康目标（用于生成推荐理由）
            
        Returns:
            菜品列表，每个菜品包含营养数据和推荐信息
        """
        try:
            # 读取图片文件（确保从文件开头读取）
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
            image_bytes = image_file.read()
            
            # 将图片转换为base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            dish_names = self._extract_dish_names_from_image(image_base64)
            
            if not dish_names:
                return []
            
            # 并发分析每个菜品的营养成分
            dishes = []
            
            def process_dish(dish_name: str) -> dict:
                """处理单个菜品：分析营养并生成推荐"""
                try:
                    # 获取营养数据
                    nutrition_data = self.analyze_food_nutrition(dish_name)
                    
                    # 根据健康目标生成推荐理由
                    is_recommended, reason = self._generate_recommendation(
                        nutrition_data, 
                        health_goal
                    )
                    
                    return {
                        "name": dish_name,
                        "calories": nutrition_data["calories"],
                        "protein": nutrition_data["protein"],
                        "fat": nutrition_data["fat"],
                        "carbs": nutrition_data["carbs"],
                        "isRecommended": is_recommended,
                        "reason": reason
                    }
                except Exception as e:
                    print(f"分析菜品 {dish_name} 失败: {str(e)}")
                    # 返回基础信息，避免整个请求失败
                    return {
                        "name": dish_name,
                        "calories": 0.0,
                        "protein": 0.0,
                        "fat": 0.0,
                        "carbs": 0.0,
                        "isRecommended": False,
                        "reason": f"分析失败: {str(e)}"
                    }
            
            # 使用线程池并发处理
            with ThreadPoolExecutor(max_workers=min(len(dish_names), 5)) as executor:
                # 提交所有任务
                future_to_dish = {
                    executor.submit(process_dish, dish_name): dish_name 
                    for dish_name in dish_names
                }
                
                # 收集结果（保持原始顺序）
                dish_results = {}
                for future in as_completed(future_to_dish):
                    dish_name = future_to_dish[future]
                    try:
                        dish_results[dish_name] = future.result()
                    except Exception as e:
                        print(f"处理菜品 {dish_name} 时出错: {str(e)}")
                        dish_results[dish_name] = {
                            "name": dish_name,
                            "calories": 0.0,
                            "protein": 0.0,
                            "fat": 0.0,
                            "carbs": 0.0,
                            "isRecommended": False,
                            "reason": f"处理失败: {str(e)}"
                        }
                
                # 按照原始顺序返回结果
                dishes = [dish_results[dish_name] for dish_name in dish_names]
            
            return dishes
            
        except Exception as e:
            print(f"识别菜单图片失败: {str(e)}")
            raise Exception(f"识别菜单失败: {str(e)}")
    
    def _extract_dish_names_from_image(self, image_base64: str) -> List[str]:
        """
        从图片中提取菜名列表（使用豆包AI）
        
        Args:
            image_base64: base64编码的图片
            
        Returns:
            菜名列表
            
        Raises:
            ValueError: 如果豆包AI未初始化或调用失败
        """
        if not self.ark_client:
            raise ValueError("豆包AI未初始化，请检查ARK_API_KEY环境变量")
        
        return self._extract_dish_names_with_ark(image_base64)
    
    def _extract_dish_names_with_ark(self, image_base64: str) -> List[str]:
        """使用豆包AI识别菜单图片（Phase 57: 支持模板服务）"""
        _recog_start = time.time()
        try:
            # 构建base64 data URI（尝试使用data URI格式）
            image_data_uri = f"data:image/jpeg;base64,{image_base64}"
            
            # Phase 57: 尝试使用模板服务构建prompt
            prompt = None
            tpl_svc = _get_prompt_tpl_service()
            if tpl_svc is not None:
                try:
                    rendered = tpl_svc.render_prompt("menu_recognition", variables={})
                    prompt = rendered["user_prompt"]
                except Exception as e:
                    logger.warning(f"模板服务渲染menu_recognition失败，回退硬编码: {e}")
            
            if prompt is None:
                prompt = """请识别这张菜单图片中的所有菜品名称，并以JSON数组格式返回。

要求：
1. 只返回菜品名称，不要价格、描述等其他信息
2. 如果图片不是菜单，返回空数组 []
3. 只返回JSON数组，不要其他解释

返回格式：
["菜品1", "菜品2", "菜品3"]

示例：
["宫保鸡丁", "麻婆豆腐", "鱼香肉丝"]"""
            
            response = self.ark_client.responses.create(
                model="doubao-seed-1-6-251015",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_image",
                                "image_url": image_data_uri  # 使用base64 data URI
                            },
                            {
                                "type": "input_text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            # 解析响应 - 从output列表项的content[0].text获取内容
            content = None
            
            if hasattr(response, 'output') and response.output:
                output = response.output
                # 如果output是列表，从列表项的content[0].text获取
                if isinstance(output, list) and len(output) > 0:
                    for item in output:
                        if hasattr(item, 'content') and item.content:
                            item_content = item.content
                            # 如果content是列表，从第一个元素的text字段获取
                            if isinstance(item_content, list) and len(item_content) > 0:
                                sub_item = item_content[0]
                                if hasattr(sub_item, 'text') and sub_item.text:
                                    content = sub_item.text
                                    break
            
            _recog_latency = int((time.time() - _recog_start) * 1000)
            if content:
                print(content)
                dish_names = self._parse_dish_names_from_content(content)
                # Phase 56: 记录成功的AI调用
                self._log_ai_call(
                    call_type="menu_recognition",
                    model_name="doubao-seed-1-6-251015",
                    input_summary="菜单图片识别",
                    success=True,
                    latency_ms=_recog_latency,
                    output_summary=f"识别到{len(dish_names)}个菜品: {', '.join(dish_names[:5])}",
                )
                return dish_names
            else:
                raise Exception("无法从响应中提取内容")
                
        except Exception as e:
            _recog_latency = int((time.time() - _recog_start) * 1000)
            # Phase 56: 记录失败的AI调用
            self._log_ai_call(
                call_type="menu_recognition",
                model_name="doubao-seed-1-6-251015",
                input_summary="菜单图片识别",
                success=False,
                latency_ms=_recog_latency,
                error_message=str(e),
            )
            print(f"豆包AI识别失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _parse_dish_names_from_content(self, content) -> List[str]:
        """从AI响应内容中解析菜名列表"""
        try:
            # content应该是JSON数组字符串，例如：'["小炒黄牛肉","韭菜炒鸡蛋",...]'
            if isinstance(content, str):
                content = content.strip()
                json_start = content.find('[')
                json_end = content.rfind(']') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    dish_names = json.loads(json_str)
                else:
                    return []
            else:
                return []
            
            # 确保返回的是列表并过滤无效值
            if isinstance(dish_names, list):
                dish_names = [
                    name.strip() 
                    for name in dish_names 
                    if name and isinstance(name, str) and name.strip()
                ]
                return dish_names
            else:
                return []
                
        except Exception as e:
            print(f"解析菜名失败: {str(e)}")
            return []
    
   
    def extract_before_meal_features(self, image_base64: str) -> dict:
        """
        从餐前图片中提取特征信息（菜品识别、份量估算、热量估算）
        
        Phase 11: 餐前图片特征提取
        
        Args:
            image_base64: base64编码的图片
            
        Returns:
            包含菜品特征的字典：
            {
                "dishes": [
                    {
                        "name": "菜品名称",
                        "estimated_weight": 200,  # 估算重量（g）
                        "estimated_calories": 500,  # 估算热量（kcal）
                        "estimated_protein": 25.0,  # 估算蛋白质（g）
                        "estimated_fat": 30.0,  # 估算脂肪（g）
                        "estimated_carbs": 15.0  # 估算碳水化合物（g）
                    }
                ],
                "total_estimated_calories": 580,
                "total_estimated_protein": 30.0,
                "total_estimated_fat": 35.0,
                "total_estimated_carbs": 20.0
            }
        """
        if not self.ark_client:
            raise ValueError("豆包AI未初始化，请检查ARK_API_KEY环境变量")
        
        return self._extract_before_meal_features_with_ark(image_base64)
    
    def _extract_before_meal_features_with_ark(self, image_base64: str) -> dict:
        """使用豆包AI从餐前图片提取特征（Phase 57: 支持模板服务）"""
        _bf_start = time.time()
        try:
            image_data_uri = f"data:image/jpeg;base64,{image_base64}"
            
            # Phase 57: 尝试使用模板服务构建prompt
            prompt = None
            tpl_svc = _get_prompt_tpl_service()
            if tpl_svc is not None:
                try:
                    rendered = tpl_svc.render_prompt("before_meal_features", variables={})
                    prompt = rendered["user_prompt"]
                except Exception as e:
                    logger.warning(f"模板服务渲染before_meal_features失败，回退硬编码: {e}")
            
            if prompt is None:
                prompt = """请分析这张餐前食物图片，识别图片中的所有菜品，并估算每个菜品的份量和营养成分。

要求：
1. 识别图片中所有可见的菜品
2. 根据视觉判断估算每个菜品的重量（克）
3. 根据菜品类型和重量估算热量、蛋白质、脂肪、碳水化合物
4. 计算所有菜品的总营养成分
5. 只返回JSON，不要其他解释
6. 如果图片不是食物图片，返回空dishes数组

请分析图片："""
            
            response = self.ark_client.responses.create(
                model="doubao-seed-1-6-251015",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_image",
                                "image_url": image_data_uri
                            },
                            {
                                "type": "input_text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            # 解析响应
            content = None
            if hasattr(response, 'output') and response.output:
                output = response.output
                if isinstance(output, list) and len(output) > 0:
                    for item in output:
                        if hasattr(item, 'content') and item.content:
                            item_content = item.content
                            if isinstance(item_content, list) and len(item_content) > 0:
                                sub_item = item_content[0]
                                if hasattr(sub_item, 'text') and sub_item.text:
                                    content = sub_item.text
                                    break
            
            if content:
                result = self._parse_before_meal_features(content)
                # Phase 56: 记录成功的AI调用
                _bf_latency = int((time.time() - _bf_start) * 1000)
                self._log_ai_call(
                    call_type="food_analysis",
                    model_name="doubao-seed-1-6-251015",
                    input_summary="餐前图片特征提取",
                    success=True,
                    latency_ms=_bf_latency,
                    output_summary=f"dishes={len(result.get('dishes', []))}, calories={result.get('total_estimated_calories')}",
                )
                return result
            else:
                raise Exception("豆包AI返回空响应")
                
        except Exception as e:
            # Phase 56: 记录失败的AI调用
            _bf_latency = int((time.time() - _bf_start) * 1000)
            self._log_ai_call(
                call_type="food_analysis",
                model_name="doubao-seed-1-6-251015",
                input_summary="餐前图片特征提取",
                success=False,
                latency_ms=_bf_latency,
                error_message=str(e),
            )
            print(f"餐前图片特征提取失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _parse_before_meal_features(self, content: str) -> dict:
        """解析餐前图片特征提取结果"""
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                # 确保必需字段存在
                dishes = data.get("dishes", [])
                
                # 处理每个菜品
                processed_dishes = []
                for dish in dishes:
                    processed_dish = {
                        "name": dish.get("name", "未知菜品"),
                        "estimated_weight": int(dish.get("estimated_weight", 100)),
                        "estimated_calories": float(dish.get("estimated_calories", 0)),
                        "estimated_protein": float(dish.get("estimated_protein", 0)),
                        "estimated_fat": float(dish.get("estimated_fat", 0)),
                        "estimated_carbs": float(dish.get("estimated_carbs", 0))
                    }
                    processed_dishes.append(processed_dish)
                
                result = {
                    "dishes": processed_dishes,
                    "total_estimated_calories": float(data.get("total_estimated_calories", 0)),
                    "total_estimated_protein": float(data.get("total_estimated_protein", 0)),
                    "total_estimated_fat": float(data.get("total_estimated_fat", 0)),
                    "total_estimated_carbs": float(data.get("total_estimated_carbs", 0))
                }
                
                # 如果总热量为0但有菜品，重新计算
                if result["total_estimated_calories"] == 0 and processed_dishes:
                    result["total_estimated_calories"] = sum(d["estimated_calories"] for d in processed_dishes)
                    result["total_estimated_protein"] = sum(d["estimated_protein"] for d in processed_dishes)
                    result["total_estimated_fat"] = sum(d["estimated_fat"] for d in processed_dishes)
                    result["total_estimated_carbs"] = sum(d["estimated_carbs"] for d in processed_dishes)
                
                return result
            else:
                raise ValueError("未找到JSON数据")
                
        except Exception as e:
            print(f"解析餐前特征失败: {str(e)}")
            print(f"原始内容: {content}")
            # 返回空结果
            return {
                "dishes": [],
                "total_estimated_calories": 0,
                "total_estimated_protein": 0,
                "total_estimated_fat": 0,
                "total_estimated_carbs": 0
            }

    def compare_before_after_meal(
        self, 
        before_image_base64: str, 
        after_image_base64: str,
        before_features: dict
    ) -> dict:
        """
        对比餐前餐后图片，计算剩余比例
        
        Phase 12: 餐前餐后对比计算
        
        Args:
            before_image_base64: 餐前图片base64编码
            after_image_base64: 餐后图片base64编码
            before_features: 餐前图片特征（包含识别的菜品和估算热量）
            
        Returns:
            包含对比结果的字典：
            {
                "dishes": [
                    {
                        "name": "菜品名称",
                        "remaining_ratio": 0.25,  # 剩余比例（0-1）
                        "remaining_weight": 50  # 估算剩余重量（g）
                    }
                ],
                "overall_remaining_ratio": 0.25,  # 整体剩余比例
                "consumption_ratio": 0.75,  # 消耗比例 = 1 - 剩余比例
                "comparison_analysis": "AI对比分析说明"
            }
        """
        if not self.ark_client:
            raise ValueError("豆包AI未初始化，请检查ARK_API_KEY环境变量")
        
        return self._compare_before_after_meal_with_ark(
            before_image_base64, 
            after_image_base64,
            before_features
        )
    
    def _compare_before_after_meal_with_ark(
        self, 
        before_image_base64: str, 
        after_image_base64: str,
        before_features: dict
    ) -> dict:
        """使用豆包AI对比餐前餐后图片（Phase 57: 支持模板服务）"""
        _cmp_start = time.time()
        try:
            before_data_uri = f"data:image/jpeg;base64,{before_image_base64}"
            after_data_uri = f"data:image/jpeg;base64,{after_image_base64}"
            
            # 构建餐前菜品信息文本
            before_dishes_text = ""
            if before_features and before_features.get("dishes"):
                dishes_info = []
                for dish in before_features["dishes"]:
                    name = dish.get("name", "未知菜品")
                    weight = dish.get("estimated_weight", 0)
                    calories = dish.get("estimated_calories", 0)
                    dishes_info.append(f"- {name}（估算重量：{weight}g，热量：{calories}kcal）")
                before_dishes_text = "\n".join(dishes_info)
            
            # Phase 57: 尝试使用模板服务构建prompt
            prompt = None
            tpl_svc = _get_prompt_tpl_service()
            if tpl_svc is not None:
                try:
                    rendered = tpl_svc.render_prompt("meal_comparison", variables={
                        "before_dishes_text": before_dishes_text if before_dishes_text else "未识别到具体菜品",
                    })
                    prompt = rendered["user_prompt"]
                except Exception as e:
                    logger.warning(f"模板服务渲染meal_comparison失败，回退硬编码: {e}")
            
            if prompt is None:
                prompt = f"""请对比这两张图片（餐前和餐后），分析用户吃掉了多少食物，剩余了多少。

餐前识别到的菜品信息：
{before_dishes_text if before_dishes_text else "未识别到具体菜品"}

要求：
1. 对比餐前图片（第一张）和餐后图片（第二张）
2. 估算每个菜品的剩余比例（0表示吃完，1表示没动）
3. 计算整体剩余比例
4. 给出简短的对比分析说明
5. 只返回JSON，不要其他解释

请分析图片："""
            
            response = self.ark_client.responses.create(
                model="doubao-seed-1-6-251015",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "这是餐前的食物图片："
                            },
                            {
                                "type": "input_image",
                                "image_url": before_data_uri
                            },
                            {
                                "type": "input_text",
                                "text": "这是餐后的食物图片："
                            },
                            {
                                "type": "input_image",
                                "image_url": after_data_uri
                            },
                            {
                                "type": "input_text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            # 解析响应
            content = None
            if hasattr(response, 'output') and response.output:
                output = response.output
                if isinstance(output, list) and len(output) > 0:
                    for item in output:
                        if hasattr(item, 'content') and item.content:
                            item_content = item.content
                            if isinstance(item_content, list) and len(item_content) > 0:
                                sub_item = item_content[0]
                                if hasattr(sub_item, 'text') and sub_item.text:
                                    content = sub_item.text
                                    break
            
            if content:
                result = self._parse_comparison_result(content)
                # Phase 56: 记录成功的AI调用
                _cmp_latency = int((time.time() - _cmp_start) * 1000)
                self._log_ai_call(
                    call_type="meal_comparison",
                    model_name="doubao-seed-1-6-251015",
                    input_summary="餐前餐后对比分析",
                    success=True,
                    latency_ms=_cmp_latency,
                    output_summary=f"remaining={result.get('overall_remaining_ratio')}",
                )
                return result
            else:
                raise Exception("豆包AI返回空响应")
                
        except Exception as e:
            # Phase 56: 记录失败的AI调用
            _cmp_latency = int((time.time() - _cmp_start) * 1000)
            self._log_ai_call(
                call_type="meal_comparison",
                model_name="doubao-seed-1-6-251015",
                input_summary="餐前餐后对比分析",
                success=False,
                latency_ms=_cmp_latency,
                error_message=str(e),
            )
            print(f"餐前餐后对比失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _parse_comparison_result(self, content: str) -> dict:
        """解析餐前餐后对比结果"""
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                # 处理菜品剩余信息
                dishes = data.get("dishes", [])
                processed_dishes = []
                for dish in dishes:
                    processed_dish = {
                        "name": dish.get("name", "未知菜品"),
                        "remaining_ratio": float(dish.get("remaining_ratio", 0)),
                        "remaining_weight": int(dish.get("remaining_weight", 0))
                    }
                    # 确保比例在0-1范围内
                    processed_dish["remaining_ratio"] = max(0, min(1, processed_dish["remaining_ratio"]))
                    processed_dishes.append(processed_dish)
                
                overall_remaining_ratio = float(data.get("overall_remaining_ratio", 0))
                # 确保比例在0-1范围内
                overall_remaining_ratio = max(0, min(1, overall_remaining_ratio))
                
                # 计算消耗比例
                consumption_ratio = 1 - overall_remaining_ratio
                
                result = {
                    "dishes": processed_dishes,
                    "overall_remaining_ratio": round(overall_remaining_ratio, 4),
                    "consumption_ratio": round(consumption_ratio, 4),
                    "comparison_analysis": data.get("comparison_analysis", "对比分析完成")
                }
                
                return result
            else:
                raise ValueError("未找到JSON数据")
                
        except Exception as e:
            print(f"解析对比结果失败: {str(e)}")
            print(f"原始内容: {content}")
            # 返回默认结果（假设吃掉了一半）
            return {
                "dishes": [],
                "overall_remaining_ratio": 0.5,
                "consumption_ratio": 0.5,
                "comparison_analysis": "无法准确分析，默认估算您吃掉了约50%的食物。"
            }

    def _generate_recommendation(self, nutrition_data: dict, health_goal: Optional[str] = None) -> Tuple[bool, str]:
        """
        根据营养数据和健康目标生成推荐理由
        
        Args:
            nutrition_data: 营养数据字典
            health_goal: 健康目标（reduce_fat/gain_muscle/control_sugar/balanced）
            
        Returns:
            (是否推荐, 推荐理由)
        """
        calories = nutrition_data.get("calories", 150.0)
        protein = nutrition_data.get("protein", 10.0)
        fat = nutrition_data.get("fat", 8.0)
        carbs = nutrition_data.get("carbs", 15.0)
        dish_name = nutrition_data.get("name", "菜品")
        
        if not health_goal or health_goal == "balanced":
            # 均衡模式：营养均衡即可推荐
            if calories < 300 and fat < 15:
                return True, "营养均衡，适合日常食用"
            else:
                return False, "热量或脂肪含量较高，建议适量食用"
        
        elif health_goal == "reduce_fat":
            # 减脂模式：低热量、高蛋白、低脂肪
            if calories < 250 and protein > 15 and fat < 12:
                return True, f"蛋白质丰富、热量较低，适合您的减脂目标"
            elif calories > 400 or fat > 20:
                return False, "热量或脂肪含量较高，建议减少摄入"
            else:
                return False, "热量适中，建议控制摄入量"
        
        elif health_goal == "gain_muscle":
            # 增肌模式：高蛋白、适量碳水
            if protein > 20:
                return True, f"蛋白质含量高，适合增肌期食用"
            elif protein < 10:
                return False, "蛋白质含量较低，建议选择高蛋白食物"
            else:
                return True, "蛋白质含量适中，可以适量食用"
        
        elif health_goal == "control_sugar":
            # 控糖模式：低碳水
            if carbs < 20:
                return True, f"碳水化合物含量低，适合控糖饮食"
            elif carbs > 40:
                return False, "碳水化合物含量较高，建议减少摄入"
            else:
                return False, "碳水化合物含量适中，建议适量食用"
        
        else:
            # 默认推荐
            return True, nutrition_data.get("recommendation", "营养数据仅供参考")

