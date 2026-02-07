"""
Phase 57: Few-shot Prompt模板管理服务

集中管理所有AI调用的Prompt模板，支持：
- 内置默认模板（6种AI调用类型）
- Few-shot示例管理（增删查）
- 动态变量替换
- 模板版本管理
- JSON文件持久化
- 线程安全访问
"""

import os
import json
import copy
import logging
import threading
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class PromptTemplateService:
    """Few-shot Prompt模板管理服务"""

    def __init__(self, templates_dir: Optional[str] = None):
        """
        初始化模板服务

        Args:
            templates_dir: 模板JSON文件存储目录，默认为 data/prompt_templates/
        """
        self._lock = threading.RLock()
        self._templates: Dict[str, dict] = {}

        if templates_dir is None:
            # 默认目录: 项目根/data/prompt_templates/
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            templates_dir = os.path.join(project_root, "data", "prompt_templates")

        self._templates_dir = templates_dir
        os.makedirs(self._templates_dir, exist_ok=True)

        # 注册内置默认模板
        self._register_builtin_templates()

        # 从目录加载自定义模板（覆盖同名内置模板）
        self.load_templates_from_dir()

    # ──────────────────────────────────────────────
    # 内置模板定义
    # ──────────────────────────────────────────────
    def _register_builtin_templates(self):
        """注册所有内置默认模板"""
        self._templates["food_analysis"] = self._builtin_food_analysis()
        self._templates["exercise_intent"] = self._builtin_exercise_intent()
        self._templates["trip_generation"] = self._builtin_trip_generation()
        self._templates["menu_recognition"] = self._builtin_menu_recognition()
        self._templates["before_meal_features"] = self._builtin_before_meal_features()
        self._templates["meal_comparison"] = self._builtin_meal_comparison()

    @staticmethod
    def _builtin_food_analysis() -> dict:
        return {
            "version": "1.0",
            "description": "菜品营养分析Prompt模板（含过敏原推理 + RAG上下文 + 烹饪方式对比）",
            "system_prompt": (
                "你是一位专业的营养分析师，擅长分析中国菜品的营养成分、过敏原和烹饪方式差异。"
                "你的回答必须是严格的JSON格式，不要包含任何额外文字。"
            ),
            "few_shot_examples": [
                {
                    "input": "请分析菜品\"宫保鸡丁\"的营养成分和可能的过敏原。",
                    "output": json.dumps({
                        "calories": 180.0,
                        "protein": 18.0,
                        "fat": 10.0,
                        "carbs": 8.0,
                        "recommendation": "蛋白质丰富，但花生热量较高，建议适量食用。",
                        "allergens": ["peanut", "soy"],
                        "allergen_reasoning": "宫保鸡丁是经典川菜，主要配料包括花生米（花生过敏原），调味通常使用酱油（大豆过敏原）。",
                        "cooking_method_comparisons": [
                            {"method": "炒", "calories": 180.0, "fat": 10.0, "description": "标准做法，油量适中"},
                            {"method": "水煮", "calories": 130.0, "fat": 5.0, "description": "水煮减少油脂"},
                            {"method": "油炸", "calories": 260.0, "fat": 18.0, "description": "油炸热量大幅增加"}
                        ]
                    }, ensure_ascii=False),
                },
                {
                    "input": "请分析菜品\"番茄炒蛋\"的营养成分和可能的过敏原。",
                    "output": json.dumps({
                        "calories": 150.0,
                        "protein": 10.5,
                        "fat": 8.2,
                        "carbs": 6.3,
                        "recommendation": "营养均衡，蛋白质含量较高，适合减脂期食用。",
                        "allergens": ["egg"],
                        "allergen_reasoning": "番茄炒蛋的主要食材是鸡蛋，属于蛋类过敏原。",
                        "cooking_method_comparisons": [
                            {"method": "炒", "calories": 150.0, "fat": 8.2, "description": "标准做法"},
                            {"method": "蒸蛋", "calories": 80.0, "fat": 5.0, "description": "无需额外油脂"},
                            {"method": "煎", "calories": 200.0, "fat": 14.0, "description": "煎制需更多油"}
                        ]
                    }, ensure_ascii=False),
                },
                {
                    "input": "请分析菜品\"清蒸鲈鱼\"的营养成分和可能的过敏原。",
                    "output": json.dumps({
                        "calories": 105.0,
                        "protein": 19.5,
                        "fat": 3.0,
                        "carbs": 0.5,
                        "recommendation": "高蛋白低脂肪，非常适合减脂期食用。",
                        "allergens": ["fish", "soy"],
                        "allergen_reasoning": "鲈鱼属于鱼类过敏原，清蒸时通常使用酱油调味（大豆过敏原）。",
                        "cooking_method_comparisons": [
                            {"method": "清蒸", "calories": 105.0, "fat": 3.0, "description": "最健康，保留营养"},
                            {"method": "红烧", "calories": 180.0, "fat": 10.0, "description": "酱汁增加热量"},
                            {"method": "油炸", "calories": 250.0, "fat": 18.0, "description": "油炸热量最高"}
                        ]
                    }, ensure_ascii=False),
                },
            ],
            "user_prompt_template": (
                "请分析菜品\"{food_name}\"的营养成分和可能的过敏原，并以JSON格式返回。\n"
                "{rag_context}\n"
                "要求：\n"
                "1. 估算每100克的营养数据\n"
                "2. 给出减脂人群的饮食建议\n"
                "3. 分析该菜品可能包含的八大类过敏原（乳制品、鸡蛋、鱼类、甲壳类、花生、树坚果、小麦、大豆）\n"
                "4. 特别注意推理隐性过敏原（如：宫保鸡丁通常含花生；蛋炒饭含鸡蛋；炸酱面含小麦和大豆等）\n"
                "5. 只返回JSON，不要其他解释\n"
                "6. 如果有参考数据，营养数值应与参考数据接近\n"
                "7. 列出该食材/菜品在2-4种不同烹饪方式下的热量和脂肪对比\n\n"
                "八大类过敏原代码对照：\n"
                "- milk: 乳制品  - egg: 鸡蛋  - fish: 鱼类  - shellfish: 甲壳类\n"
                "- peanut: 花生  - tree_nut: 树坚果  - wheat: 小麦  - soy: 大豆\n\n"
                "返回格式：\n"
                '{{\n'
                '    "calories": 热量数值,\n'
                '    "protein": 蛋白质数值,\n'
                '    "fat": 脂肪数值,\n'
                '    "carbs": 碳水化合物数值,\n'
                '    "recommendation": "建议",\n'
                '    "allergens": ["过敏原代码"],\n'
                '    "allergen_reasoning": "推理说明",\n'
                '    "cooking_method_comparisons": [\n'
                '        {{"method": "方式", "calories": 数值, "fat": 数值, "description": "说明"}}\n'
                '    ]\n'
                '}}\n\n'
                '现在请分析"{food_name}"：'
            ),
        }

    @staticmethod
    def _builtin_exercise_intent() -> dict:
        return {
            "version": "1.0",
            "description": "运动意图提取Prompt模板（槽位提取：目的地、日期、卡路里目标、运动类型）",
            "system_prompt": (
                "你是一个运动规划意图解析助手。你的任务是从用户查询中提取餐后运动规划的关键信息，"
                "并以严格的JSON格式返回。不要包含任何额外文字。"
            ),
            "few_shot_examples": [
                {
                    "input": "用户查询：\"餐后散步30分钟\"\n系统当前日期：2026-03-01",
                    "output": json.dumps({
                        "destination": "社区公园",
                        "startDate": "2026-03-01",
                        "endDate": "2026-03-01",
                        "days": 1,
                        "calories_target": 150,
                        "exercise_type": "散步"
                    }, ensure_ascii=False),
                },
                {
                    "input": "用户查询：\"周末在北京跑步消耗500卡路里\"\n系统当前日期：2026-03-03",
                    "output": json.dumps({
                        "destination": "北京奥林匹克公园",
                        "startDate": "2026-03-07",
                        "endDate": "2026-03-08",
                        "days": 2,
                        "calories_target": 500,
                        "exercise_type": "跑步"
                    }, ensure_ascii=False),
                },
                {
                    "input": "用户查询：\"规划餐后运动，消耗300卡路里\"\n系统当前日期：2026-03-01",
                    "output": json.dumps({
                        "destination": "健身步道",
                        "startDate": "2026-03-01",
                        "endDate": "2026-03-01",
                        "days": 1,
                        "calories_target": 300,
                        "exercise_type": None
                    }, ensure_ascii=False),
                },
            ],
            "user_prompt_template": (
                "请从以下用户查询中提取餐后运动规划的关键信息，并以JSON格式返回。\n\n"
                "用户查询：\"{query}\"\n"
                "{calories_info}\n"
                "{explicit_place_hint}\n"
                "{location_hint}\n\n"
                "系统当前日期：{today_date}\n\n"
                "要求提取的信息：\n"
                "1. destination: 运动区域/起点（具体地点名称）\n"
                "2. startDate: YYYY-MM-DD格式\n"
                "3. endDate: YYYY-MM-DD格式\n"
                "4. days: 运动天数（整数）\n"
                "5. calories_target: 目标消耗卡路里（整数，kcal）\n"
                "6. exercise_type: 运动类型偏好（如未指定则为null）\n\n"
                "只返回JSON，不要其他解释。\n"
                "严格禁止抄写任何示例值（尤其是日期）。"
                "startDate/endDate必须根据用户查询或当前系统日期{today_date}计算。"
            ),
        }

    @staticmethod
    def _builtin_trip_generation() -> dict:
        return {
            "version": "1.0",
            "description": "运动计划生成Prompt模板",
            "system_prompt": (
                "你是一位专业的运动规划师，擅长根据用户需求生成个性化的餐后运动计划。"
                "你的回答必须是严格的JSON格式，不要包含任何额外文字。"
                "运动计划应包含具体的运动类型、地点、时长和卡路里消耗。"
            ),
            "few_shot_examples": [
                {
                    "input": (
                        "运动区域：北京朝阳公园\n"
                        "运动日期：2026-03-01 至 2026-03-01（共1天）\n"
                        "目标消耗卡路里：300 kcal"
                    ),
                    "output": json.dumps({
                        "title": "朝阳公园餐后健走计划",
                        "destination": "北京朝阳公园",
                        "startDate": "2026-03-01",
                        "endDate": "2026-03-01",
                        "items": [
                            {
                                "dayIndex": 1,
                                "startTime": "19:00",
                                "placeName": "北京朝阳公园",
                                "placeType": "walking",
                                "duration": 40,
                                "cost": 180,
                                "notes": "餐后健走，保持中等速度"
                            },
                            {
                                "dayIndex": 1,
                                "startTime": "19:50",
                                "placeName": "北京朝阳健身步道",
                                "placeType": "running",
                                "duration": 15,
                                "cost": 120,
                                "notes": "慢跑收尾，注意拉伸"
                            }
                        ]
                    }, ensure_ascii=False),
                },
            ],
            "user_prompt_template": (
                "请为以下餐后运动需求生成详细的运动计划，并以JSON格式返回。\n\n"
                "运动区域：{destination}\n"
                "运动日期：{start_date} 至 {end_date}（共{days}天）\n"
                "目标消耗卡路里：{calories_target} kcal\n"
                "{exercise_type_text}\n"
                "{preference_text}\n"
                "{calories_context}\n"
                "{location_context}\n\n"
                "要求：\n"
                "1. 生成具体的运动安排，包括运动类型、地点、时长等\n"
                "2. 合理安排运动强度和时间，确保能达到目标卡路里消耗\n"
                "3. 考虑餐后运动的特点（建议餐后30-60分钟开始）\n"
                "4. placeName必须是具体地点名称，不能用\"附近\"等模糊描述\n"
                "5. placeType: walking/running/cycling/park/gym/indoor/outdoor\n"
                "6. cost字段存储预计消耗卡路里（kcal）\n"
                "7. title必须个性化，不要总是\"餐后运动计划\"\n"
                "8. 多节点时placeName应各不相同\n\n"
                "只返回JSON，不要其他解释。\n\n"
                "返回格式：\n"
                '{{\n'
                '    "title": "个性化标题",\n'
                '    "destination": "{destination}",\n'
                '    "startDate": "{start_date}",\n'
                '    "endDate": "{end_date}",\n'
                '    "items": [\n'
                '        {{\n'
                '            "dayIndex": 1,\n'
                '            "startTime": "HH:mm",\n'
                '            "placeName": "具体地点",\n'
                '            "placeType": "walking",\n'
                '            "duration": 30,\n'
                '            "cost": 150,\n'
                '            "notes": "运动建议"\n'
                '        }}\n'
                '    ]\n'
                '}}'
            ),
        }

    @staticmethod
    def _builtin_menu_recognition() -> dict:
        return {
            "version": "1.0",
            "description": "菜单图片识别Prompt模板",
            "system_prompt": (
                "你是一个菜单识别助手，擅长从菜单图片中提取菜品名称。"
                "你的回答必须是严格的JSON数组格式，不要包含任何额外文字。"
            ),
            "few_shot_examples": [
                {
                    "input": "请识别这张菜单图片中的所有菜品名称。",
                    "output": '["宫保鸡丁", "麻婆豆腐", "鱼香肉丝", "水煮牛肉"]',
                },
                {
                    "input": "请识别这张菜单图片中的所有菜品名称。",
                    "output": '["凯撒沙拉", "意大利面", "牛排", "蘑菇汤"]',
                },
            ],
            "user_prompt_template": (
                "请识别这张菜单图片中的所有菜品名称，并以JSON数组格式返回。\n\n"
                "要求：\n"
                "1. 只返回菜品名称，不要价格、描述等其他信息\n"
                "2. 如果图片不是菜单，返回空数组 []\n"
                "3. 只返回JSON数组，不要其他解释\n\n"
                "返回格式：\n"
                '[\"菜品1\", \"菜品2\", \"菜品3\"]'
            ),
        }

    @staticmethod
    def _builtin_before_meal_features() -> dict:
        return {
            "version": "1.0",
            "description": "餐前图片特征提取Prompt模板",
            "system_prompt": (
                "你是一位食物识别和营养估算专家，擅长从食物图片中识别菜品并估算营养成分。"
                "你的回答必须是严格的JSON格式，不要包含任何额外文字。"
            ),
            "few_shot_examples": [
                {
                    "input": "请分析这张餐前食物图片，识别菜品并估算营养成分。",
                    "output": json.dumps({
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
                    }, ensure_ascii=False),
                },
            ],
            "user_prompt_template": (
                "请分析这张餐前食物图片，识别图片中的所有菜品，并估算每个菜品的份量和营养成分。\n\n"
                "要求：\n"
                "1. 识别图片中所有可见的菜品\n"
                "2. 根据视觉判断估算每个菜品的重量（克）\n"
                "3. 根据菜品类型和重量估算热量、蛋白质、脂肪、碳水化合物\n"
                "4. 计算所有菜品的总营养成分\n"
                "5. 只返回JSON，不要其他解释\n"
                "6. 如果图片不是食物图片，返回空dishes数组\n\n"
                "返回格式：\n"
                '{{\n'
                '    "dishes": [{{"name":"菜品","estimated_weight":200,'
                '"estimated_calories":500.0,"estimated_protein":25.0,'
                '"estimated_fat":35.0,"estimated_carbs":10.0}}],\n'
                '    "total_estimated_calories": 500.0,\n'
                '    "total_estimated_protein": 25.0,\n'
                '    "total_estimated_fat": 35.0,\n'
                '    "total_estimated_carbs": 10.0\n'
                '}}\n\n'
                "请分析图片："
            ),
        }

    @staticmethod
    def _builtin_meal_comparison() -> dict:
        return {
            "version": "1.0",
            "description": "餐前餐后对比Prompt模板",
            "system_prompt": (
                "你是一位食物摄入量评估专家，擅长通过对比餐前餐后图片来估算实际摄入量。"
                "你的回答必须是严格的JSON格式，不要包含任何额外文字。"
            ),
            "few_shot_examples": [
                {
                    "input": (
                        "请对比餐前和餐后图片，分析用户吃掉了多少食物。\n"
                        "餐前识别到的菜品：\n"
                        "- 红烧肉（估算重量：200g，热量：500kcal）\n"
                        "- 清炒时蔬（估算重量：150g，热量：80kcal）"
                    ),
                    "output": json.dumps({
                        "dishes": [
                            {"name": "红烧肉", "remaining_ratio": 0.25, "remaining_weight": 50},
                            {"name": "清炒时蔬", "remaining_ratio": 0.0, "remaining_weight": 0}
                        ],
                        "overall_remaining_ratio": 0.15,
                        "comparison_analysis": "您吃掉了约85%的食物，红烧肉剩余约1/4，蔬菜全部吃完。"
                    }, ensure_ascii=False),
                },
            ],
            "user_prompt_template": (
                "请对比这两张图片（餐前和餐后），分析用户吃掉了多少食物，剩余了多少。\n\n"
                "餐前识别到的菜品信息：\n"
                "{before_dishes_text}\n\n"
                "要求：\n"
                "1. 对比餐前图片（第一张）和餐后图片（第二张）\n"
                "2. 估算每个菜品的剩余比例（0表示吃完，1表示没动）\n"
                "3. 计算整体剩余比例\n"
                "4. 给出简短的对比分析说明\n"
                "5. 只返回JSON，不要其他解释\n\n"
                "返回格式：\n"
                '{{\n'
                '    "dishes": [{{"name":"菜品","remaining_ratio":0.25,"remaining_weight":50}}],\n'
                '    "overall_remaining_ratio": 0.15,\n'
                '    "comparison_analysis": "分析说明"\n'
                '}}\n\n'
                "请分析图片："
            ),
        }

    # ──────────────────────────────────────────────
    # 模板管理API
    # ──────────────────────────────────────────────
    def list_templates(self) -> List[str]:
        """返回所有已注册模板名称"""
        with self._lock:
            return list(self._templates.keys())

    def get_template(self, name: str) -> Optional[dict]:
        """获取模板（返回深拷贝，避免外部修改影响内部状态）"""
        with self._lock:
            tpl = self._templates.get(name)
            return copy.deepcopy(tpl) if tpl else None

    def register_template(self, name: str, template: dict) -> None:
        """
        注册或更新模板

        Args:
            name: 模板名称（非空字符串）
            template: 模板字典，必须包含 system_prompt, few_shot_examples, user_prompt_template, version

        Raises:
            ValueError: 名称为空或模板缺少必需字段
        """
        if not name or not isinstance(name, str):
            raise ValueError("模板名称不能为空")

        required_keys = {"system_prompt", "few_shot_examples", "user_prompt_template", "version"}
        missing = required_keys - set(template.keys())
        if missing:
            raise ValueError(f"模板缺少必需字段: {missing}")

        with self._lock:
            self._templates[name] = copy.deepcopy(template)

    def add_few_shot_example(self, name: str, example: dict) -> None:
        """
        向指定模板追加一个few-shot示例

        Args:
            name: 模板名称
            example: 示例字典，必须包含 input 和 output

        Raises:
            KeyError/ValueError: 模板不存在或示例格式错误
        """
        if "input" not in example or "output" not in example:
            raise ValueError("few-shot示例必须包含 input 和 output 字段")

        with self._lock:
            if name not in self._templates:
                raise KeyError(f"模板不存在: {name}")
            self._templates[name]["few_shot_examples"].append(copy.deepcopy(example))

    def remove_few_shot_example(self, name: str, index: int) -> None:
        """
        删除指定模板的第 index 个few-shot示例

        Raises:
            KeyError: 模板不存在
            IndexError: 索引越界
        """
        with self._lock:
            if name not in self._templates:
                raise KeyError(f"模板不存在: {name}")
            examples = self._templates[name]["few_shot_examples"]
            if index < 0 or index >= len(examples):
                raise IndexError(f"索引越界: {index}，当前示例数: {len(examples)}")
            examples.pop(index)

    # ──────────────────────────────────────────────
    # Prompt渲染
    # ──────────────────────────────────────────────
    def render_prompt(
        self,
        name: str,
        variables: Optional[Dict[str, str]] = None,
        max_examples: Optional[int] = None,
    ) -> dict:
        """
        渲染模板，生成完整的prompt结构

        Args:
            name: 模板名称
            variables: 动态变量字典
            max_examples: 最多使用的few-shot示例数（None表示全部）

        Returns:
            {
                "system_prompt": str,
                "user_prompt": str,
                "few_shot_messages": [{"role": "user"|"assistant", "content": str}, ...]
            }

        Raises:
            KeyError/ValueError: 模板不存在
        """
        tpl = self.get_template(name)
        if tpl is None:
            raise KeyError(f"模板不存在: {name}")

        variables = variables or {}

        # 替换system_prompt中的变量
        system_prompt = self._substitute(tpl["system_prompt"], variables)

        # 替换user_prompt_template中的变量
        user_prompt = self._substitute(tpl["user_prompt_template"], variables)

        # 构建few-shot消息
        examples = tpl.get("few_shot_examples", [])
        if max_examples is not None:
            examples = examples[:max_examples]

        few_shot_messages = []
        for ex in examples:
            few_shot_messages.append({"role": "user", "content": str(ex["input"])})
            few_shot_messages.append({"role": "assistant", "content": str(ex["output"])})

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "few_shot_messages": few_shot_messages,
        }

    def build_messages(
        self,
        name: str,
        variables: Optional[Dict[str, str]] = None,
        max_examples: Optional[int] = None,
    ) -> List[dict]:
        """
        构建完整的消息列表（system + few-shot + user），可直接用于LLM API调用

        Returns:
            [{"role": "system", "content": ...}, {"role": "user", ...}, {"role": "assistant", ...}, ..., {"role": "user", ...}]
        """
        rendered = self.render_prompt(name, variables=variables, max_examples=max_examples)

        messages = [{"role": "system", "content": rendered["system_prompt"]}]
        messages.extend(rendered["few_shot_messages"])
        messages.append({"role": "user", "content": rendered["user_prompt"]})

        return messages

    @staticmethod
    def _substitute(template_str: str, variables: Dict[str, str]) -> str:
        """
        安全的变量替换，缺少的变量保留为空字符串

        使用 str.format_map 配合 defaultdict 实现安全替换，
        避免 KeyError 和大括号转义问题。
        """
        if not variables:
            # 移除所有未替换的单层占位符 {var_name}，但保留 {{...}}
            import re
            # 先将 {{ 和 }} 临时替换，避免误匹配
            temp = template_str.replace("{{", "\x00LBRACE\x00").replace("}}", "\x00RBRACE\x00")
            # 替换剩余的 {var_name} 为空字符串
            temp = re.sub(r'\{(\w+)\}', '', temp)
            # 恢复 {{ 和 }}
            return temp.replace("\x00LBRACE\x00", "{{").replace("\x00RBRACE\x00", "}}")

        import re
        # 先将 {{ 和 }} 临时替换
        temp = template_str.replace("{{", "\x00LBRACE\x00").replace("}}", "\x00RBRACE\x00")

        # 替换已知变量
        def replacer(match):
            key = match.group(1)
            return str(variables.get(key, ""))

        temp = re.sub(r'\{(\w+)\}', replacer, temp)

        # 恢复 {{ 和 }}
        return temp.replace("\x00LBRACE\x00", "{").replace("\x00RBRACE\x00", "}")

    # ──────────────────────────────────────────────
    # 持久化
    # ──────────────────────────────────────────────
    def save_template(self, name: str) -> None:
        """将指定模板保存为JSON文件"""
        tpl = self.get_template(name)
        if tpl is None:
            raise KeyError(f"模板不存在: {name}")

        filepath = os.path.join(self._templates_dir, f"{name}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(tpl, f, ensure_ascii=False, indent=2)
        logger.info(f"模板已保存: {filepath}")

    def save_all_templates(self) -> None:
        """将所有模板保存为JSON文件"""
        with self._lock:
            names = list(self._templates.keys())
        for name in names:
            self.save_template(name)

    def load_templates_from_dir(self) -> None:
        """从目录加载所有JSON模板文件（覆盖同名内置模板）"""
        if not os.path.isdir(self._templates_dir):
            return

        for filename in os.listdir(self._templates_dir):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self._templates_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                name = filename[:-5]  # 去掉 .json 后缀
                # 验证必需字段
                required = {"system_prompt", "few_shot_examples", "user_prompt_template", "version"}
                if required.issubset(set(data.keys())):
                    with self._lock:
                        self._templates[name] = data
                    logger.info(f"从文件加载模板: {name}")
                else:
                    logger.warning(f"模板文件缺少必需字段，跳过: {filepath}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"加载模板文件失败，跳过: {filepath} - {e}")


# ──────────────────────────────────────────────────
# 单例
# ──────────────────────────────────────────────────
_singleton_instance: Optional[PromptTemplateService] = None
_singleton_lock = threading.Lock()


def get_prompt_template_service() -> PromptTemplateService:
    """获取全局单例"""
    global _singleton_instance
    if _singleton_instance is None:
        with _singleton_lock:
            if _singleton_instance is None:
                _singleton_instance = PromptTemplateService()
    return _singleton_instance
