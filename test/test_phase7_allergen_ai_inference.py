"""
Phase 7 测试文件：过敏原AI推理（Prompt增强）

测试内容：
1. 测试AI营养分析Prompt是否包含过敏原推理要求
2. 测试_parse_nutrition_response是否正确解析过敏原字段
3. 测试allergen_service的merge_with_ai_inference方法
4. 测试FoodData模型是否正确包含过敏原字段
5. 测试真实API调用（需要API Key）
"""

import sys
import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.allergen_service import AllergenService, allergen_service
from app.models.food import FoodData, FoodResponse


class TestAllergenServiceMerge:
    """测试AllergenService的merge_with_ai_inference方法"""
    
    def setup_method(self):
        """每个测试方法前初始化"""
        self.service = AllergenService()
    
    def test_merge_only_keyword_detection(self):
        """测试仅有关键词检测结果的情况"""
        keyword_result = {
            "food_name": "番茄炒蛋",
            "detected_allergens": [
                {
                    "code": "egg",
                    "name": "鸡蛋",
                    "name_en": "Egg",
                    "matched_keywords": ["蛋", "炒蛋"],
                    "confidence": "high"
                }
            ],
            "allergen_count": 1,
            "has_allergens": True
        }
        
        result = self.service.merge_with_ai_inference(
            food_name="番茄炒蛋",
            keyword_result=keyword_result,
            ai_allergens=[],
            ai_reasoning=""
        )
        
        assert result["allergen_count"] == 1
        assert result["has_allergens"] == True
        assert len(result["detected_allergens"]) == 1
        assert result["detected_allergens"][0]["code"] == "egg"
        assert result["detected_allergens"][0]["source"] == "keyword"
        print("✓ 测试仅关键词检测结果 - 通过")
    
    def test_merge_only_ai_inference(self):
        """测试仅有AI推理结果的情况"""
        keyword_result = {
            "food_name": "宫保鸡丁",
            "detected_allergens": [],
            "allergen_count": 0,
            "has_allergens": False
        }
        
        result = self.service.merge_with_ai_inference(
            food_name="宫保鸡丁",
            keyword_result=keyword_result,
            ai_allergens=["peanut", "soy"],
            ai_reasoning="宫保鸡丁含有花生和酱油（大豆）"
        )
        
        assert result["allergen_count"] == 2
        assert result["has_allergens"] == True
        assert result["ai_reasoning"] == "宫保鸡丁含有花生和酱油（大豆）"
        
        # 检查每个过敏原的来源
        codes = {a["code"]: a for a in result["detected_allergens"]}
        assert codes["peanut"]["source"] == "ai"
        assert codes["soy"]["source"] == "ai"
        print("✓ 测试仅AI推理结果 - 通过")
    
    def test_merge_keyword_and_ai(self):
        """测试关键词检测和AI推理结果合并"""
        keyword_result = {
            "food_name": "蛋炒饭",
            "detected_allergens": [
                {
                    "code": "egg",
                    "name": "鸡蛋",
                    "name_en": "Egg",
                    "matched_keywords": ["蛋"],
                    "confidence": "medium"
                }
            ],
            "allergen_count": 1,
            "has_allergens": True
        }
        
        # AI也检测到蛋，并额外检测到大豆（酱油）
        result = self.service.merge_with_ai_inference(
            food_name="蛋炒饭",
            keyword_result=keyword_result,
            ai_allergens=["egg", "soy"],
            ai_reasoning="蛋炒饭含有鸡蛋，炒制时可能使用酱油（大豆）"
        )
        
        assert result["allergen_count"] == 2
        assert result["has_allergens"] == True
        
        # 检查来源标识
        codes = {a["code"]: a for a in result["detected_allergens"]}
        assert codes["egg"]["source"] == "keyword+ai"  # 两者都检测到
        assert codes["egg"]["confidence"] == "high"  # 双重确认置信度高
        assert codes["soy"]["source"] == "ai"  # 仅AI检测到
        print("✓ 测试关键词+AI合并结果 - 通过")
    
    def test_merge_with_user_allergens_warning(self):
        """测试合并时生成用户过敏原警告"""
        keyword_result = {
            "food_name": "宫保鸡丁",
            "detected_allergens": [
                {
                    "code": "peanut",
                    "name": "花生",
                    "name_en": "Peanut",
                    "matched_keywords": ["花生", "宫保"],
                    "confidence": "high"
                }
            ],
            "allergen_count": 1,
            "has_allergens": True
        }
        
        result = self.service.merge_with_ai_inference(
            food_name="宫保鸡丁",
            keyword_result=keyword_result,
            ai_allergens=["peanut", "soy"],
            ai_reasoning="宫保鸡丁含有花生和酱油",
            user_allergens=["花生"]  # 用户对花生过敏
        )
        
        assert result["has_warnings"] == True
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["allergen"] == "花生"
        assert "关键词匹配和AI推理" in result["warnings"][0]["message"]
        print("✓ 测试用户过敏原警告生成 - 通过")
    
    def test_merge_detection_methods_stats(self):
        """测试合并后的检测方法统计"""
        keyword_result = {
            "food_name": "清蒸鲈鱼",
            "detected_allergens": [
                {
                    "code": "fish",
                    "name": "鱼类",
                    "name_en": "Fish",
                    "matched_keywords": ["鱼", "鲈鱼"],
                    "confidence": "high"
                }
            ],
            "allergen_count": 1,
            "has_allergens": True
        }
        
        result = self.service.merge_with_ai_inference(
            food_name="清蒸鲈鱼",
            keyword_result=keyword_result,
            ai_allergens=["fish", "soy"],
            ai_reasoning="鲈鱼是鱼类过敏原，清蒸时通常用酱油调味"
        )
        
        # 检查统计信息
        assert "detection_methods" in result
        stats = result["detection_methods"]
        assert stats["keyword_count"] == 1
        assert stats["ai_count"] == 2
        assert stats["merged_count"] == 2
        print("✓ 测试检测方法统计 - 通过")
    
    def test_invalid_allergen_codes_filtered(self):
        """测试无效的过敏原代码被过滤"""
        keyword_result = {
            "food_name": "测试菜品",
            "detected_allergens": [],
            "allergen_count": 0,
            "has_allergens": False
        }
        
        # AI返回了一些无效的过敏原代码
        result = self.service.merge_with_ai_inference(
            food_name="测试菜品",
            keyword_result=keyword_result,
            ai_allergens=["invalid_code", "egg", "unknown", "peanut"],
            ai_reasoning="测试"
        )
        
        # 只有有效的代码被保留
        codes = [a["code"] for a in result["detected_allergens"]]
        assert "invalid_code" not in codes
        assert "unknown" not in codes
        assert "egg" in codes
        assert "peanut" in codes
        assert result["allergen_count"] == 2
        print("✓ 测试无效代码过滤 - 通过")


class TestNutritionResponseParsing:
    """测试营养分析响应解析（模拟AI响应）"""
    
    def test_parse_response_with_allergens(self):
        """测试解析包含过敏原的AI响应"""
        # 模拟AI返回的JSON字符串
        mock_ai_response = json.dumps({
            "calories": 180.0,
            "protein": 18.0,
            "fat": 10.0,
            "carbs": 8.0,
            "recommendation": "蛋白质丰富，适合减脂期食用",
            "allergens": ["peanut", "soy"],
            "allergen_reasoning": "宫保鸡丁含有花生米和酱油"
        })
        
        # 测试解析
        from app.services.ai_service import AIService
        
        # 使用mock避免真实API调用
        with patch.object(AIService, '__init__', lambda x: None):
            service = AIService()
            service.ark_client = None
            
            result = service._parse_nutrition_response(mock_ai_response, "宫保鸡丁")
            
            assert result["name"] == "宫保鸡丁"
            assert result["calories"] == 180.0
            assert result["protein"] == 18.0
            assert "allergens" in result
            assert result["allergens"] == ["peanut", "soy"]
            assert result["allergen_reasoning"] == "宫保鸡丁含有花生米和酱油"
            print("✓ 测试解析含过敏原的AI响应 - 通过")
    
    def test_parse_response_without_allergens(self):
        """测试解析不含过敏原的AI响应（向后兼容）"""
        mock_ai_response = json.dumps({
            "calories": 50.0,
            "protein": 1.0,
            "fat": 0.2,
            "carbs": 12.0,
            "recommendation": "低热量蔬菜，适合减脂"
        })
        
        from app.services.ai_service import AIService
        
        with patch.object(AIService, '__init__', lambda x: None):
            service = AIService()
            service.ark_client = None
            
            result = service._parse_nutrition_response(mock_ai_response, "白菜")
            
            assert result["name"] == "白菜"
            assert result["allergens"] == []
            assert result["allergen_reasoning"] == ""
            print("✓ 测试解析不含过敏原的响应（向后兼容） - 通过")
    
    def test_parse_response_with_invalid_allergen_codes(self):
        """测试解析包含无效过敏原代码的响应"""
        mock_ai_response = json.dumps({
            "calories": 150.0,
            "protein": 10.0,
            "fat": 8.0,
            "carbs": 15.0,
            "recommendation": "营养均衡",
            "allergens": ["egg", "invalid_allergen", "MILK", "Peanut"],  # 混合大小写和无效代码
            "allergen_reasoning": "测试"
        })
        
        from app.services.ai_service import AIService
        
        with patch.object(AIService, '__init__', lambda x: None):
            service = AIService()
            service.ark_client = None
            
            result = service._parse_nutrition_response(mock_ai_response, "测试菜品")
            
            # 应该过滤掉无效代码，并统一转小写
            assert "invalid_allergen" not in result["allergens"]
            assert "egg" in result["allergens"]
            assert "milk" in result["allergens"]  # MILK -> milk
            assert "peanut" in result["allergens"]  # Peanut -> peanut
            print("✓ 测试过滤无效过敏原代码 - 通过")


class TestFoodDataModel:
    """测试FoodData模型"""
    
    def test_food_data_with_allergens(self):
        """测试创建包含过敏原字段的FoodData"""
        food_data = FoodData(
            name="番茄炒蛋",
            calories=150.0,
            protein=10.5,
            fat=8.2,
            carbs=6.3,
            recommendation="营养均衡，适合减脂",
            allergens=["egg"],
            allergen_reasoning="主要食材是鸡蛋"
        )
        
        assert food_data.name == "番茄炒蛋"
        assert food_data.allergens == ["egg"]
        assert food_data.allergen_reasoning == "主要食材是鸡蛋"
        print("✓ 测试FoodData含过敏原字段 - 通过")
    
    def test_food_data_default_allergen_values(self):
        """测试FoodData过敏原字段默认值"""
        food_data = FoodData(
            name="白菜",
            calories=20.0,
            protein=1.0,
            fat=0.2,
            carbs=4.0,
            recommendation="低热量蔬菜"
        )
        
        # 默认值应该是空列表和空字符串
        assert food_data.allergens == []
        assert food_data.allergen_reasoning == ""
        print("✓ 测试FoodData过敏原字段默认值 - 通过")
    
    def test_food_response_with_allergens(self):
        """测试FoodResponse包含过敏原信息"""
        food_data = FoodData(
            name="宫保鸡丁",
            calories=180.0,
            protein=18.0,
            fat=10.0,
            carbs=8.0,
            recommendation="高蛋白，注意花生过敏",
            allergens=["peanut", "soy"],
            allergen_reasoning="含有花生和酱油"
        )
        
        response = FoodResponse(
            success=True,
            message="分析成功",
            data=food_data
        )
        
        assert response.success == True
        assert response.data.allergens == ["peanut", "soy"]
        print("✓ 测试FoodResponse含过敏原信息 - 通过")


class TestPromptEnhancement:
    """测试Prompt增强"""
    
    def test_prompt_contains_allergen_requirements(self):
        """测试营养分析Prompt包含过敏原推理要求"""
        from app.services.ai_service import AIService
        
        with patch.object(AIService, '__init__', lambda x: None):
            service = AIService()
            service.ark_client = None
            
            prompt = service._build_nutrition_prompt("宫保鸡丁")
            
            # 检查Prompt是否包含过敏原相关要求
            assert "过敏原" in prompt
            assert "allergens" in prompt
            assert "allergen_reasoning" in prompt
            assert "八大类过敏原" in prompt
            assert "隐性过敏原" in prompt
            
            # 检查是否包含八大类过敏原代码说明
            assert "milk" in prompt
            assert "egg" in prompt
            assert "fish" in prompt
            assert "shellfish" in prompt
            assert "peanut" in prompt
            assert "tree_nut" in prompt
            assert "wheat" in prompt
            assert "soy" in prompt
            print("✓ 测试Prompt包含过敏原推理要求 - 通过")


class TestRealAPIIntegration:
    """真实API集成测试（需要API Key环境变量）"""
    
    @pytest.mark.skipif(
        not os.getenv("ARK_API_KEY"),
        reason="需要设置ARK_API_KEY环境变量才能运行此测试"
    )
    def test_real_api_food_analysis_with_allergens(self):
        """测试真实API调用返回过敏原信息"""
        from app.services.ai_service import AIService
        
        try:
            service = AIService()
            result = service.analyze_food_nutrition("宫保鸡丁")
            
            # 验证基本营养字段
            assert "name" in result
            assert "calories" in result
            assert "protein" in result
            assert "fat" in result
            assert "carbs" in result
            assert "recommendation" in result
            
            # 验证过敏原字段
            assert "allergens" in result
            assert "allergen_reasoning" in result
            assert isinstance(result["allergens"], list)
            
            # 宫保鸡丁应该至少检测到花生
            print(f"AI返回的过敏原: {result['allergens']}")
            print(f"AI推理说明: {result['allergen_reasoning']}")
            
            # 基本验证（宫保鸡丁通常含花生）
            # 注意：AI结果可能有波动，所以这里只验证格式正确
            assert isinstance(result["allergen_reasoning"], str)
            print("✓ 真实API测试 - 通过")
            
        except Exception as e:
            print(f"真实API测试失败（可能是网络或配置问题）: {e}")
            raise


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Phase 7 测试：过敏原AI推理（Prompt增强）")
    print("=" * 60)
    print()
    
    # 测试AllergenService合并功能
    print("【测试1】AllergenService.merge_with_ai_inference")
    print("-" * 40)
    test_merge = TestAllergenServiceMerge()
    test_merge.setup_method()
    test_merge.test_merge_only_keyword_detection()
    test_merge.test_merge_only_ai_inference()
    test_merge.test_merge_keyword_and_ai()
    test_merge.test_merge_with_user_allergens_warning()
    test_merge.test_merge_detection_methods_stats()
    test_merge.test_invalid_allergen_codes_filtered()
    print()
    
    # 测试响应解析
    print("【测试2】营养分析响应解析")
    print("-" * 40)
    test_parse = TestNutritionResponseParsing()
    test_parse.test_parse_response_with_allergens()
    test_parse.test_parse_response_without_allergens()
    test_parse.test_parse_response_with_invalid_allergen_codes()
    print()
    
    # 测试数据模型
    print("【测试3】FoodData数据模型")
    print("-" * 40)
    test_model = TestFoodDataModel()
    test_model.test_food_data_with_allergens()
    test_model.test_food_data_default_allergen_values()
    test_model.test_food_response_with_allergens()
    print()
    
    # 测试Prompt增强
    print("【测试4】Prompt增强检查")
    print("-" * 40)
    test_prompt = TestPromptEnhancement()
    test_prompt.test_prompt_contains_allergen_requirements()
    print()
    
    # 真实API测试（可选）
    print("【测试5】真实API集成测试")
    print("-" * 40)
    if os.getenv("ARK_API_KEY"):
        test_api = TestRealAPIIntegration()
        try:
            test_api.test_real_api_food_analysis_with_allergens()
        except Exception as e:
            print(f"⚠ 真实API测试跳过或失败: {e}")
    else:
        print("⚠ 跳过真实API测试（未设置ARK_API_KEY环境变量）")
    print()
    
    print("=" * 60)
    print("✅ Phase 7 所有单元测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
