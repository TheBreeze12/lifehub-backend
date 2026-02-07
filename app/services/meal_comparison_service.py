"""
餐前餐后对比服务
Phase 12: 处理餐后图片上传与对比计算逻辑
"""
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db_models.meal_comparison import MealComparison


class MealComparisonService:
    """
    餐前餐后对比服务类
    负责处理餐后图片上传后的对比计算逻辑
    """
    
    def __init__(self, ai_service=None):
        """
        初始化服务
        
        Args:
            ai_service: AI服务实例（用于调用对比分析）
        """
        self.ai_service = ai_service
    
    def calculate_net_intake(
        self,
        original_calories: float,
        original_protein: float,
        original_fat: float,
        original_carbs: float,
        consumption_ratio: float
    ) -> Dict[str, float]:
        """
        计算净摄入营养成分
        
        净摄入 = 原始值 × 消耗比例
        消耗比例 = 1 - 剩余比例
        
        Args:
            original_calories: 原始热量（kcal）
            original_protein: 原始蛋白质（g）
            original_fat: 原始脂肪（g）
            original_carbs: 原始碳水化合物（g）
            consumption_ratio: 消耗比例（0-1，1表示全部吃完）
            
        Returns:
            包含净摄入值的字典
        """
        return {
            "net_calories": round(original_calories * consumption_ratio, 2),
            "net_protein": round(original_protein * consumption_ratio, 2),
            "net_fat": round(original_fat * consumption_ratio, 2),
            "net_carbs": round(original_carbs * consumption_ratio, 2)
        }
    
    def update_comparison_with_after_meal(
        self,
        db: Session,
        comparison: MealComparison,
        after_image_url: str,
        after_features: Dict[str, Any],
        consumption_ratio: float,
        comparison_analysis: str
    ) -> MealComparison:
        """
        更新MealComparison记录（添加餐后数据和计算结果）
        
        Args:
            db: 数据库会话
            comparison: MealComparison记录
            after_image_url: 餐后图片URL
            after_features: 餐后图片特征
            consumption_ratio: 消耗比例
            comparison_analysis: AI对比分析说明
            
        Returns:
            更新后的MealComparison记录
        """
        # 计算净摄入
        net_values = self.calculate_net_intake(
            original_calories=comparison.original_calories or 0,
            original_protein=comparison.original_protein or 0,
            original_fat=comparison.original_fat or 0,
            original_carbs=comparison.original_carbs or 0,
            consumption_ratio=consumption_ratio
        )
        
        # 更新记录
        comparison.after_image_url = after_image_url
        comparison.after_features = json.dumps(after_features, ensure_ascii=False)
        comparison.consumption_ratio = consumption_ratio
        comparison.net_calories = net_values["net_calories"]
        comparison.net_protein = net_values["net_protein"]
        comparison.net_fat = net_values["net_fat"]
        comparison.net_carbs = net_values["net_carbs"]
        comparison.comparison_analysis = comparison_analysis
        comparison.status = "completed"
        
        db.commit()
        db.refresh(comparison)
        
        return comparison
    
    def adjust_consumption_ratio(
        self,
        db: Session,
        comparison: MealComparison,
        new_ratio: float
    ) -> MealComparison:
        """
        手动调整消耗比例并重新计算净摄入
        
        Args:
            db: 数据库会话
            comparison: MealComparison记录
            new_ratio: 新的消耗比例（0-1）
            
        Returns:
            更新后的MealComparison记录
        """
        if new_ratio < 0 or new_ratio > 1:
            raise ValueError("消耗比例必须在0-1之间")
        
        # 重新计算净摄入
        net_values = self.calculate_net_intake(
            original_calories=comparison.original_calories or 0,
            original_protein=comparison.original_protein or 0,
            original_fat=comparison.original_fat or 0,
            original_carbs=comparison.original_carbs or 0,
            consumption_ratio=new_ratio
        )
        
        # 更新记录
        comparison.consumption_ratio = new_ratio
        comparison.net_calories = net_values["net_calories"]
        comparison.net_protein = net_values["net_protein"]
        comparison.net_fat = net_values["net_fat"]
        comparison.net_carbs = net_values["net_carbs"]
        
        db.commit()
        db.refresh(comparison)
        
        return comparison
    
    def format_comparison_result(self, comparison: MealComparison) -> Dict[str, Any]:
        """
        格式化对比结果用于API响应
        
        Args:
            comparison: MealComparison记录
            
        Returns:
            格式化后的字典
        """
        # 解析JSON字段
        before_features = None
        after_features = None
        
        if comparison.before_features:
            try:
                before_features = json.loads(comparison.before_features)
            except json.JSONDecodeError:
                before_features = {}
        
        if comparison.after_features:
            try:
                after_features = json.loads(comparison.after_features)
            except json.JSONDecodeError:
                after_features = {}
        
        return {
            "comparison_id": comparison.id,
            "user_id": comparison.user_id,
            "before_image_url": comparison.before_image_url,
            "after_image_url": comparison.after_image_url,
            "before_features": before_features,
            "after_features": after_features,
            "consumption_ratio": comparison.consumption_ratio,
            "original_calories": comparison.original_calories,
            "original_protein": comparison.original_protein,
            "original_fat": comparison.original_fat,
            "original_carbs": comparison.original_carbs,
            "net_calories": comparison.net_calories,
            "net_protein": comparison.net_protein,
            "net_fat": comparison.net_fat,
            "net_carbs": comparison.net_carbs,
            "comparison_analysis": comparison.comparison_analysis,
            "status": comparison.status,
            "created_at": comparison.created_at.strftime("%Y-%m-%dT%H:%M:%S") if comparison.created_at else None,
            "updated_at": comparison.updated_at.strftime("%Y-%m-%dT%H:%M:%S") if comparison.updated_at else None
        }


# 创建单例实例
meal_comparison_service = MealComparisonService()
