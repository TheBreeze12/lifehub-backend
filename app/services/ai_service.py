"""
AI服务 - 调用通义千问API（行程生成）和火山引擎豆包AI（菜品识别和分析）
"""
import os
import json
import base64
import time
import tempfile
import logging
from typing import List, Optional, Tuple, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import dashscope
from dashscope import Generation

logger = logging.getLogger(__name__)

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
        """
        # Phase 38: RAG上下文注入
        rag_section = ""
        if rag_context:
            rag_section = f"""\n\n{rag_context}\n\n重要：请优先参考以上《中国食物成分表》数据给出营养分析，确保数据尽量准确。\n"""
        
        prompt = f"""请分析菜品"{food_name}"的营养成分和可能的过敏原，并以JSON格式返回。
{rag_section}
要求：
1. 估算每100克的营养数据
2. 给出减脂人群的饮食建议
3. 分析该菜品可能包含的八大类过敏原（乳制品、鸡蛋、鱼类、甲壳类、花生、树坚果、小麦、大豆）
4. 特别注意推理隐性过敏原（如：宫保鸡丁通常含花生；蛋炒饭含鸡蛋；炸酱面含小麦和大豆等）
5. 只返回JSON，不要其他解释
6. 如果有参考数据，营养数值应与参考数据接近
7. 列出该食材/菜品在2-4种不同烹饪方式下的热量和脂肪对比（如清蒸、红烧、油炸、水煮等），帮助用户选择更健康的烹饪方式

八大类过敏原代码对照：
- milk: 乳制品（牛奶、奶酪、黄油、奶油等）
- egg: 鸡蛋（各种蛋类及其制品）
- fish: 鱼类（各种鱼类及鱼制品）
- shellfish: 甲壳类（虾、蟹、贝类等海鲜）
- peanut: 花生（花生及花生制品）
- tree_nut: 树坚果（杏仁、核桃、腰果等）
- wheat: 小麦（面粉、面条、面包等含麸质食品）
- soy: 大豆（豆腐、豆浆、酱油等豆制品）

返回格式：
{{
    "calories": 热量数值（千卡，浮点数）,
    "protein": 蛋白质数值（克，浮点数）,
    "fat": 脂肪数值（克，浮点数）,
    "carbs": 碳水化合物数值（克，浮点数）,
    "recommendation": "给减脂人群的建议（50字以内）",
    "allergens": ["过敏原代码列表，如peanut, egg等"],
    "allergen_reasoning": "过敏原推理说明（说明为什么这道菜可能含有这些过敏原，100字以内）",
    "cooking_method_comparisons": [
        {{"method": "烹饪方式名称", "calories": 热量浮点数, "fat": 脂肪浮点数, "description": "简要说明（20字以内）"}}
    ]
}}

示例1（宫保鸡丁）：
{{
    "calories": 180.0,
    "protein": 18.0,
    "fat": 10.0,
    "carbs": 8.0,
    "recommendation": "蛋白质丰富，但花生热量较高，建议适量食用。",
    "allergens": ["peanut", "soy"],
    "allergen_reasoning": "宫保鸡丁是经典川菜，主要配料包括花生米（花生过敏原），调味通常使用酱油（大豆过敏原）。",
    "cooking_method_comparisons": [
        {{"method": "炒", "calories": 180.0, "fat": 10.0, "description": "标准做法，油量适中"}},
        {{"method": "水煮", "calories": 130.0, "fat": 5.0, "description": "水煮减少油脂"}},
        {{"method": "油炸", "calories": 260.0, "fat": 18.0, "description": "油炸热量大幅增加"}}
    ]
}}

示例2（番茄炒蛋）：
{{
    "calories": 150.0,
    "protein": 10.5,
    "fat": 8.2,
    "carbs": 6.3,
    "recommendation": "营养均衡，蛋白质含量较高，适合减脂期食用。",
    "allergens": ["egg"],
    "allergen_reasoning": "番茄炒蛋的主要食材是鸡蛋，属于蛋类过敏原。",
    "cooking_method_comparisons": [
        {{"method": "炒", "calories": 150.0, "fat": 8.2, "description": "标准做法"}},
        {{"method": "蒸蛋", "calories": 80.0, "fat": 5.0, "description": "无需额外油脂"}},
        {{"method": "煎", "calories": 200.0, "fat": 14.0, "description": "煎制需更多油"}}
    ]
}}

示例3（清蒸鲈鱼）：
{{
    "calories": 105.0,
    "protein": 19.5,
    "fat": 3.0,
    "carbs": 0.5,
    "recommendation": "高蛋白低脂肪，非常适合减脂期食用。",
    "allergens": ["fish", "soy"],
    "allergen_reasoning": "鲈鱼属于鱼类过敏原，清蒸时通常使用酱油调味（大豆过敏原）。",
    "cooking_method_comparisons": [
        {{"method": "清蒸", "calories": 105.0, "fat": 3.0, "description": "最健康，保留营养"}},
        {{"method": "红烧", "calories": 180.0, "fat": 10.0, "description": "酱汁增加热量"}},
        {{"method": "油炸", "calories": 250.0, "fat": 18.0, "description": "油炸热量最高"}}
    ]
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
        
        # 第二步：生成运动计划（传递query以便识别城市）
        trip_data = self._generate_exercise_plan(intent, preferences, calories_intake, user_location, query)
        
        return trip_data
    
    def _reverse_geocode(self, latitude: float, longitude: float) -> Optional[Dict[str, str]]:
        """逆地理编码：将经纬度转换为地理位置信息"""
        if not self.geocoder:
            return None
        
        try:
            location = self.geocoder.reverse((latitude, longitude), timeout=5, language='zh')
            if location:
                # 从 geopy Location 中提取原始地址字典
                raw = getattr(location, 'raw', {}) or {}
                address = raw.get('address', {}) if isinstance(raw.get('address', {}), dict) else {}

                city = address.get('city') or address.get('town') or address.get('village') or address.get('municipality') or ''
                district = address.get('suburb') or address.get('district') or address.get('county') or ''
                province = address.get('state') or address.get('province') or address.get('region') or ''
                country = address.get('country') or ''
                full_address = location.address or (raw.get('display_name') or '')

                return {
                    'city': city,
                    'district': district,
                    'province': province,
                    'country': country,
                    'full_address': full_address
                }
        except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
            print(f"地理编码失败: {str(e)}")
            return None
        
        return None
    
    def _extract_exercise_intent(self, query: str, preferences: dict = None, calories_intake: float = 0.0, user_location: dict = None) -> dict:
        """提取运动意图（卡路里目标、运动类型、时间等）"""
        calories_info = ""
        if calories_intake > 0:
            calories_info = f"\n用户今日已摄入卡路里：{calories_intake:.1f} kcal"
        # 当前系统日期（用于约束模型不要抄示例日期）
        from datetime import datetime
        today_str = datetime.now().date().strftime("%Y-%m-%d")
        
        # 从查询中尝试解析显式地点/地址
        explicit_place = self._extract_explicit_place_from_query(query)
        explicit_place_hint = ""
        if explicit_place and explicit_place.get("placeName"):
            ep_city = explicit_place.get("city") or ""
            ep_name = explicit_place.get("placeName")
            explicit_place_hint = f"\n用户查询包含明确地点/地址：{ep_city + (ep_name if not ep_city or ep_name.startswith(ep_city) else ep_name)}\n重要：如果查询中提供了明确地点/地址，destination必须优先使用该地点或与其同一城市的具体真实地点，不要使用模糊名称。"
        
        # 优先从查询中提取城市信息（如"我在北京"、"北京"等）
        query_city = None
        city_keywords = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "南京", "重庆", 
                        "天津", "苏州", "长沙", "郑州", "东莞", "青岛", "沈阳", "宁波", "昆明", "大连"]
        for city in city_keywords:
            if city in query:
                query_city = city
                break
        
        # 位置信息提示
        location_hint = ""
        detected_city = None
        
        # 优先使用查询中提到的城市
        if query_city:
            detected_city = query_city
            location_hint = f"""
用户查询中明确提到了城市：{query_city}
重要：请优先使用查询中提到的城市信息，而不是GPS位置信息。
请根据用户查询中提到的城市（{query_city}），在destination字段中生成具体的地点名称：
- 如果查询中明确指定了地点类型（如"公园"、"健身房"、"步道"等），请结合{query_city}生成具体名称，例如"{query_city}中央公园"、"{query_city}滨江健身步道"、"{query_city}XX体育中心"等
- 如果查询中没有指定地点，请根据{query_city}生成一个合理的运动地点名称，例如"{query_city}中央公园"、"{query_city}世纪公园"、"{query_city}XX社区健身步道"等
- 重要：不要使用"附近"、"附近XX"、"当前位置附近"这样的模糊描述，必须生成具体的地点名称，并包含城市信息（如"{query_city}XX公园"、"{query_city}XX健身步道"等）
"""
        elif user_location:
            lat = user_location['latitude']
            lon = user_location['longitude']
            
            # 尝试进行地理编码，获取具体地理位置
            geo_info = self._reverse_geocode(lat, lon)
            
            if geo_info:
                # 构建地理位置描述
                location_parts = []
                if geo_info.get('city'):
                    location_parts.append(geo_info['city'])
                    detected_city = geo_info['city']
                if geo_info.get('district'):
                    location_parts.append(geo_info['district'])
                if geo_info.get('province'):
                    location_parts.append(geo_info['province'])
                
                location_desc = '、'.join(location_parts) if location_parts else geo_info.get('full_address', '')
                
                location_hint = f"""
用户GPS位置：{location_desc}（纬度 {lat:.6f}, 经度 {lon:.6f}）
请根据用户所在城市和区域，在destination字段中生成具体的地点名称：
- 如果查询中明确指定了地点类型（如"公园"、"健身房"、"步道"等），请结合用户所在城市生成具体名称，例如"{detected_city}中央公园"、"{detected_city}滨江健身步道"、"{detected_city}XX体育中心"等
- 如果查询中没有指定地点，请根据用户所在城市和区域生成一个合理的运动地点名称，例如"{detected_city}中央公园"、"{detected_city}世纪公园"、"{detected_city}XX社区健身步道"等
- 重要：不要使用"附近"、"附近XX"、"当前位置附近"这样的模糊描述，必须生成具体的地点名称，并包含城市信息（如"{detected_city}XX公园"、"{detected_city}XX健身步道"等）
"""
            else:
                # 如果地理编码失败，使用经纬度
                location_hint = f"""
用户GPS位置：纬度 {lat:.6f}, 经度 {lon:.6f}
请根据用户位置信息，在destination字段中生成具体的地点名称：
- 如果查询中明确指定了地点类型（如"公园"、"健身房"、"步道"等），请结合位置信息生成具体名称，例如"中央公园"、"滨江健身步道"、"XX体育中心"等
- 如果查询中没有指定地点，请根据位置信息生成一个合理的运动地点名称，例如"中央公园"、"社区健身步道"等
- 重要：不要使用"附近"、"附近XX"、"当前位置附近"这样的模糊描述，必须生成具体的地点名称（如"中央公园"、"XX健身步道"等）
"""
        
        prompt = f"""请从以下用户查询中提取餐后运动规划的关键信息，并以JSON格式返回。

用户查询："{query}"
{calories_info}
    {explicit_place_hint}
{location_hint}

系统当前日期：{today_str}

要求提取的信息：
1. destination: 运动区域/起点（必须是具体的地点名称，不要使用"附近"、"附近XX"、"当前位置附近"等模糊描述）
   - 优先识别查询中明确提到的城市和地点（如"我在北京"、"北京XX公园"等），直接使用查询中的城市信息
   - 如果查询中明确指定了地点（如"XX公园"、"健身房"等），直接使用该地点名称，并包含城市信息
   - 如果查询中只指定了地点类型（如"公园"、"步道"），请结合位置信息中的城市生成一个具体的地点名称（如"北京中央公园"、"上海滨江健身步道"等）
   - 如果查询中没有指定地点，请根据位置信息中的城市生成一个合理的具体地点名称（如"北京中央公园"、"上海世纪公园"等）
2. startDate: 运动开始日期（YYYY-MM-DD格式）
   - 如果查询中提到"今天"、"今日"，使用今天的日期
   - 如果查询中提到"明天"、"明日"，使用明天的日期
   - 如果查询中提到"周末"、"周六"、"周日"，计算最近的周末日期
   - 如果查询中提到具体日期（如"1月27日"），转换为YYYY-MM-DD格式
   - 如果未指定，使用今天的日期
3. endDate: 运动结束日期（YYYY-MM-DD格式）
   - 如果查询中提到"周末"（通常指周六和周日两天），endDate应该是周日的日期
   - 如果查询中提到"三天"、"3天"等，endDate应该是startDate之后2天的日期
   - 如果查询中提到"一周"、"7天"等，endDate应该是startDate之后6天的日期
   - 如果未指定多天，endDate通常与startDate相同
4. days: 运动天数（整数）
   - 如果查询中提到"周末"，days应该是2（周六和周日）
   - 如果查询中提到"三天"、"3天"等，days应该是3
   - 如果查询中提到"一周"、"7天"等，days应该是7
   - 如果未指定，days通常是1
5. calories_target: 目标消耗卡路里（整数，单位：kcal，如果未指定则根据已摄入卡路里推算）
6. exercise_type: 运动类型偏好（如"散步"、"跑步"、"骑行"等，如果未指定则为null）

只返回JSON，不要其他解释。

严格禁止抄写任何示例值（尤其是日期）。startDate/endDate 必须根据用户查询或当前系统日期 {today_str} 计算。

注意：
- 如果查询中提到"周末"，需要计算最近的周六和周日日期，days=2
- destination必须是具体地点名称，不能包含"附近"、"附近XX"等模糊词汇
"""
        
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
                    
                    # 后处理：修复日期和天数
                    intent = self._fix_date_and_days(intent)
                    
                    # 如果没有指定卡路里目标，根据已摄入卡路里推算
                    if not intent.get("calories_target") and calories_intake > 0:
                        # 建议消耗已摄入卡路里的30-50%
                        intent["calories_target"] = int(calories_intake * 0.4)
                    elif not intent.get("calories_target"):
                        intent["calories_target"] = 200  # 默认200卡路里
                    
                    # 确保destination不包含"附近"等模糊词汇
                    destination = intent.get("destination", "")
                    if "附近" in destination or destination.startswith("附近"):
                        # 移除"附近"前缀，生成具体名称
                        destination = destination.replace("附近", "").strip()
                        if not destination:
                            destination = "运动场所"
                        intent["destination"] = destination
                    
                    # 如果查询提供了明确地点/地址，优先覆盖destination
                    if explicit_place and explicit_place.get("placeName"):
                        city_prefix = explicit_place.get("city")
                        cleaned = self._sanitize_place_name(explicit_place["placeName"], city_prefix=city_prefix)
                        if cleaned:
                            intent["destination"] = cleaned
                    
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
            # 返回默认意图
            from datetime import datetime, timedelta
            today = datetime.now().date()
            calories_target = int(calories_intake * 0.4) if calories_intake > 0 else 200
            # 如果用户提供了位置，destination使用"当前位置附近"，否则使用"附近"
            default_destination = "当前位置附近" if user_location else "附近"
            return {
                "destination": default_destination,
                "startDate": today.strftime("%Y-%m-%d"),
                "endDate": today.strftime("%Y-%m-%d"),
                "days": 1,
                "calories_target": calories_target,
                "exercise_type": None
            }
    
    def _generate_exercise_plan(self, intent: dict, preferences: dict = None, calories_intake: float = 0.0, user_location: dict = None, query: str = "") -> dict:
        """生成运动计划"""
        destination = intent.get("destination", "附近")
        # 如果destination仍然是模糊描述，且用户提供了位置，尝试生成更具体的描述
        if user_location and destination in ["附近", "当前位置附近", "附近公园", "附近步道"]:
            # 根据位置信息生成一个更具体的地点名称
            # 这里可以根据需要接入地理编码API，或者使用AI生成
            # 暂时使用一个通用的描述，但会在prompt中要求AI生成具体名称
            destination = "附近运动场所"  # 这个会在prompt中被AI替换为具体名称
        
        # 明确查询中的地点优先
        explicit_place = self._extract_explicit_place_from_query(query)
        if explicit_place and explicit_place.get("placeName"):
            city_prefix = explicit_place.get("city")
            cleaned = self._sanitize_place_name(explicit_place["placeName"], city_prefix=city_prefix)
            if cleaned:
                destination = cleaned
        
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
        
        # 优先从查询中提取城市信息
        query_city = None
        city_keywords = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "南京", "重庆", 
                        "天津", "苏州", "长沙", "郑州", "东莞", "青岛", "沈阳", "宁波", "昆明", "大连"]
        for city in city_keywords:
            if city in query:
                query_city = city
                break
        
        # 从intent的destination中提取城市（如果AI已经识别）
        detected_city = None
        if "destination" in intent:
            dest = intent.get("destination", "")
            for city in city_keywords:
                if city in dest:
                    detected_city = city
                    break
        
        # 优先使用查询中的城市
        final_city = query_city or detected_city
        
        location_context = ""
        if final_city:
            # 如果检测到城市（来自查询或intent），优先使用
            location_context = f"""
用户所在城市：{final_city}（优先使用查询中提到的城市信息）
重要提示：
1. 请根据用户所在城市（{final_city}），在placeName字段中生成具体、真实的地点名称（如"{final_city}中央公园"、"{final_city}滨江健身步道"、"{final_city}XX体育中心"等）
2. 不要使用"附近公园"、"附近步道"这样的模糊描述，要生成具体的地点名称，并包含城市信息
3. 可以根据{final_city}的城市特征生成合理的地点名称（例如：如果在北京，可以是"北京中央公园"、"北京奥林匹克公园"、"北京朝阳公园"等；如果在上海，可以是"上海世纪公园"、"上海滨江健身步道"、"上海外滩"等）
4. **地点多样性**：如果有多个运动节点，每个节点的placeName必须不同，要推荐{final_city}不同的运动地点（如"北京中央公园"、"北京奥林匹克公园"、"北京朝阳公园"、"北京颐和园"等）
5. 所有地点名称都应该包含城市信息，例如"{final_city}XX公园"、"{final_city}XX健身步道"等
"""
        elif user_location:
            lat = user_location['latitude']
            lon = user_location['longitude']
            
            # 尝试进行地理编码，获取具体地理位置
            geo_info = self._reverse_geocode(lat, lon)
            
            if geo_info:
                # 构建地理位置描述
                location_parts = []
                city_name = None
                if geo_info.get('city'):
                    location_parts.append(geo_info['city'])
                    city_name = geo_info['city']
                if geo_info.get('district'):
                    location_parts.append(geo_info['district'])
                if geo_info.get('province'):
                    location_parts.append(geo_info['province'])
                
                location_desc = '、'.join(location_parts) if location_parts else geo_info.get('full_address', '')
                
                location_context = f"""
用户GPS位置：{location_desc}（纬度 {lat:.6f}, 经度 {lon:.6f}）
重要提示：
1. 请根据用户所在城市和区域，在placeName字段中生成具体、真实的地点名称（如"{city_name}中央公园"、"{city_name}滨江健身步道"、"{city_name}XX体育中心"等）
2. 不要使用"附近公园"、"附近步道"这样的模糊描述，要生成具体的地点名称，并包含城市信息
3. 可以根据用户所在城市和区域特征生成合理的地点名称
4. **地点多样性**：如果有多个运动节点，每个节点的placeName必须不同，要推荐不同的运动地点
5. 所有地点名称都应该包含城市信息，例如"{city_name}XX公园"、"{city_name}XX健身步道"等
"""
            else:
                # 如果地理编码失败，使用经纬度
                location_context = f"""
用户GPS位置：纬度 {lat:.6f}, 经度 {lon:.6f}
重要提示：
1. 请根据用户位置信息，在placeName字段中生成具体、真实的地点名称（如"XX公园"、"XX健身步道"、"XX体育中心"等）
2. 不要使用"附近公园"、"附近步道"这样的模糊描述，要生成具体的地点名称
3. **地点多样性**：如果有多个运动节点，每个节点的placeName必须不同，要推荐不同的运动地点
4. 可以根据位置特征生成合理的地点名称（例如：如果在城市中心，可以是"中央公园"；如果在住宅区，可以是"XX社区公园"等）
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
        
        prompt = f"""请为以下餐后运动需求生成详细的运动计划，并以JSON格式返回。

运动区域：{destination}
运动日期：{start_date} 至 {end_date}（共{days}天）
目标消耗卡路里：{calories_target} kcal
{exercise_type_text}
{preference_text}

要求：
1. 生成具体的运动安排，包括运动类型、地点、时长等
2. 合理安排运动强度和时间，确保能达到目标卡路里消耗
3. 考虑餐后运动的特点（建议餐后30-60分钟开始）
4. 根据运动类型和用户位置推荐合适的运动地点
5. 如果days>1，需要为每一天生成运动节点，dayIndex从1开始递增
6. 每个节点需要包含：
   - dayIndex: 第几天（从1开始，如果days>1，需要为每一天生成节点）
   - startTime: 开始时间（HH:mm格式，建议餐后时间）
   - placeName: 运动地点名称（必须是具体的地点名称，如"中央公园"、"滨江健身步道"、"XX体育中心"等，绝对不要使用"附近公园"、"附近XX"、"附近"等模糊描述）
   - placeType: 运动类型（walking/running/cycling/park/gym/indoor/outdoor）
   - duration: 运动时长（分钟）
   - cost: 预计消耗卡路里（kcal，注意：这里用cost字段存储卡路里）
   - notes: 运动建议、注意事项等

重要：
1. title必须个性化，不要总是"餐后运动计划"
2. placeName字段必须包含具体的地点名称，不能是"附近"、"附近XX"这样的模糊描述
3. 如果days>1，需要为每一天生成至少一个运动节点
4. **地点多样性要求**：如果有多个运动节点（items数组中有多个元素），每个节点的placeName必须不同，要推荐不同的运动地点。例如：
   - 如果生成4个节点，可以分别是："中央公园"、"滨江健身步道"、"XX体育中心"、"社区健身广场"
   - 不要所有节点都使用同一个地点名称
   - 可以根据不同的运动类型推荐不同的地点（如散步在公园，跑步在步道，力量训练在健身房等）
5. **优先使用查询中的城市信息**：如果用户查询中明确提到了城市（如"我在北京"、"北京"等），请优先使用查询中的城市信息，而不是GPS位置信息

只返回JSON，不要其他解释。

返回格式：
{{
    "title": "周末慢跑健身计划",
    "destination": "{destination}",
    "startDate": "{start_date}",
    "endDate": "{end_date}",
    "items": [
        {{
            "dayIndex": 1,
            "startTime": "19:00",
            "placeName": "中央公园",
            "placeType": "walking",
            "duration": 30,
            "cost": 150,
            "notes": "餐后散步，建议慢走"
        }},
        {{
            "dayIndex": 1,
            "startTime": "20:00",
            "placeName": "滨江健身步道",
            "placeType": "running",
            "duration": 20,
            "cost": 150,
            "notes": "慢跑，注意控制强度"
        }}
    ]
}}"""
        
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
                    # 确保有travelers字段（兼容性）
                    if "travelers" not in trip_data:
                        trip_data["travelers"] = ["本人"]
                    
                    # 后处理：确保destination和placeName都是具体的地点名称
                    trip_data = self._ensure_specific_locations(trip_data, user_location, city_prefix=final_city)
                    # 进一步规范与清洗地点名称，避免重复与虚构词
                    trip_data = self._normalize_plan_locations(trip_data, city_prefix=final_city)
                    
                    # 后处理：确保地点多样性
                    trip_data = self._ensure_location_diversity(trip_data)
                    
                    # 后处理：根据提示词或当前时间动态调整startTime，避免固定时间
                    trip_data = self._adjust_plan_times(trip_data, intent, query)
                    
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

    def _adjust_plan_times(self, trip_data: dict, intent: dict, query: str) -> dict:
        """根据提示词（早餐/午餐/晚餐/早上/下午/晚上）或当前时间，动态设置每个节点的startTime，避免固定时间"""
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

        now_dt = datetime.now()

        def _compute_time_for_day(day_index: int) -> str:
            # 动态偏移：30-60分钟范围内随dayIndex变化
            offset_min = 30 + ((day_index * 11) % 31)  # 30..60

            # 根据提示词选择基础时间
            if hint == "breakfast":
                base_t = time(8, 0)
            elif hint == "lunch":
                base_t = time(12, 0)
            elif hint == "dinner":
                base_t = time(19, 0)
            elif hint == "afternoon":
                base_t = time(15, 0)
            else:
                # 无提示词：如果第一天且是今天，用当前时间+偏移；否则用傍晚基准
                if day_index == 1 and start_date == today:
                    t = (now_dt + timedelta(minutes=offset_min)).time()
                    return f"{t.hour:02d}:{t.minute:02d}"
                base_t = time(18, 0)

            dt = datetime.combine(today, base_t) + timedelta(minutes=offset_min)
            # 限制在合理范围（06:30 - 21:30），超界则截断
            min_dt = datetime.combine(today, time(6, 30))
            max_dt = datetime.combine(today, time(21, 30))
            if dt < min_dt:
                dt = min_dt
            if dt > max_dt:
                dt = max_dt
            return f"{dt.hour:02d}:{dt.minute:02d}"

        items = trip_data.get("items") or []
        for item in items:
            day_index = 1
            try:
                di = item.get("dayIndex")
                if isinstance(di, int):
                    day_index = di
                elif isinstance(di, str) and di.isdigit():
                    day_index = int(di)
            except Exception:
                pass
            item["startTime"] = _compute_time_for_day(day_index)

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
        """使用豆包AI识别菜单图片"""
        _recog_start = time.time()
        try:
            # 构建base64 data URI（尝试使用data URI格式）
            image_data_uri = f"data:image/jpeg;base64,{image_base64}"
            
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
        """使用豆包AI从餐前图片提取特征"""
        try:
            image_data_uri = f"data:image/jpeg;base64,{image_base64}"
            
            prompt = """请分析这张餐前食物图片，识别图片中的所有菜品，并估算每个菜品的份量和营养成分。

要求：
1. 识别图片中所有可见的菜品
2. 根据视觉判断估算每个菜品的重量（克）
3. 根据菜品类型和重量估算热量、蛋白质、脂肪、碳水化合物
4. 计算所有菜品的总营养成分
5. 只返回JSON，不要其他解释

返回格式：
{
    "dishes": [
        {
            "name": "菜品名称",
            "estimated_weight": 重量数值（克，整数）,
            "estimated_calories": 热量数值（千卡，浮点数）,
            "estimated_protein": 蛋白质数值（克，浮点数）,
            "estimated_fat": 脂肪数值（克，浮点数）,
            "estimated_carbs": 碳水化合物数值（克，浮点数）
        }
    ],
    "total_estimated_calories": 总热量（千卡，浮点数）,
    "total_estimated_protein": 总蛋白质（克，浮点数）,
    "total_estimated_fat": 总脂肪（克，浮点数）,
    "total_estimated_carbs": 总碳水化合物（克，浮点数）
}

示例（一份红烧肉+清炒时蔬）：
{
    "dishes": [
        {
            "name": "红烧肉",
            "estimated_weight": 200,
            "estimated_calories": 500.0,
            "estimated_protein": 25.0,
            "estimated_fat": 35.0,
            "estimated_carbs": 10.0
        },
        {
            "name": "清炒时蔬",
            "estimated_weight": 150,
            "estimated_calories": 80.0,
            "estimated_protein": 3.0,
            "estimated_fat": 5.0,
            "estimated_carbs": 8.0
        }
    ],
    "total_estimated_calories": 580.0,
    "total_estimated_protein": 28.0,
    "total_estimated_fat": 40.0,
    "total_estimated_carbs": 18.0
}

如果图片不是食物图片，返回空dishes数组：
{
    "dishes": [],
    "total_estimated_calories": 0,
    "total_estimated_protein": 0,
    "total_estimated_fat": 0,
    "total_estimated_carbs": 0
}

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
                return self._parse_before_meal_features(content)
            else:
                raise Exception("豆包AI返回空响应")
                
        except Exception as e:
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
        """使用豆包AI对比餐前餐后图片"""
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
            
            prompt = f"""请对比这两张图片（餐前和餐后），分析用户吃掉了多少食物，剩余了多少。

餐前识别到的菜品信息：
{before_dishes_text if before_dishes_text else "未识别到具体菜品"}

要求：
1. 对比餐前图片（第一张）和餐后图片（第二张）
2. 估算每个菜品的剩余比例（0表示吃完，1表示没动）
3. 计算整体剩余比例
4. 给出简短的对比分析说明
5. 只返回JSON，不要其他解释

返回格式：
{{
    "dishes": [
        {{
            "name": "菜品名称",
            "remaining_ratio": 剩余比例（0-1的浮点数，0表示全部吃完，1表示完全没动）,
            "remaining_weight": 估算剩余重量（克，整数）
        }}
    ],
    "overall_remaining_ratio": 整体剩余比例（0-1的浮点数）,
    "comparison_analysis": "对比分析说明（50字以内，描述用户大约吃掉了多少）"
}}

示例（吃掉了大部分红烧肉，吃完了所有蔬菜）：
{{
    "dishes": [
        {{"name": "红烧肉", "remaining_ratio": 0.25, "remaining_weight": 50}},
        {{"name": "清炒时蔬", "remaining_ratio": 0.0, "remaining_weight": 0}}
    ],
    "overall_remaining_ratio": 0.15,
    "comparison_analysis": "您吃掉了约85%的食物，红烧肉剩余约1/4，蔬菜全部吃完。"
}}

示例（几乎没吃）：
{{
    "dishes": [
        {{"name": "红烧肉", "remaining_ratio": 0.9, "remaining_weight": 180}},
        {{"name": "清炒时蔬", "remaining_ratio": 0.8, "remaining_weight": 120}}
    ],
    "overall_remaining_ratio": 0.85,
    "comparison_analysis": "您只吃了约15%的食物，大部分食物还剩余在盘中。"
}}

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
                return self._parse_comparison_result(content)
            else:
                raise Exception("豆包AI返回空响应")
                
        except Exception as e:
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

