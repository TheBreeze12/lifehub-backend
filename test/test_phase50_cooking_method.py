"""
测试烹饪方式热量差异对比功能（Phase 50）
- 测试Pydantic模型字段定义（CookingMethodItem + FoodData新增字段）
- 测试AI Prompt构建是否包含烹饪方式对比要求
- 测试AI响应解析是否正确提取烹饪方式数据
- 测试默认营养数据中烹饪方式字段的默认值
- 测试API端点返回烹饪方式对比数据
"""
import sys
import os
import json
import types

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock dashscope模块（如果未安装）
if 'dashscope' not in sys.modules:
    dashscope_mock = types.ModuleType('dashscope')
    dashscope_mock.Generation = type('Generation', (), {'call': staticmethod(lambda **kwargs: None)})
    dashscope_mock.api_key = None
    sys.modules['dashscope'] = dashscope_mock
    sys.modules['dashscope.Generation'] = dashscope_mock.Generation

# 设置测试用的环境变量（避免AIService初始化失败）
if not os.getenv("DASHSCOPE_API_KEY"):
    os.environ["DASHSCOPE_API_KEY"] = "test_dummy_key_for_phase50"


def print_separator(title: str):
    """打印分隔线"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(success: bool, message: str):
    """打印测试结果"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")
    return success


# ==================== 测试1：Pydantic模型 CookingMethodItem ====================

def test_cooking_method_item_import():
    """测试CookingMethodItem模型能否正确导入"""
    print_separator("测试1：CookingMethodItem模型导入测试")
    
    try:
        from app.models.food import CookingMethodItem
        return print_result(True, "CookingMethodItem模型导入成功")
    except ImportError as e:
        return print_result(False, f"模型导入失败: {e}")


def test_cooking_method_item_fields():
    """测试CookingMethodItem模型字段定义"""
    print_separator("测试2：CookingMethodItem字段定义测试")
    
    try:
        from app.models.food import CookingMethodItem
        
        # 测试有效数据
        item = CookingMethodItem(
            method="清蒸",
            calories=105.0,
            fat=3.0,
            description="保留原味，低油脂，适合减脂期"
        )
        
        assert item.method == "清蒸", f"method不正确: {item.method}"
        assert item.calories == 105.0, f"calories不正确: {item.calories}"
        assert item.fat == 3.0, f"fat不正确: {item.fat}"
        assert item.description == "保留原味，低油脂，适合减脂期", f"description不正确"
        
        print(f"    ✓ 字段赋值和读取正确")
        return print_result(True, "CookingMethodItem字段定义正确")
    except Exception as e:
        return print_result(False, f"字段测试失败: {e}")


def test_cooking_method_item_validation():
    """测试CookingMethodItem模型验证"""
    print_separator("测试3：CookingMethodItem模型验证测试")
    
    try:
        from app.models.food import CookingMethodItem
        
        # 测试缺少必填字段
        try:
            invalid_item = CookingMethodItem(method="油炸")
            return print_result(False, "应该拒绝缺少必填字段的数据")
        except Exception:
            print(f"    ✓ 正确拒绝缺少必填字段的数据")
        
        # 测试多个有效数据
        items = [
            CookingMethodItem(method="红烧", calories=200.0, fat=12.0, description="酱汁增加热量"),
            CookingMethodItem(method="油炸", calories=280.0, fat=20.0, description="油炸导致脂肪大幅增加"),
            CookingMethodItem(method="水煮", calories=90.0, fat=2.0, description="最低热量烹饪方式"),
        ]
        
        assert len(items) == 3
        assert items[0].method == "红烧"
        assert items[1].calories == 280.0
        assert items[2].fat == 2.0
        print(f"    ✓ 多条烹饪方式数据验证通过")
        
        return print_result(True, "CookingMethodItem验证正确")
    except Exception as e:
        return print_result(False, f"验证测试失败: {e}")


def test_cooking_method_item_serialization():
    """测试CookingMethodItem序列化"""
    print_separator("测试4：CookingMethodItem序列化测试")
    
    try:
        from app.models.food import CookingMethodItem
        
        item = CookingMethodItem(
            method="清蒸",
            calories=105.0,
            fat=3.0,
            description="保留原味"
        )
        
        # 测试dict序列化
        item_dict = item.model_dump()
        assert isinstance(item_dict, dict)
        assert "method" in item_dict
        assert "calories" in item_dict
        assert "fat" in item_dict
        assert "description" in item_dict
        print(f"    ✓ model_dump()序列化正确")
        
        # 测试JSON序列化
        item_json = item.model_dump_json()
        parsed = json.loads(item_json)
        assert parsed["method"] == "清蒸"
        assert parsed["calories"] == 105.0
        print(f"    ✓ JSON序列化和反序列化正确")
        
        return print_result(True, "序列化测试通过")
    except Exception as e:
        return print_result(False, f"序列化测试失败: {e}")


# ==================== 测试2：FoodData新增烹饪方式字段 ====================

def test_food_data_has_cooking_method_field():
    """测试FoodData模型是否包含cooking_method_comparisons字段"""
    print_separator("测试5：FoodData烹饪方式字段测试")
    
    try:
        from app.models.food import FoodData
        
        # 测试不传cooking_method_comparisons时使用默认值
        food = FoodData(
            name="番茄炒蛋",
            calories=150.0,
            protein=10.5,
            fat=8.2,
            carbs=6.3,
            recommendation="营养均衡"
        )
        
        assert hasattr(food, 'cooking_method_comparisons'), "FoodData缺少cooking_method_comparisons字段"
        # 默认值应为空列表或None
        assert food.cooking_method_comparisons is None or food.cooking_method_comparisons == [], \
            f"默认值不正确: {food.cooking_method_comparisons}"
        print(f"    ✓ cooking_method_comparisons字段存在，默认值正确")
        
        return print_result(True, "FoodData包含烹饪方式字段")
    except Exception as e:
        return print_result(False, f"字段测试失败: {e}")


def test_food_data_with_cooking_methods():
    """测试FoodData包含烹饪方式对比数据"""
    print_separator("测试6：FoodData携带烹饪方式数据测试")
    
    try:
        from app.models.food import FoodData, CookingMethodItem
        
        cooking_methods = [
            CookingMethodItem(method="清蒸", calories=105.0, fat=3.0, description="保留原味"),
            CookingMethodItem(method="红烧", calories=180.0, fat=10.0, description="酱汁增加热量"),
            CookingMethodItem(method="油炸", calories=260.0, fat=18.0, description="油炸高热量"),
        ]
        
        food = FoodData(
            name="鲈鱼",
            calories=105.0,
            protein=19.5,
            fat=3.0,
            carbs=0.5,
            recommendation="高蛋白低脂",
            cooking_method_comparisons=cooking_methods
        )
        
        assert food.cooking_method_comparisons is not None
        assert len(food.cooking_method_comparisons) == 3
        assert food.cooking_method_comparisons[0].method == "清蒸"
        assert food.cooking_method_comparisons[1].calories == 180.0
        assert food.cooking_method_comparisons[2].fat == 18.0
        print(f"    ✓ FoodData携带3种烹饪方式数据正确")
        
        return print_result(True, "FoodData烹饪方式数据正确")
    except Exception as e:
        return print_result(False, f"测试失败: {e}")


def test_food_data_serialization_with_cooking_methods():
    """测试FoodData含烹饪方式时的序列化"""
    print_separator("测试7：FoodData含烹饪方式序列化测试")
    
    try:
        from app.models.food import FoodData, CookingMethodItem
        
        food = FoodData(
            name="鸡胸肉",
            calories=165.0,
            protein=31.0,
            fat=3.6,
            carbs=0.0,
            recommendation="优质蛋白来源",
            cooking_method_comparisons=[
                CookingMethodItem(method="水煮", calories=165.0, fat=3.6, description="最健康"),
                CookingMethodItem(method="煎", calories=220.0, fat=10.0, description="增加油脂"),
            ]
        )
        
        # 序列化为dict
        food_dict = food.model_dump()
        assert "cooking_method_comparisons" in food_dict
        assert len(food_dict["cooking_method_comparisons"]) == 2
        assert food_dict["cooking_method_comparisons"][0]["method"] == "水煮"
        print(f"    ✓ model_dump包含烹饪方式数据")
        
        # 序列化为JSON
        food_json = food.model_dump_json()
        parsed = json.loads(food_json)
        assert "cooking_method_comparisons" in parsed
        assert len(parsed["cooking_method_comparisons"]) == 2
        print(f"    ✓ JSON序列化包含烹饪方式数据")
        
        return print_result(True, "序列化测试通过")
    except Exception as e:
        return print_result(False, f"序列化测试失败: {e}")


# ==================== 测试3：AI Prompt包含烹饪方式对比要求 ====================

def test_prompt_contains_cooking_method_section():
    """测试营养分析Prompt是否包含烹饪方式对比要求"""
    print_separator("测试8：AI Prompt烹饪方式对比要求测试")
    
    try:
        from app.services.ai_service import AIService
        
        service = AIService()
        prompt = service._build_nutrition_prompt("红烧肉")
        
        # 检查Prompt中是否包含烹饪方式相关内容
        assert "烹饪方式" in prompt or "cooking_method" in prompt, \
            "Prompt中缺少烹饪方式相关内容"
        print(f"    ✓ Prompt包含'烹饪方式'关键词")
        
        assert "cooking_method_comparisons" in prompt, \
            "Prompt中缺少cooking_method_comparisons字段要求"
        print(f"    ✓ Prompt包含'cooking_method_comparisons'字段")
        
        # 检查是否要求返回method, calories, fat, description
        assert "method" in prompt, "Prompt中缺少method字段"
        assert "description" in prompt, "Prompt中缺少description字段"
        print(f"    ✓ Prompt包含烹饪方式对比的必要字段要求")
        
        return print_result(True, "AI Prompt包含烹饪方式对比要求")
    except Exception as e:
        return print_result(False, f"Prompt测试失败: {e}")


# ==================== 测试4：AI响应解析烹饪方式数据 ====================

def test_parse_response_with_cooking_methods():
    """测试解析包含烹饪方式对比的AI响应"""
    print_separator("测试9：解析含烹饪方式的AI响应测试")
    
    try:
        from app.services.ai_service import AIService
        
        service = AIService()
        
        # 模拟AI返回的JSON响应（包含烹饪方式对比）
        mock_response = json.dumps({
            "calories": 180.0,
            "protein": 18.0,
            "fat": 10.0,
            "carbs": 8.0,
            "recommendation": "蛋白质丰富，建议适量食用",
            "allergens": ["peanut", "soy"],
            "allergen_reasoning": "含花生和酱油",
            "cooking_method_comparisons": [
                {
                    "method": "清炒",
                    "calories": 150.0,
                    "fat": 8.0,
                    "description": "少油翻炒，热量较低"
                },
                {
                    "method": "油炸",
                    "calories": 280.0,
                    "fat": 22.0,
                    "description": "油炸热量最高"
                },
                {
                    "method": "水煮",
                    "calories": 120.0,
                    "fat": 5.0,
                    "description": "水煮最健康"
                }
            ]
        })
        
        result = service._parse_nutrition_response(mock_response, "宫保鸡丁")
        
        # 验证基本字段
        assert result["name"] == "宫保鸡丁"
        assert result["calories"] == 180.0
        print(f"    ✓ 基本营养字段解析正确")
        
        # 验证烹饪方式字段
        assert "cooking_method_comparisons" in result, \
            "解析结果缺少cooking_method_comparisons字段"
        
        comparisons = result["cooking_method_comparisons"]
        assert isinstance(comparisons, list), "cooking_method_comparisons应为列表"
        assert len(comparisons) == 3, f"应有3种烹饪方式，实际: {len(comparisons)}"
        
        # 验证每个烹饪方式的字段
        first = comparisons[0]
        assert "method" in first, "缺少method字段"
        assert "calories" in first, "缺少calories字段"
        assert "fat" in first, "缺少fat字段"
        assert "description" in first, "缺少description字段"
        print(f"    ✓ 烹饪方式对比数据解析正确，共{len(comparisons)}种")
        
        return print_result(True, "AI响应解析烹饪方式数据正确")
    except Exception as e:
        return print_result(False, f"解析测试失败: {e}")


def test_parse_response_without_cooking_methods():
    """测试解析不包含烹饪方式的AI响应（向后兼容）"""
    print_separator("测试10：解析无烹饪方式的AI响应（兼容性）")
    
    try:
        from app.services.ai_service import AIService
        
        service = AIService()
        
        # 模拟旧版AI响应（不含烹饪方式）
        mock_response = json.dumps({
            "calories": 150.0,
            "protein": 10.0,
            "fat": 8.0,
            "carbs": 15.0,
            "recommendation": "营养均衡",
            "allergens": ["egg"],
            "allergen_reasoning": "含鸡蛋"
        })
        
        result = service._parse_nutrition_response(mock_response, "番茄炒蛋")
        
        # 验证基本字段正常
        assert result["name"] == "番茄炒蛋"
        assert result["calories"] == 150.0
        print(f"    ✓ 基本字段正常")
        
        # 验证烹饪方式字段有合理默认值
        assert "cooking_method_comparisons" in result, \
            "缺少cooking_method_comparisons字段"
        comparisons = result["cooking_method_comparisons"]
        assert comparisons == [] or comparisons is None, \
            f"无烹饪方式时应为空列表或None，实际: {comparisons}"
        print(f"    ✓ 无烹饪方式时默认值正确")
        
        return print_result(True, "向后兼容性测试通过")
    except Exception as e:
        return print_result(False, f"兼容性测试失败: {e}")


# ==================== 测试5：默认营养数据 ====================

def test_default_nutrition_has_cooking_method_field():
    """测试默认营养数据是否包含烹饪方式字段"""
    print_separator("测试11：默认营养数据烹饪方式字段测试")
    
    try:
        from app.services.ai_service import AIService
        
        service = AIService()
        default_data = service._get_default_nutrition("测试食物")
        
        assert "cooking_method_comparisons" in default_data, \
            "默认数据缺少cooking_method_comparisons字段"
        
        comparisons = default_data["cooking_method_comparisons"]
        assert comparisons == [] or comparisons is None, \
            f"默认烹饪方式应为空: {comparisons}"
        print(f"    ✓ 默认营养数据包含cooking_method_comparisons字段")
        
        return print_result(True, "默认营养数据测试通过")
    except Exception as e:
        return print_result(False, f"默认数据测试失败: {e}")


# ==================== 测试6：FoodResponse完整性测试 ====================

def test_food_response_with_cooking_methods():
    """测试FoodResponse包含烹饪方式对比数据"""
    print_separator("测试12：FoodResponse完整性测试")
    
    try:
        from app.models.food import FoodData, FoodResponse, CookingMethodItem
        
        food_data = FoodData(
            name="红烧肉",
            calories=350.0,
            protein=15.0,
            fat=25.0,
            carbs=12.0,
            recommendation="热量较高，建议少量食用",
            allergens=["soy"],
            allergen_reasoning="含酱油",
            cooking_method_comparisons=[
                CookingMethodItem(method="红烧", calories=350.0, fat=25.0, description="传统做法，热量高"),
                CookingMethodItem(method="清蒸", calories=200.0, fat=12.0, description="减少酱汁，热量降低"),
                CookingMethodItem(method="卤制", calories=300.0, fat=20.0, description="卤汁入味，热量中等"),
            ]
        )
        
        response = FoodResponse(
            success=True,
            message="分析成功",
            data=food_data
        )
        
        assert response.success is True
        assert response.data is not None
        assert response.data.cooking_method_comparisons is not None
        assert len(response.data.cooking_method_comparisons) == 3
        print(f"    ✓ FoodResponse包含完整的烹饪方式对比数据")
        
        # 验证JSON序列化
        response_dict = response.model_dump()
        assert "cooking_method_comparisons" in response_dict["data"]
        assert len(response_dict["data"]["cooking_method_comparisons"]) == 3
        print(f"    ✓ FoodResponse JSON序列化正确")
        
        return print_result(True, "FoodResponse完整性测试通过")
    except Exception as e:
        return print_result(False, f"FoodResponse测试失败: {e}")


# ==================== 测试7：端到端数据流测试 ====================

def test_end_to_end_data_flow():
    """测试从AI响应解析到Pydantic模型的端到端数据流"""
    print_separator("测试13：端到端数据流测试")
    
    try:
        from app.services.ai_service import AIService
        from app.models.food import FoodData, FoodResponse
        
        service = AIService()
        
        # 模拟完整的AI响应
        mock_ai_response = json.dumps({
            "calories": 320.0,
            "protein": 28.0,
            "fat": 18.0,
            "carbs": 15.0,
            "recommendation": "蛋白质丰富，适合运动后食用",
            "allergens": ["peanut", "soy"],
            "allergen_reasoning": "含花生和酱油",
            "cooking_method_comparisons": [
                {"method": "炒", "calories": 320.0, "fat": 18.0, "description": "标准做法"},
                {"method": "蒸", "calories": 200.0, "fat": 8.0, "description": "减少油脂"},
                {"method": "炸", "calories": 400.0, "fat": 28.0, "description": "油炸高热量"}
            ]
        })
        
        # Step 1: 解析AI响应
        parsed_data = service._parse_nutrition_response(mock_ai_response, "宫保鸡丁")
        assert "cooking_method_comparisons" in parsed_data
        print(f"    ✓ Step 1: AI响应解析成功")
        
        # Step 2: 构建FoodData
        food_data = FoodData(**parsed_data)
        assert food_data.cooking_method_comparisons is not None
        assert len(food_data.cooking_method_comparisons) == 3
        print(f"    ✓ Step 2: FoodData构建成功")
        
        # Step 3: 构建FoodResponse
        response = FoodResponse(success=True, message="分析成功", data=food_data)
        assert response.data.cooking_method_comparisons[0].method == "炒"
        print(f"    ✓ Step 3: FoodResponse构建成功")
        
        # Step 4: JSON序列化（模拟API返回）
        response_json = response.model_dump_json()
        final = json.loads(response_json)
        assert len(final["data"]["cooking_method_comparisons"]) == 3
        assert final["data"]["cooking_method_comparisons"][1]["method"] == "蒸"
        print(f"    ✓ Step 4: JSON API响应序列化正确")
        
        return print_result(True, "端到端数据流测试通过")
    except Exception as e:
        return print_result(False, f"端到端测试失败: {e}")


# ==================== 主测试函数 ====================

def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  Phase 50: 烹饪方式热量差异对比功能测试")
    print("="*60)
    
    results = []
    
    # Pydantic模型测试
    results.append(("CookingMethodItem导入", test_cooking_method_item_import()))
    results.append(("CookingMethodItem字段", test_cooking_method_item_fields()))
    results.append(("CookingMethodItem验证", test_cooking_method_item_validation()))
    results.append(("CookingMethodItem序列化", test_cooking_method_item_serialization()))
    
    # FoodData新增字段测试
    results.append(("FoodData烹饪方式字段", test_food_data_has_cooking_method_field()))
    results.append(("FoodData携带烹饪方式", test_food_data_with_cooking_methods()))
    results.append(("FoodData序列化", test_food_data_serialization_with_cooking_methods()))
    
    # AI Prompt测试
    results.append(("Prompt烹饪方式要求", test_prompt_contains_cooking_method_section()))
    
    # AI响应解析测试
    results.append(("解析含烹饪方式响应", test_parse_response_with_cooking_methods()))
    results.append(("解析无烹饪方式响应", test_parse_response_without_cooking_methods()))
    
    # 默认数据测试
    results.append(("默认数据烹饪方式字段", test_default_nutrition_has_cooking_method_field()))
    
    # FoodResponse测试
    results.append(("FoodResponse完整性", test_food_response_with_cooking_methods()))
    
    # 端到端测试
    results.append(("端到端数据流", test_end_to_end_data_flow()))
    
    # 打印测试总结
    print("\n" + "="*60)
    print("  测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n  总计: {passed}/{total} 通过")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
