"""
测试过敏原检测功能（Phase 6）
- 测试过敏原检测接口 POST /api/food/allergen/check
- 测试获取过敏原类别接口 GET /api/food/allergen/categories
- 测试八大类过敏原的关键词匹配
- 测试用户过敏原告警匹配
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"


def print_separator(title: str):
    """打印分隔线"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(success: bool, message: str):
    """打印测试结果"""
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")


class TestResults:
    """测试结果统计"""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.failed_tests = []
    
    def add_result(self, test_name: str, passed: bool):
        self.total += 1
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            self.failed_tests.append(test_name)
    
    def print_summary(self):
        print_separator("测试结果汇总")
        print(f"总计: {self.total} 个测试")
        print(f"通过: {self.passed} 个 ✅")
        print(f"失败: {self.failed} 个 ❌")
        if self.failed_tests:
            print(f"\n失败的测试:")
            for test in self.failed_tests:
                print(f"  - {test}")
        print()
        return self.failed == 0


results = TestResults()


def test_get_allergen_categories() -> bool:
    """测试获取过敏原类别列表"""
    print_separator("测试1：获取过敏原类别列表")
    
    url = f"{BASE_URL}/api/food/allergen/categories"
    
    try:
        response = requests.get(url)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("code") == 200:
                categories = data.get("data", [])
                # 验证八大类过敏原
                expected_codes = {"milk", "egg", "fish", "shellfish", "peanut", "tree_nut", "wheat", "soy"}
                actual_codes = {cat.get("code") for cat in categories}
                
                if expected_codes == actual_codes:
                    print_result(True, f"成功获取所有 {len(categories)} 种过敏原类别")
                    return True
                else:
                    missing = expected_codes - actual_codes
                    extra = actual_codes - expected_codes
                    print_result(False, f"过敏原类别不完整，缺少: {missing}, 多余: {extra}")
                    return False
            else:
                print_result(False, f"响应code不为200: {data.get('message')}")
                return False
        else:
            print_result(False, f"HTTP状态码错误: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"请求异常: {str(e)}")
        return False


def test_allergen_check_basic() -> bool:
    """测试基础过敏原检测 - 检测宫保鸡丁中的花生"""
    print_separator("测试2：基础过敏原检测 - 宫保鸡丁")
    
    url = f"{BASE_URL}/api/food/allergen/check"
    payload = {
        "food_name": "宫保鸡丁"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("code") == 200:
                result = data.get("data", {})
                detected = result.get("detected_allergens", [])
                
                # 宫保鸡丁应该检测到花生
                peanut_detected = any(a.get("code") == "peanut" for a in detected)
                
                if peanut_detected:
                    print_result(True, "成功检测到宫保鸡丁中的花生过敏原")
                    return True
                else:
                    print_result(False, "未能检测到宫保鸡丁中的花生过敏原")
                    return False
            else:
                print_result(False, f"响应code不为200: {data.get('message')}")
                return False
        else:
            print_result(False, f"HTTP状态码错误: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"请求异常: {str(e)}")
        return False


def test_allergen_check_with_ingredients() -> bool:
    """测试带配料的过敏原检测"""
    print_separator("测试3：带配料的过敏原检测 - 番茄炒蛋")
    
    url = f"{BASE_URL}/api/food/allergen/check"
    payload = {
        "food_name": "番茄炒蛋",
        "ingredients": ["番茄", "鸡蛋", "葱", "盐", "油"]
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("code") == 200:
                result = data.get("data", {})
                detected = result.get("detected_allergens", [])
                
                # 番茄炒蛋应该检测到鸡蛋
                egg_detected = any(a.get("code") == "egg" for a in detected)
                
                if egg_detected:
                    print_result(True, "成功检测到番茄炒蛋中的鸡蛋过敏原")
                    return True
                else:
                    print_result(False, "未能检测到番茄炒蛋中的鸡蛋过敏原")
                    return False
            else:
                print_result(False, f"响应code不为200: {data.get('message')}")
                return False
        else:
            print_result(False, f"HTTP状态码错误: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"请求异常: {str(e)}")
        return False


def test_allergen_check_user_warning() -> bool:
    """测试用户过敏原告警匹配"""
    print_separator("测试4：用户过敏原告警匹配")
    
    url = f"{BASE_URL}/api/food/allergen/check"
    payload = {
        "food_name": "虾仁炒蛋",
        "ingredients": ["虾仁", "鸡蛋", "葱", "盐"],
        "user_allergens": ["虾", "鸡蛋"]  # 用户对虾和鸡蛋过敏
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("code") == 200:
                result = data.get("data", {})
                warnings = result.get("warnings", [])
                has_warnings = result.get("has_warnings", False)
                
                # 应该有告警
                if has_warnings and len(warnings) > 0:
                    print_result(True, f"成功生成 {len(warnings)} 条过敏原告警")
                    return True
                else:
                    print_result(False, "未能生成用户过敏原告警")
                    return False
            else:
                print_result(False, f"响应code不为200: {data.get('message')}")
                return False
        else:
            print_result(False, f"HTTP状态码错误: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"请求异常: {str(e)}")
        return False


def test_allergen_check_no_allergen() -> bool:
    """测试无过敏原食物"""
    print_separator("测试5：无过敏原食物检测 - 清炒白菜")
    
    url = f"{BASE_URL}/api/food/allergen/check"
    payload = {
        "food_name": "清炒白菜",
        "ingredients": ["白菜", "蒜", "盐", "油"]
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("code") == 200:
                result = data.get("data", {})
                detected = result.get("detected_allergens", [])
                has_allergens = result.get("has_allergens", True)
                
                # 清炒白菜应该没有常见过敏原
                if not has_allergens and len(detected) == 0:
                    print_result(True, "正确识别：清炒白菜无常见过敏原")
                    return True
                else:
                    print_result(False, f"误报过敏原: {[a.get('name') for a in detected]}")
                    return False
            else:
                print_result(False, f"响应code不为200: {data.get('message')}")
                return False
        else:
            print_result(False, f"HTTP状态码错误: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"请求异常: {str(e)}")
        return False


def test_allergen_check_multiple() -> bool:
    """测试检测多种过敏原"""
    print_separator("测试6：多过敏原食物检测 - 海鲜豆腐煲")
    
    url = f"{BASE_URL}/api/food/allergen/check"
    payload = {
        "food_name": "海鲜豆腐煲",
        "ingredients": ["虾仁", "蛤蜊", "豆腐", "鸡蛋", "葱"]
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("code") == 200:
                result = data.get("data", {})
                detected = result.get("detected_allergens", [])
                allergen_count = result.get("allergen_count", 0)
                
                # 应该检测到多种过敏原：甲壳类、大豆、鸡蛋
                detected_codes = {a.get("code") for a in detected}
                expected_codes = {"shellfish", "soy", "egg"}
                
                # 至少检测到这三种
                if expected_codes.issubset(detected_codes):
                    print_result(True, f"成功检测到 {allergen_count} 种过敏原: {[a.get('name') for a in detected]}")
                    return True
                else:
                    missing = expected_codes - detected_codes
                    print_result(False, f"漏检过敏原: {missing}, 检测到: {detected_codes}")
                    return False
            else:
                print_result(False, f"响应code不为200: {data.get('message')}")
                return False
        else:
            print_result(False, f"HTTP状态码错误: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"请求异常: {str(e)}")
        return False


def test_allergen_check_milk_products() -> bool:
    """测试乳制品过敏原检测"""
    print_separator("测试7：乳制品过敏原检测 - 芝士焗饭")
    
    url = f"{BASE_URL}/api/food/allergen/check"
    payload = {
        "food_name": "芝士焗饭",
        "ingredients": ["米饭", "芝士", "奶油", "培根"]
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("code") == 200:
                result = data.get("data", {})
                detected = result.get("detected_allergens", [])
                
                # 应该检测到乳制品
                milk_detected = any(a.get("code") == "milk" for a in detected)
                
                if milk_detected:
                    print_result(True, "成功检测到芝士焗饭中的乳制品过敏原")
                    return True
                else:
                    print_result(False, "未能检测到芝士焗饭中的乳制品过敏原")
                    return False
            else:
                print_result(False, f"响应code不为200: {data.get('message')}")
                return False
        else:
            print_result(False, f"HTTP状态码错误: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"请求异常: {str(e)}")
        return False


def test_allergen_check_wheat() -> bool:
    """测试小麦/麸质过敏原检测"""
    print_separator("测试8：小麦过敏原检测 - 炸酱面")
    
    url = f"{BASE_URL}/api/food/allergen/check"
    payload = {
        "food_name": "炸酱面",
        "ingredients": ["面条", "肉末", "酱油", "葱", "黄瓜"]
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("code") == 200:
                result = data.get("data", {})
                detected = result.get("detected_allergens", [])
                
                # 应该检测到小麦
                wheat_detected = any(a.get("code") == "wheat" for a in detected)
                
                if wheat_detected:
                    print_result(True, "成功检测到炸酱面中的小麦过敏原")
                    return True
                else:
                    print_result(False, "未能检测到炸酱面中的小麦过敏原")
                    return False
            else:
                print_result(False, f"响应code不为200: {data.get('message')}")
                return False
        else:
            print_result(False, f"HTTP状态码错误: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"请求异常: {str(e)}")
        return False


def test_allergen_check_tree_nuts() -> bool:
    """测试树坚果过敏原检测"""
    print_separator("测试9：树坚果过敏原检测 - 杏仁曲奇")
    
    url = f"{BASE_URL}/api/food/allergen/check"
    payload = {
        "food_name": "杏仁曲奇",
        "ingredients": ["面粉", "黄油", "杏仁", "糖"]
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("code") == 200:
                result = data.get("data", {})
                detected = result.get("detected_allergens", [])
                
                # 应该检测到树坚果和小麦、乳制品
                tree_nut_detected = any(a.get("code") == "tree_nut" for a in detected)
                
                if tree_nut_detected:
                    print_result(True, "成功检测到杏仁曲奇中的树坚果过敏原")
                    return True
                else:
                    print_result(False, "未能检测到杏仁曲奇中的树坚果过敏原")
                    return False
            else:
                print_result(False, f"响应code不为200: {data.get('message')}")
                return False
        else:
            print_result(False, f"HTTP状态码错误: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"请求异常: {str(e)}")
        return False


def test_allergen_check_fish() -> bool:
    """测试鱼类过敏原检测"""
    print_separator("测试10：鱼类过敏原检测 - 清蒸鲈鱼")
    
    url = f"{BASE_URL}/api/food/allergen/check"
    payload = {
        "food_name": "清蒸鲈鱼",
        "ingredients": ["鲈鱼", "葱", "姜", "蒸鱼豉油"]
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get("code") == 200:
                result = data.get("data", {})
                detected = result.get("detected_allergens", [])
                
                # 应该检测到鱼类
                fish_detected = any(a.get("code") == "fish" for a in detected)
                
                if fish_detected:
                    print_result(True, "成功检测到清蒸鲈鱼中的鱼类过敏原")
                    return True
                else:
                    print_result(False, "未能检测到清蒸鲈鱼中的鱼类过敏原")
                    return False
            else:
                print_result(False, f"响应code不为200: {data.get('message')}")
                return False
        else:
            print_result(False, f"HTTP状态码错误: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"请求异常: {str(e)}")
        return False


def check_server_health() -> bool:
    """检查服务器是否正常运行"""
    print_separator("检查后端服务状态")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_result(True, "后端服务运行正常")
            return True
        else:
            print_result(False, f"后端服务返回异常状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_result(False, "无法连接到后端服务，请确保服务已启动")
        print(f"  提示: 请在后端目录运行 'uvicorn app.main:app --reload --host 0.0.0.0 --port 8000'")
        return False
    except Exception as e:
        print_result(False, f"检查服务状态时发生异常: {str(e)}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  Phase 6 过敏原检测功能测试")
    print("="*60)
    
    # 首先检查服务器状态
    if not check_server_health():
        print("\n⚠️ 后端服务未运行，无法执行测试")
        return False
    
    # 运行所有测试
    tests = [
        ("获取过敏原类别列表", test_get_allergen_categories),
        ("基础过敏原检测-宫保鸡丁", test_allergen_check_basic),
        ("带配料的过敏原检测-番茄炒蛋", test_allergen_check_with_ingredients),
        ("用户过敏原告警匹配", test_allergen_check_user_warning),
        ("无过敏原食物检测-清炒白菜", test_allergen_check_no_allergen),
        ("多过敏原食物检测-海鲜豆腐煲", test_allergen_check_multiple),
        ("乳制品过敏原检测-芝士焗饭", test_allergen_check_milk_products),
        ("小麦过敏原检测-炸酱面", test_allergen_check_wheat),
        ("树坚果过敏原检测-杏仁曲奇", test_allergen_check_tree_nuts),
        ("鱼类过敏原检测-清蒸鲈鱼", test_allergen_check_fish),
    ]
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.add_result(test_name, passed)
        except Exception as e:
            print_result(False, f"测试异常: {str(e)}")
            results.add_result(test_name, False)
    
    # 打印汇总
    return results.print_summary()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
