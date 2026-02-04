"""
过敏原检测服务
实现八大类过敏原的基础检测（基于关键词匹配）

八大类过敏原（参考中国《预包装食品标签通则》和国际标准）：
1. 乳制品（牛奶）
2. 鸡蛋
3. 鱼类
4. 甲壳类（虾、蟹等）
5. 花生
6. 树坚果（杏仁、核桃、腰果等）
7. 小麦（麸质）
8. 大豆
"""
from typing import List, Dict, Optional, Set
from dataclasses import dataclass


@dataclass
class AllergenCategory:
    """过敏原类别"""
    code: str  # 唯一标识码
    name: str  # 中文名称
    name_en: str  # 英文名称
    keywords: Set[str]  # 匹配关键词集合
    description: str  # 描述


# 八大类过敏原定义
ALLERGEN_CATEGORIES: Dict[str, AllergenCategory] = {
    "milk": AllergenCategory(
        code="milk",
        name="乳制品",
        name_en="Milk",
        keywords={
            # 直接乳制品
            "牛奶", "鲜奶", "纯奶", "全脂奶", "脱脂奶", "低脂奶",
            "奶粉", "奶油", "黄油", "芝士", "奶酪", "起司", "干酪",
            "炼乳", "淡奶", "奶皮", "奶昔", "酸奶", "酸乳", "乳酪",
            "奶酥", "奶糖", "奶茶", "牛乳", "羊奶", "马奶",
            # 成分
            "乳清", "乳糖", "酪蛋白", "乳脂", "乳粉", "乳制品",
            # 含奶菜品关键词
            "奶香", "奶味", "芝士焗", "奶油焗", "白汁", "忌廉"
        },
        description="包括牛奶及其制品，如奶酪、黄油、酸奶、奶油等"
    ),
    "egg": AllergenCategory(
        code="egg",
        name="鸡蛋",
        name_en="Egg",
        keywords={
            # 直接蛋类
            "鸡蛋", "蛋", "蛋黄", "蛋白", "蛋清", "鸡子", "鸭蛋", "鹅蛋",
            "鹌鹑蛋", "皮蛋", "松花蛋", "咸蛋", "卤蛋", "茶叶蛋",
            "蛋花", "蛋液", "蛋粉", "全蛋", "溏心蛋", "荷包蛋",
            # 含蛋菜品
            "蛋炒", "炒蛋", "煎蛋", "蒸蛋", "蛋羹", "蛋饼",
            "蛋糕", "蛋挞", "蛋卷", "蛋包", "蛋皮",
            # 成分
            "卵磷脂", "蛋黄酱", "美乃滋", "沙拉酱"
        },
        description="包括鸡蛋、鸭蛋、鹅蛋等各种蛋类及其制品"
    ),
    "fish": AllergenCategory(
        code="fish",
        name="鱼类",
        name_en="Fish",
        keywords={
            # 常见鱼类
            "鱼", "鲈鱼", "鲫鱼", "鲤鱼", "草鱼", "鳙鱼", "鳊鱼",
            "鳜鱼", "桂鱼", "石斑鱼", "多宝鱼", "比目鱼", "鳕鱼",
            "三文鱼", "鲑鱼", "金枪鱼", "吞拿鱼", "鲷鱼", "带鱼",
            "黄花鱼", "鲳鱼", "鲅鱼", "秋刀鱼", "沙丁鱼", "鳗鱼",
            "鲶鱼", "黑鱼", "鲢鱼", "罗非鱼", "鲻鱼", "梭鱼",
            # 鱼制品
            "鱼片", "鱼丸", "鱼糕", "鱼籽", "鱼子酱", "鱼露",
            "鱼干", "鱼皮", "鱼肉", "鱼头", "鱼尾", "鱼腩",
            "鱼柳", "鱼排", "鱼翅"
        },
        description="包括各种鱼类及鱼制品"
    ),
    "shellfish": AllergenCategory(
        code="shellfish",
        name="甲壳类",
        name_en="Shellfish",
        keywords={
            # 虾类
            "虾", "大虾", "明虾", "基围虾", "龙虾", "小龙虾", "虾仁",
            "虾米", "虾皮", "虾干", "虾酱", "虾膏", "虾球", "虾饺",
            # 蟹类
            "蟹", "螃蟹", "大闸蟹", "梭子蟹", "青蟹", "蟹黄", "蟹肉",
            "蟹膏", "蟹粉", "蟹柳",
            # 其他甲壳类
            "龙虾", "濑尿虾", "皮皮虾", "寄居蟹",
            # 贝类（部分标准也将贝类归入此类）
            "贝", "扇贝", "蛤蜊", "蛤", "蚬", "蚌", "牡蛎", "生蚝",
            "鲍鱼", "海螺", "蛏子", "花甲", "蚝", "青口", "淡菜",
            # 其他海鲜
            "海鲜", "海味"
        },
        description="包括虾、蟹、贝类等甲壳类海鲜"
    ),
    "peanut": AllergenCategory(
        code="peanut",
        name="花生",
        name_en="Peanut",
        keywords={
            "花生", "花生米", "花生仁", "花生酱", "花生油", "花生碎",
            "花生粉", "花生糖", "花生酥", "落花生", "长生果",
            # 含花生菜品
            "宫保", "怪味", "五香花生", "油炸花生", "酒鬼花生"
        },
        description="包括花生及花生制品"
    ),
    "tree_nut": AllergenCategory(
        code="tree_nut",
        name="树坚果",
        name_en="Tree Nuts",
        keywords={
            # 各种坚果
            "杏仁", "核桃", "腰果", "榛子", "开心果", "夏威夷果",
            "澳洲坚果", "松子", "栗子", "板栗", "碧根果", "山核桃",
            "巴旦木", "巴达木", "扁桃仁", "白果", "银杏",
            # 坚果制品
            "坚果", "果仁", "杏仁露", "核桃露", "坚果酱",
            "杏仁粉", "核桃粉", "椰子", "椰浆", "椰奶", "椰蓉"
        },
        description="包括杏仁、核桃、腰果、榛子等树坚果及其制品"
    ),
    "wheat": AllergenCategory(
        code="wheat",
        name="小麦",
        name_en="Wheat",
        keywords={
            # 小麦及制品
            "小麦", "麦", "面粉", "面", "馒头", "包子", "饺子", "馄饨",
            "面条", "面包", "蛋糕", "饼干", "曲奇", "披萨", "意面",
            "通心粉", "挂面", "拉面", "刀削面", "炸酱面", "担担面",
            "烧麦", "春卷", "煎饼", "葱油饼", "手抓饼", "油条",
            # 麸质相关
            "麸质", "面筋", "烤麸", "麦芽", "麦片", "燕麦",
            "大麦", "黑麦", "裸麦",
            # 酱料
            "酱油", "生抽", "老抽", "豉油", "蚝油"
        },
        description="包括小麦及其制品，含麸质食品"
    ),
    "soy": AllergenCategory(
        code="soy",
        name="大豆",
        name_en="Soy",
        keywords={
            # 大豆及制品
            "大豆", "黄豆", "豆腐", "豆干", "豆皮", "腐竹", "豆浆",
            "豆奶", "豆花", "豆脑", "豆芽", "毛豆", "青豆", "黑豆",
            "纳豆", "味噌", "豆瓣酱", "豆豉", "腐乳",
            # 豆制品
            "豆腐乳", "臭豆腐", "千张", "百叶", "素鸡", "素肉",
            "豆腐干", "香干", "豆腐丝", "豆腐泡", "油豆腐",
            # 大豆油和卵磷脂
            "大豆油", "豆油", "大豆卵磷脂"
        },
        description="包括大豆及其制品，如豆腐、豆浆、酱油等"
    )
}


class AllergenService:
    """过敏原检测服务类"""
    
    def __init__(self):
        """初始化过敏原检测服务"""
        self.categories = ALLERGEN_CATEGORIES
        
    def get_all_categories(self) -> List[Dict]:
        """
        获取所有过敏原类别信息
        
        Returns:
            过敏原类别列表
        """
        return [
            {
                "code": cat.code,
                "name": cat.name,
                "name_en": cat.name_en,
                "description": cat.description
            }
            for cat in self.categories.values()
        ]
    
    def check_allergens(
        self,
        food_name: str,
        ingredients: Optional[List[str]] = None,
        user_allergens: Optional[List[str]] = None
    ) -> Dict:
        """
        检测食物中的过敏原
        
        Args:
            food_name: 菜品名称
            ingredients: 配料列表（可选，如果提供会更精确）
            user_allergens: 用户的过敏原列表（用于匹配告警）
            
        Returns:
            包含检测结果的字典
        """
        detected_allergens = []
        warnings = []
        
        # 合并检测文本
        texts_to_check = [food_name]
        if ingredients:
            texts_to_check.extend(ingredients)
        
        combined_text = " ".join(texts_to_check)
        
        # 遍历每个过敏原类别进行检测
        for code, category in self.categories.items():
            matched_keywords = self._find_matching_keywords(combined_text, category.keywords)
            
            if matched_keywords:
                allergen_info = {
                    "code": category.code,
                    "name": category.name,
                    "name_en": category.name_en,
                    "matched_keywords": list(matched_keywords),
                    "confidence": "high" if len(matched_keywords) > 1 else "medium"
                }
                detected_allergens.append(allergen_info)
                
                # 检查是否匹配用户的过敏原
                if user_allergens:
                    user_allergen_lower = [a.lower() for a in user_allergens]
                    if (category.name in user_allergens or 
                        category.name_en.lower() in user_allergen_lower or
                        category.code in user_allergen_lower or
                        any(kw in user_allergens for kw in matched_keywords)):
                        warnings.append({
                            "allergen": category.name,
                            "level": "high",
                            "message": f"警告：检测到您的过敏原【{category.name}】，匹配关键词：{', '.join(matched_keywords)}"
                        })
        
        # 构建返回结果
        result = {
            "food_name": food_name,
            "detected_allergens": detected_allergens,
            "allergen_count": len(detected_allergens),
            "has_allergens": len(detected_allergens) > 0,
            "warnings": warnings,
            "has_warnings": len(warnings) > 0
        }
        
        # 如果提供了配料，也返回
        if ingredients:
            result["ingredients"] = ingredients
            
        return result
    
    def _find_matching_keywords(self, text: str, keywords: Set[str]) -> Set[str]:
        """
        在文本中查找匹配的关键词
        
        Args:
            text: 待检测文本
            keywords: 关键词集合
            
        Returns:
            匹配到的关键词集合
        """
        matched = set()
        for keyword in keywords:
            if keyword in text:
                matched.add(keyword)
        return matched
    
    def check_single_allergen(self, food_name: str, allergen_code: str) -> bool:
        """
        检测食物是否包含特定过敏原
        
        Args:
            food_name: 菜品名称
            allergen_code: 过敏原代码
            
        Returns:
            是否包含该过敏原
        """
        if allergen_code not in self.categories:
            return False
            
        category = self.categories[allergen_code]
        matched = self._find_matching_keywords(food_name, category.keywords)
        return len(matched) > 0
    
    def get_allergen_summary(self, detected_allergens: List[Dict]) -> str:
        """
        生成过敏原检测摘要文本
        
        Args:
            detected_allergens: 检测到的过敏原列表
            
        Returns:
            摘要文本
        """
        if not detected_allergens:
            return "未检测到常见过敏原"
        
        allergen_names = [a["name"] for a in detected_allergens]
        return f"检测到以下过敏原：{', '.join(allergen_names)}"
    
    def merge_with_ai_inference(
        self,
        food_name: str,
        keyword_result: Dict,
        ai_allergens: List[str],
        ai_reasoning: str,
        user_allergens: Optional[List[str]] = None
    ) -> Dict:
        """
        Phase 7: 合并关键词检测与AI推理结果
        
        将基于关键词匹配的检测结果与AI推理的过敏原结果进行合并，
        去重并标注来源，提供更全面的过敏原检测结果。
        
        Args:
            food_name: 菜品名称
            keyword_result: 关键词检测结果（来自check_allergens方法）
            ai_allergens: AI推理的过敏原代码列表
            ai_reasoning: AI过敏原推理说明
            user_allergens: 用户的过敏原列表（用于匹配告警）
            
        Returns:
            合并后的检测结果字典
        """
        # 从关键词检测结果中获取已检测的过敏原代码
        keyword_allergen_codes = set()
        for allergen in keyword_result.get("detected_allergens", []):
            keyword_allergen_codes.add(allergen.get("code"))
        
        # AI推理的过敏原代码集合
        ai_allergen_codes = set(ai_allergens) if ai_allergens else set()
        
        # 合并后的过敏原列表
        merged_allergens = []
        all_codes = keyword_allergen_codes | ai_allergen_codes
        
        for code in all_codes:
            if code not in self.categories:
                continue
                
            category = self.categories[code]
            
            # 判断来源
            from_keyword = code in keyword_allergen_codes
            from_ai = code in ai_allergen_codes
            
            # 获取关键词匹配信息（如果有）
            matched_keywords = []
            if from_keyword:
                for allergen in keyword_result.get("detected_allergens", []):
                    if allergen.get("code") == code:
                        matched_keywords = allergen.get("matched_keywords", [])
                        break
            
            # 确定来源标签
            if from_keyword and from_ai:
                source = "keyword+ai"
                confidence = "high"
            elif from_keyword:
                source = "keyword"
                confidence = "high" if len(matched_keywords) > 1 else "medium"
            else:  # from_ai
                source = "ai"
                confidence = "medium"  # AI推理置信度设为中等
            
            allergen_info = {
                "code": category.code,
                "name": category.name,
                "name_en": category.name_en,
                "matched_keywords": matched_keywords,
                "confidence": confidence,
                "source": source  # Phase 7新增：来源标识
            }
            merged_allergens.append(allergen_info)
        
        # 重新生成警告信息
        warnings = []
        if user_allergens:
            user_allergen_lower = [a.lower() for a in user_allergens]
            for allergen in merged_allergens:
                if (allergen["name"] in user_allergens or 
                    allergen["name_en"].lower() in user_allergen_lower or
                    allergen["code"] in user_allergen_lower or
                    any(kw in user_allergens for kw in allergen.get("matched_keywords", []))):
                    
                    source_text = {
                        "keyword": "关键词匹配",
                        "ai": "AI推理",
                        "keyword+ai": "关键词匹配和AI推理"
                    }.get(allergen.get("source", ""), "检测")
                    
                    warnings.append({
                        "allergen": allergen["name"],
                        "level": "high",
                        "message": f"警告：通过{source_text}检测到您的过敏原【{allergen['name']}】"
                    })
        
        # 构建合并后的结果
        result = {
            "food_name": food_name,
            "detected_allergens": merged_allergens,
            "allergen_count": len(merged_allergens),
            "has_allergens": len(merged_allergens) > 0,
            "warnings": warnings,
            "has_warnings": len(warnings) > 0,
            # Phase 7新增字段
            "ai_reasoning": ai_reasoning,
            "detection_methods": {
                "keyword_count": len(keyword_allergen_codes),
                "ai_count": len(ai_allergen_codes),
                "merged_count": len(merged_allergens)
            }
        }
        
        return result


# 创建全局服务实例
allergen_service = AllergenService()
