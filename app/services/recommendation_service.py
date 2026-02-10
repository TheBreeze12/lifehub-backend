"""
个性化菜品推荐服务
Phase 41: 基于健康目标匹配 + 热量配额过滤 + 历史偏好排序的个性化菜品推荐

推荐算法流程：
1. 获取用户信息（健康目标、过敏原、身体参数）
2. 计算每日热量目标和当日剩余热量配额
3. 从内置菜品库获取候选菜品
4. 多因子评分：健康目标匹配 + 热量配额适配 + 历史偏好加分 + 过敏原过滤
5. 排序并生成透明推荐理由
"""
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.db_models.user import User
from app.db_models.diet_record import DietRecord
from app.models.food import RecommendedFood, RecommendationData


# 健康目标中文标签
HEALTH_GOAL_LABELS = {
    "reduce_fat": "减脂",
    "gain_muscle": "增肌",
    "control_sugar": "控糖",
    "balanced": "均衡",
}

# 过敏原代码到中文名称映射
ALLERGEN_CODE_TO_CN = {
    "milk": "乳制品",
    "egg": "鸡蛋",
    "fish": "鱼类",
    "shellfish": "甲壳类海鲜",
    "peanut": "花生",
    "tree_nut": "树坚果",
    "wheat": "小麦",
    "soy": "大豆",
}

# 中文过敏原到代码映射
ALLERGEN_CN_TO_CODE = {
    "乳制品": "milk", "牛奶": "milk", "奶": "milk",
    "鸡蛋": "egg", "蛋": "egg", "蛋类": "egg",
    "鱼类": "fish", "鱼": "fish",
    "甲壳类": "shellfish", "虾": "shellfish", "蟹": "shellfish", "海鲜": "shellfish", "贝类": "shellfish",
    "花生": "peanut",
    "树坚果": "tree_nut", "坚果": "tree_nut", "杏仁": "tree_nut", "核桃": "tree_nut", "腰果": "tree_nut",
    "小麦": "wheat", "麸质": "wheat", "面粉": "wheat",
    "大豆": "soy", "豆制品": "soy", "豆腐": "soy", "酱油": "soy",
}

# 内置菜品库（每100g营养数据）
FOOD_DATABASE = [
    # === 高蛋白低脂肪 ===
    {"food_name": "清蒸鲈鱼", "calories": 105, "protein": 19.5, "fat": 3.0, "carbs": 0.5,
     "category": "鱼类", "allergens": ["fish"], "meal_types": ["lunch", "dinner"]},
    {"food_name": "白灼虾", "calories": 90, "protein": 18.0, "fat": 1.5, "carbs": 0.0,
     "category": "海鲜", "allergens": ["shellfish"], "meal_types": ["lunch", "dinner"]},
    {"food_name": "鸡胸肉沙拉", "calories": 120, "protein": 22.0, "fat": 3.0, "carbs": 4.0,
     "category": "沙拉", "allergens": [], "meal_types": ["lunch", "dinner"]},
    {"food_name": "清炒西兰花", "calories": 35, "protein": 3.5, "fat": 0.5, "carbs": 5.0,
     "category": "蔬菜", "allergens": [], "meal_types": ["lunch", "dinner"]},
    {"food_name": "蒸蛋羹", "calories": 65, "protein": 6.5, "fat": 4.0, "carbs": 1.0,
     "category": "蛋类", "allergens": ["egg"], "meal_types": ["breakfast", "lunch", "dinner"]},
    {"food_name": "凉拌黄瓜", "calories": 20, "protein": 0.8, "fat": 0.2, "carbs": 3.5,
     "category": "蔬菜", "allergens": [], "meal_types": ["lunch", "dinner"]},
    {"food_name": "番茄蛋汤", "calories": 35, "protein": 2.5, "fat": 1.5, "carbs": 3.5,
     "category": "汤类", "allergens": ["egg"], "meal_types": ["lunch", "dinner"]},

    # === 均衡营养 ===
    {"food_name": "番茄炒蛋", "calories": 150, "protein": 10.5, "fat": 8.2, "carbs": 6.3,
     "category": "家常菜", "allergens": ["egg"], "meal_types": ["lunch", "dinner"]},
    {"food_name": "青椒肉丝", "calories": 180, "protein": 15.0, "fat": 10.0, "carbs": 5.0,
     "category": "家常菜", "allergens": [], "meal_types": ["lunch", "dinner"]},
    {"food_name": "西红柿牛腩", "calories": 160, "protein": 14.0, "fat": 8.0, "carbs": 6.0,
     "category": "炖菜", "allergens": [], "meal_types": ["lunch", "dinner"]},
    {"food_name": "蒜蓉菠菜", "calories": 40, "protein": 3.0, "fat": 1.0, "carbs": 4.5,
     "category": "蔬菜", "allergens": [], "meal_types": ["lunch", "dinner"]},
    {"food_name": "木须肉", "calories": 170, "protein": 12.0, "fat": 10.0, "carbs": 8.0,
     "category": "家常菜", "allergens": ["egg"], "meal_types": ["lunch", "dinner"]},
    {"food_name": "家常豆腐", "calories": 130, "protein": 9.0, "fat": 7.0, "carbs": 6.0,
     "category": "豆制品", "allergens": ["soy"], "meal_types": ["lunch", "dinner"]},

    # === 高蛋白高热量（增肌） ===
    {"food_name": "红烧牛肉", "calories": 250, "protein": 26.0, "fat": 15.0, "carbs": 3.0,
     "category": "肉类", "allergens": ["soy"], "meal_types": ["lunch", "dinner"]},
    {"food_name": "糖醋排骨", "calories": 280, "protein": 18.0, "fat": 16.0, "carbs": 15.0,
     "category": "肉类", "allergens": [], "meal_types": ["lunch", "dinner"]},
    {"food_name": "宫保鸡丁", "calories": 180, "protein": 18.0, "fat": 10.0, "carbs": 8.0,
     "category": "鸡肉", "allergens": ["peanut", "soy"], "meal_types": ["lunch", "dinner"]},
    {"food_name": "牛肉面", "calories": 350, "protein": 20.0, "fat": 8.0, "carbs": 50.0,
     "category": "面食", "allergens": ["wheat", "soy"], "meal_types": ["lunch", "dinner"]},
    {"food_name": "鸡蛋灌饼", "calories": 260, "protein": 10.0, "fat": 12.0, "carbs": 28.0,
     "category": "面食", "allergens": ["egg", "wheat"], "meal_types": ["breakfast"]},

    # === 低碳水（控糖） ===
    {"food_name": "烤鸡翅", "calories": 200, "protein": 20.0, "fat": 13.0, "carbs": 0.5,
     "category": "鸡肉", "allergens": [], "meal_types": ["lunch", "dinner"]},
    {"food_name": "香煎三文鱼", "calories": 200, "protein": 22.0, "fat": 12.0, "carbs": 0.0,
     "category": "鱼类", "allergens": ["fish"], "meal_types": ["lunch", "dinner"]},
    {"food_name": "蒜香西兰花配鸡胸", "calories": 110, "protein": 18.0, "fat": 3.0, "carbs": 4.0,
     "category": "沙拉", "allergens": [], "meal_types": ["lunch", "dinner"]},

    # === 早餐类 ===
    {"food_name": "小米粥", "calories": 45, "protein": 1.5, "fat": 0.3, "carbs": 9.5,
     "category": "粥类", "allergens": [], "meal_types": ["breakfast"]},
    {"food_name": "燕麦牛奶", "calories": 150, "protein": 6.0, "fat": 5.0, "carbs": 20.0,
     "category": "早餐", "allergens": ["milk", "wheat"], "meal_types": ["breakfast"]},
    {"food_name": "全麦面包配牛油果", "calories": 180, "protein": 5.0, "fat": 10.0, "carbs": 18.0,
     "category": "面食", "allergens": ["wheat"], "meal_types": ["breakfast"]},
    {"food_name": "水煮蛋", "calories": 75, "protein": 6.5, "fat": 5.0, "carbs": 0.5,
     "category": "蛋类", "allergens": ["egg"], "meal_types": ["breakfast", "snack"]},
    {"food_name": "豆浆", "calories": 35, "protein": 3.0, "fat": 1.5, "carbs": 2.5,
     "category": "豆制品", "allergens": ["soy"], "meal_types": ["breakfast"]},

    # === 加餐类 ===
    {"food_name": "酸奶", "calories": 70, "protein": 3.5, "fat": 3.0, "carbs": 7.0,
     "category": "乳制品", "allergens": ["milk"], "meal_types": ["snack", "breakfast"]},
    {"food_name": "苹果", "calories": 52, "protein": 0.3, "fat": 0.2, "carbs": 13.0,
     "category": "水果", "allergens": [], "meal_types": ["snack"]},
    {"food_name": "香蕉", "calories": 90, "protein": 1.2, "fat": 0.3, "carbs": 22.0,
     "category": "水果", "allergens": [], "meal_types": ["snack", "breakfast"]},
    {"food_name": "坚果拼盘", "calories": 580, "protein": 18.0, "fat": 50.0, "carbs": 15.0,
     "category": "坚果", "allergens": ["tree_nut", "peanut"], "meal_types": ["snack"]},
    {"food_name": "圣女果", "calories": 25, "protein": 1.0, "fat": 0.2, "carbs": 5.0,
     "category": "水果", "allergens": [], "meal_types": ["snack"]},
]


class RecommendationService:
    """个性化菜品推荐服务"""

    def _normalize_allergens(self, user_allergens: list) -> set:
        """
        将用户过敏原列表规范化为过敏原代码集合
        支持中文和英文输入
        """
        codes = set()
        if not user_allergens:
            return codes
        for allergen in user_allergens:
            allergen = allergen.strip()
            # 如果已经是标准代码
            if allergen.lower() in ALLERGEN_CODE_TO_CN:
                codes.add(allergen.lower())
            # 中文映射
            elif allergen in ALLERGEN_CN_TO_CODE:
                codes.add(ALLERGEN_CN_TO_CODE[allergen])
            else:
                # 尝试模糊匹配
                for cn, code in ALLERGEN_CN_TO_CODE.items():
                    if cn in allergen or allergen in cn:
                        codes.add(code)
                        break
        return codes

    def _calculate_daily_calorie_target(self, user: User) -> float:
        """
        根据用户身体参数和健康目标计算每日热量目标
        使用 Mifflin-St Jeor 公式估算 BMR
        """
        weight = user.weight or 65.0
        height = user.height or 170.0
        age = user.age or 30
        gender = user.gender or "male"

        # BMR (Mifflin-St Jeor)
        if gender == "male":
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        # TDEE（轻度活动系数 1.375）
        tdee = bmr * 1.375

        # 根据健康目标调整
        goal = user.health_goal or "balanced"
        if goal == "reduce_fat":
            return tdee - 500  # 减脂：TDEE - 500
        elif goal == "gain_muscle":
            return tdee + 300  # 增肌：TDEE + 300
        elif goal == "control_sugar":
            return tdee  # 控糖：保持 TDEE
        else:
            return tdee  # 均衡：保持 TDEE

    def _get_today_intake(self, db: Session, user_id: int) -> float:
        """获取用户今日已摄入热量总和"""
        today = date.today()
        result = db.query(func.sum(DietRecord.calories)).filter(
            and_(
                DietRecord.user_id == user_id,
                DietRecord.record_date == today
            )
        ).scalar()
        return float(result) if result else 0.0

    def _get_history_food_counts(self, db: Session, user_id: int, days: int = 30) -> dict:
        """
        获取用户历史饮食偏好（最近N天的菜品出现次数）
        返回 {food_name: count} 字典
        """
        since = date.today() - __import__('datetime').timedelta(days=days)
        records = db.query(
            DietRecord.food_name,
            func.count(DietRecord.id).label("cnt")
        ).filter(
            and_(
                DietRecord.user_id == user_id,
                DietRecord.record_date >= since
            )
        ).group_by(DietRecord.food_name).all()

        return {r.food_name: r.cnt for r in records}

    def _get_today_eaten_foods(self, db: Session, user_id: int) -> set:
        """获取今天已经吃过的菜品名称集合，用于去重"""
        today = date.today()
        records = db.query(DietRecord.food_name).filter(
            and_(
                DietRecord.user_id == user_id,
                DietRecord.record_date == today
            )
        ).all()
        return {r.food_name for r in records}

    def _generate_tags(self, food: dict) -> list:
        """根据菜品营养数据生成标签"""
        tags = []
        cal = food["calories"]
        prot = food["protein"]
        fat = food["fat"]
        carbs = food["carbs"]

        # 热量标签
        if cal <= 100:
            tags.append("低热量")
        elif cal >= 300:
            tags.append("高热量")

        # 蛋白质标签（每100g高于15g算高蛋白）
        if prot >= 15:
            tags.append("高蛋白")

        # 脂肪标签
        if fat <= 3:
            tags.append("低脂肪")
        elif fat >= 20:
            tags.append("高脂肪")

        # 碳水标签
        if carbs <= 5:
            tags.append("低碳水")
        elif carbs >= 30:
            tags.append("高碳水")

        return tags

    def _score_health_goal(self, food: dict, health_goal: str) -> float:
        """
        健康目标匹配评分（0-40分）
        根据用户健康目标对菜品营养成分进行评分
        """
        cal = food["calories"]
        prot = food["protein"]
        fat = food["fat"]
        carbs = food["carbs"]

        if health_goal == "reduce_fat":
            # 减脂：低热量 + 高蛋白 + 低脂肪
            score = 0.0
            # 热量越低越好（0-200kcal映射到0-15分）
            score += max(0, 15 - cal / 200 * 15)
            # 蛋白质越高越好（0-25g映射到0-15分）
            score += min(15, prot / 25 * 15)
            # 脂肪越低越好（0-20g映射到0-10分）
            score += max(0, 10 - fat / 20 * 10)
            return min(40, score)

        elif health_goal == "gain_muscle":
            # 增肌：高蛋白 + 足够热量
            score = 0.0
            # 蛋白质越高越好（0-30g映射到0-20分）
            score += min(20, prot / 30 * 20)
            # 热量适中偏高（150-350kcal最佳）
            if 150 <= cal <= 350:
                score += 15
            elif cal < 150:
                score += cal / 150 * 10
            else:
                score += max(0, 15 - (cal - 350) / 200 * 10)
            # 脂肪适中
            if fat <= 15:
                score += 5
            return min(40, score)

        elif health_goal == "control_sugar":
            # 控糖：低碳水 + 高蛋白
            score = 0.0
            # 碳水越低越好（0-30g映射到0-20分）
            score += max(0, 20 - carbs / 30 * 20)
            # 蛋白质越高越好（0-25g映射到0-15分）
            score += min(15, prot / 25 * 15)
            # 热量适中
            if cal <= 250:
                score += 5
            return min(40, score)

        else:  # balanced
            # 均衡：三大营养素比例均衡
            score = 0.0
            total_macro = prot + fat + carbs
            if total_macro > 0:
                prot_ratio = prot / total_macro
                fat_ratio = fat / total_macro
                carbs_ratio = carbs / total_macro
                # 理想比例：蛋白质20-30%, 脂肪20-30%, 碳水40-60%
                if 0.15 <= prot_ratio <= 0.35:
                    score += 12
                if 0.15 <= fat_ratio <= 0.35:
                    score += 12
                if 0.30 <= carbs_ratio <= 0.65:
                    score += 12
            # 热量适中
            if 100 <= cal <= 300:
                score += 4
            return min(40, score)

    def _score_calorie_fit(self, food: dict, remaining_calories: float) -> float:
        """
        热量配额适配评分（0-30分）
        菜品热量在剩余配额范围内得高分
        """
        cal = food["calories"]

        if remaining_calories <= 0:
            # 已超配额，只推荐极低热量
            if cal <= 50:
                return 15.0
            return max(0, 10 - cal / 100 * 10)

        # 理想热量 = 剩余配额的20-50%（单道菜占比）
        ideal_min = remaining_calories * 0.1
        ideal_max = remaining_calories * 0.5

        if ideal_min <= cal <= ideal_max:
            return 30.0
        elif cal < ideal_min:
            # 热量太低也扣分（但不多扣）
            return max(15, 30 - (ideal_min - cal) / ideal_min * 15)
        else:
            # 超出理想范围
            over_ratio = (cal - ideal_max) / ideal_max
            return max(0, 30 - over_ratio * 40)

    def _score_preference(self, food: dict, history_counts: dict) -> float:
        """
        历史偏好评分（0-15分）
        基于用户历史饮食记录，偏好的食物类别和具体菜品加分
        """
        food_name = food["food_name"]
        category = food.get("category", "")

        score = 0.0

        # 如果用户曾经吃过这道菜，加分
        if food_name in history_counts:
            count = history_counts[food_name]
            score += min(10, count * 2.5)  # 最多10分

        # 同类别的菜品也适当加分
        for name, count in history_counts.items():
            # 简单的类别匹配（通过名称中的关键词）
            if category and count > 0:
                for keyword in ["鱼", "虾", "鸡", "牛", "豆", "蛋", "菜", "粥"]:
                    if keyword in name and keyword in food_name:
                        score += min(3, count * 0.5)
                        break

        return min(15, score)

    def _score_variety(self, food: dict, today_eaten: set) -> float:
        """
        多样性评分（0-15分）
        今天没吃过的菜品得高分，鼓励饮食多样化
        """
        if food["food_name"] in today_eaten:
            return 0.0  # 今天已经吃过了
        return 15.0

    def _generate_reason(self, food: dict, health_goal: str, remaining_calories: float,
                         tags: list, is_preferred: bool) -> str:
        """生成透明的推荐理由"""
        goal_label = HEALTH_GOAL_LABELS.get(health_goal, "均衡")
        reasons = []

        cal = food["calories"]
        prot = food["protein"]
        fat = food["fat"]
        carbs = food["carbs"]

        # 健康目标相关理由
        if health_goal == "reduce_fat":
            if "低热量" in tags or cal <= 120:
                reasons.append(f"热量仅{cal:.0f}千卡，适合减脂")
            if "高蛋白" in tags:
                reasons.append(f"蛋白质{prot:.1f}g，有助于维持肌肉")
            if "低脂肪" in tags:
                reasons.append("低脂肪，减少脂肪摄入")
        elif health_goal == "gain_muscle":
            if "高蛋白" in tags:
                reasons.append(f"蛋白质{prot:.1f}g，促进肌肉合成")
            if cal >= 150:
                reasons.append(f"热量{cal:.0f}千卡，提供充足能量")
        elif health_goal == "control_sugar":
            if "低碳水" in tags or carbs <= 10:
                reasons.append(f"碳水仅{carbs:.1f}g，有助于控糖")
            if "高蛋白" in tags:
                reasons.append(f"高蛋白{prot:.1f}g，延缓血糖上升")
        else:
            if len(tags) > 0:
                reasons.append("营养成分均衡")

        # 热量配额理由
        if remaining_calories > 0 and cal <= remaining_calories * 0.5:
            reasons.append(f"在您的剩余热量配额（{remaining_calories:.0f}kcal）内")

        # 偏好理由
        if is_preferred:
            reasons.append("符合您的饮食偏好")

        if not reasons:
            reasons.append(f"适合{goal_label}饮食目标")

        return "；".join(reasons) + "。"

    def get_recommendations(
        self,
        db: Session,
        user_id: int,
        meal_type: str = "lunch",
        limit: int = 5
    ) -> RecommendationData:
        """
        获取个性化菜品推荐

        Args:
            db: 数据库会话
            user_id: 用户ID
            meal_type: 餐次（breakfast/lunch/dinner/snack）
            limit: 返回推荐数量

        Returns:
            RecommendationData: 推荐结果

        Raises:
            ValueError: 用户不存在时抛出
        """
        # 1. 获取用户信息
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"用户不存在，user_id: {user_id}")

        health_goal = user.health_goal or "balanced"
        goal_label = HEALTH_GOAL_LABELS.get(health_goal, "均衡")
        user_allergens = self._normalize_allergens(user.allergens or [])

        # 2. 计算热量目标和剩余配额
        daily_target = self._calculate_daily_calorie_target(user)
        today_intake = self._get_today_intake(db, user_id)
        remaining_calories = max(0, daily_target - today_intake)

        # 3. 获取历史偏好和今日已食
        history_counts = self._get_history_food_counts(db, user_id, days=30)
        today_eaten = self._get_today_eaten_foods(db, user_id)

        # 4. 餐次中文映射
        meal_type_map = {
            "早餐": "breakfast", "午餐": "lunch",
            "晚餐": "dinner", "加餐": "snack",
        }
        meal_type_en = meal_type_map.get(meal_type, meal_type)

        # 5. 筛选和评分
        scored_foods = []
        for food in FOOD_DATABASE:
            # 过滤餐次不匹配
            if meal_type_en not in food.get("meal_types", []):
                continue

            # 过敏原过滤
            food_allergens = set(food.get("allergens", []))
            if food_allergens & user_allergens:
                continue

            # 多因子评分
            goal_score = self._score_health_goal(food, health_goal)
            cal_score = self._score_calorie_fit(food, remaining_calories)
            pref_score = self._score_preference(food, history_counts)
            variety_score = self._score_variety(food, today_eaten)

            total_score = goal_score + cal_score + pref_score + variety_score
            total_score = round(min(100, max(0, total_score)), 1)

            # 生成标签
            tags = self._generate_tags(food)

            # 生成理由
            is_preferred = food["food_name"] in history_counts
            reason = self._generate_reason(
                food, health_goal, remaining_calories, tags, is_preferred
            )

            scored_foods.append({
                "food": food,
                "score": total_score,
                "tags": tags,
                "reason": reason,
            })

        # 6. 按分数排序，取top N
        scored_foods.sort(key=lambda x: x["score"], reverse=True)
        top_foods = scored_foods[:limit]

        # 7. 构建响应
        recommendations = []
        for item in top_foods:
            f = item["food"]
            recommendations.append(RecommendedFood(
                food_name=f["food_name"],
                calories=float(f["calories"]),
                protein=float(f["protein"]),
                fat=float(f["fat"]),
                carbs=float(f["carbs"]),
                score=item["score"],
                reason=item["reason"],
                tags=item["tags"],
            ))

        return RecommendationData(
            user_id=user_id,
            meal_type=meal_type_en,
            remaining_calories=round(remaining_calories, 2),
            daily_calorie_target=round(daily_target, 2),
            health_goal=health_goal,
            health_goal_label=goal_label,
            recommendations=recommendations,
        )


# 模块级单例
_instance: Optional[RecommendationService] = None


def get_recommendation_service() -> RecommendationService:
    """获取推荐服务单例"""
    global _instance
    if _instance is None:
        _instance = RecommendationService()
    return _instance
