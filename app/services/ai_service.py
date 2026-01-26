"""
AI服务 - 调用通义千问API（行程生成）和火山引擎豆包AI（菜品识别和分析）
"""
import os
import json
import base64
import tempfile
from typing import List, Optional, Tuple
import dashscope
from dashscope import Generation

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
    
    def analyze_food_nutrition(self, food_name: str) -> dict:
        """
        分析菜品营养成分（使用豆包AI）
        
        Args:
            food_name: 菜品名称
            
        Returns:
            包含营养数据的字典
            
        Raises:
            ValueError: 如果豆包AI未初始化或调用失败
        """
        if not self.ark_client:
            raise ValueError("豆包AI未初始化，请检查ARK_API_KEY环境变量")
        
        return self._analyze_food_nutrition_with_ark(food_name)
    
    def _analyze_food_nutrition_with_ark(self, food_name: str) -> dict:
        """使用豆包AI分析菜品营养"""
        prompt = self._build_nutrition_prompt(food_name)
        
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
            
            if content:
                return self._parse_nutrition_response(content, food_name)
            else:
                raise Exception("豆包AI返回空响应")
                
        except Exception as e:
            print(f"豆包AI调用失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _build_nutrition_prompt(self, food_name: str) -> str:
        """构建营养分析Prompt"""
        prompt = f"""请分析菜品"{food_name}"的营养成分，并以JSON格式返回。

要求：
1. 估算每100克的营养数据
2. 给出减脂人群的饮食建议
3. 只返回JSON，不要其他解释

返回格式：
{{
    "calories": 热量数值（千卡，浮点数）,
    "protein": 蛋白质数值（克，浮点数）,
    "fat": 脂肪数值（克，浮点数）,
    "carbs": 碳水化合物数值（克，浮点数）,
    "recommendation": "给减脂人群的建议（50字以内）"
}}

示例：
{{
    "calories": 150.0,
    "protein": 10.5,
    "fat": 8.2,
    "carbs": 6.3,
    "recommendation": "这道菜营养均衡，蛋白质含量较高，适合减脂期食用。建议控制油量。"
}}

现在请分析"{food_name}"："""
        
        return prompt
    
    def _parse_nutrition_response(self, content: str, food_name: str) -> dict:
        """解析AI返回的营养数据"""
        try:
            # 尝试从内容中提取JSON
            # 有时AI会返回带有额外文字的内容，需要提取JSON部分
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                # 确保所有必需字段存在
                result = {
                    "name": food_name,
                    "calories": float(data.get("calories", 150.0)),
                    "protein": float(data.get("protein", 10.0)),
                    "fat": float(data.get("fat", 8.0)),
                    "carbs": float(data.get("carbs", 15.0)),
                    "recommendation": data.get("recommendation", "营养数据仅供参考")
                }
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
            "recommendation": f"{food_name}的营养数据暂时无法获取，建议适量食用。"
        }
    
    def generate_trip(self, query: str, preferences: dict = None) -> dict:
        """
        生成行程计划
        
        Args:
            query: 用户查询文本
            preferences: 用户偏好（健康目标、过敏原等）
            
        Returns:
            包含行程数据的字典
        """
        # 第一步：提取意图
        intent = self._extract_trip_intent(query, preferences)
        
        # 第二步：生成行程
        trip_data = self._generate_trip_plan(intent, preferences)
        
        return trip_data
    
    def _extract_trip_intent(self, query: str, preferences: dict = None) -> dict:
        """提取行程意图（时间、目的地、人群等）"""
        prompt = f"""请从以下用户查询中提取行程规划的关键信息，并以JSON格式返回。

用户查询："{query}"

要求提取的信息：
1. destination: 目的地（城市或景点名称）
2. startDate: 开始日期（YYYY-MM-DD格式，如果未指定则使用当前日期）
3. endDate: 结束日期（YYYY-MM-DD格式，如果未指定则根据天数推算）
4. days: 行程天数（整数）
5. travelers: 同行人员（数组，如["本人", "父母", "孩子"]）
6. budget: 预算（整数，单位：元，如果未指定则为null）

只返回JSON，不要其他解释。

返回格式：
{{
    "destination": "目的地",
    "startDate": "2026-01-25",
    "endDate": "2026-01-26",
    "days": 2,
    "travelers": ["本人", "孩子"],
    "budget": 2000
}}"""
        
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
                    return intent
                else:
                    raise ValueError("未找到JSON数据")
            else:
                raise Exception(f"API调用失败: {response.message}")
                
        except Exception as e:
            print(f"提取意图失败: {str(e)}")
            # 返回默认意图
            from datetime import datetime, timedelta
            today = datetime.now().date()
            return {
                "destination": "未指定",
                "startDate": today.strftime("%Y-%m-%d"),
                "endDate": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
                "days": 1,
                "travelers": ["本人"],
                "budget": None
            }
    
    def _generate_trip_plan(self, intent: dict, preferences: dict = None) -> dict:
        """生成行程计划"""
        destination = intent.get("destination", "未指定")
        days = intent.get("days", 1)
        travelers = intent.get("travelers", ["本人"])
        
        # 构建Prompt
        preference_text = ""
        if preferences:
            health_goal = preferences.get("healthGoal")
            allergens = preferences.get("allergens", [])
            if health_goal:
                preference_text += f"健康目标：{health_goal}。"
            if allergens:
                preference_text += f"过敏原：{', '.join(allergens)}。"
        
        start_date = intent.get("startDate", "2026-01-25")
        end_date = intent.get("endDate", "2026-01-26")
        
        prompt = f"""请为以下行程生成详细的行程计划，并以JSON格式返回。

目的地：{destination}
行程天数：{days}天
同行人员：{', '.join(travelers)}
{preference_text}

要求：
1. 生成每天的具体行程安排，包括景点、餐饮、交通等
2. 合理安排时间，避免行程过于紧张
3. 考虑同行人员的特点（如带娃需要考虑适合孩子的景点）
4. 餐饮推荐要考虑健康目标和过敏原
5. 每个节点需要包含：dayIndex（第几天）、startTime（开始时间HH:mm）、placeName（地点名称）、placeType（类型：attraction/dining/transport/accommodation）、duration（预计时长，分钟）、notes（备注）

只返回JSON，不要其他解释。

返回格式：
{{
    "title": "行程标题",
    "destination": "{destination}",
    "startDate": "{start_date}",
    "endDate": "{end_date}",
    "items": [
        {{
            "dayIndex": 1,
            "startTime": "09:00",
            "placeName": "景点名称",
            "placeType": "attraction",
            "duration": 180,
            "notes": "建议游玩3小时"
        }},
        {{
            "dayIndex": 1,
            "startTime": "12:30",
            "placeName": "餐厅名称",
            "placeType": "dining",
            "duration": 90,
            "notes": "推荐菜品"
        }}
    ]
}}"""
        
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
                    return trip_data
                else:
                    raise ValueError("未找到JSON数据")
            else:
                raise Exception(f"API调用失败: {response.message}")
                
        except Exception as e:
            print(f"生成行程失败: {str(e)}")
            # 返回默认行程
            return self._get_default_trip(intent)
    
    def _get_default_trip(self, intent: dict) -> dict:
        """返回默认行程（当AI调用失败时）"""
        destination = intent.get("destination", "未指定")
        start_date = intent.get("startDate", "2026-01-25")
        end_date = intent.get("endDate", "2026-01-26")
        days = intent.get("days", 1)
        travelers = intent.get("travelers", ["本人"])
        
        return {
            "title": f"{destination}{days}日游",
            "destination": destination,
            "startDate": start_date,
            "endDate": end_date,
            "travelers": travelers,
            "items": [
                {
                    "dayIndex": 1,
                    "startTime": "09:00",
                    "placeName": f"{destination}主要景点",
                    "placeType": "attraction",
                    "duration": 180,
                    "notes": "建议游玩"
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
            
            # 对每个菜品分析营养成分
            dishes = []
            for dish_name in dish_names:
                # 获取营养数据
                nutrition_data = self.analyze_food_nutrition(dish_name)
                
                # 根据健康目标生成推荐理由
                is_recommended, reason = self._generate_recommendation(
                    nutrition_data, 
                    health_goal
                )
                
                dishes.append({
                    "name": dish_name,
                    "calories": nutrition_data["calories"],
                    "protein": nutrition_data["protein"],
                    "fat": nutrition_data["fat"],
                    "carbs": nutrition_data["carbs"],
                    "isRecommended": is_recommended,
                    "reason": reason
                })
            
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
            
            if content:
                print(content)
                return self._parse_dish_names_from_content(content)
            else:
                raise Exception("无法从响应中提取内容")
                
        except Exception as e:
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

