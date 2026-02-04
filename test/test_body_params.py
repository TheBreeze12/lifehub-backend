"""
Phase 4: 身体参数设置功能测试
测试用户偏好中的体重、身高、年龄、性别字段的增删改查功能
"""
import requests
import json
import sys
import os

# 后端服务地址
BASE_URL = "http://localhost:8000"

# 测试用户信息
TEST_USER_NICKNAME = f"test_body_params_{os.getpid()}"
TEST_USER_PASSWORD = "testpassword123"
TEST_USER_ID = None


def print_test_result(test_name: str, passed: bool, message: str = ""):
    """打印测试结果"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {test_name}")
    if message:
        print(f"         {message}")


def test_register_user():
    """测试1: 注册测试用户"""
    global TEST_USER_ID
    
    url = f"{BASE_URL}/api/user/register"
    payload = {
        "nickname": TEST_USER_NICKNAME,
        "password": TEST_USER_PASSWORD
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get("code") == 200:
            TEST_USER_ID = data.get("userId")
            print_test_result("注册测试用户", True, f"userId={TEST_USER_ID}")
            return True
        else:
            print_test_result("注册测试用户", False, f"响应: {data}")
            return False
    except Exception as e:
        print_test_result("注册测试用户", False, f"异常: {str(e)}")
        return False


def test_get_preferences_initial():
    """测试2: 获取初始用户偏好（身体参数应为空）"""
    if not TEST_USER_ID:
        print_test_result("获取初始用户偏好", False, "用户ID不存在")
        return False
    
    url = f"{BASE_URL}/api/user/preferences?userId={TEST_USER_ID}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get("code") == 200:
            user_data = data.get("data", {})
            # 检查新增的身体参数字段存在且初始值为空
            weight = user_data.get("weight")
            height = user_data.get("height")
            age = user_data.get("age")
            gender = user_data.get("gender")
            
            # 初始值应该都是None
            if weight is None and height is None and age is None and gender is None:
                print_test_result("获取初始用户偏好", True, "身体参数初始值为空")
                return True
            else:
                print_test_result("获取初始用户偏好", False, 
                    f"身体参数非空: weight={weight}, height={height}, age={age}, gender={gender}")
                return False
        else:
            print_test_result("获取初始用户偏好", False, f"响应: {data}")
            return False
    except Exception as e:
        print_test_result("获取初始用户偏好", False, f"异常: {str(e)}")
        return False


def test_update_body_params_full():
    """测试3: 更新所有身体参数"""
    if not TEST_USER_ID:
        print_test_result("更新所有身体参数", False, "用户ID不存在")
        return False
    
    url = f"{BASE_URL}/api/user/preferences"
    payload = {
        "userId": TEST_USER_ID,
        "weight": 70.5,
        "height": 175.0,
        "age": 25,
        "gender": "male"
    }
    
    try:
        response = requests.put(url, json=payload, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get("code") == 200:
            user_data = data.get("data", {})
            
            # 验证返回的数据
            checks = [
                (user_data.get("weight") == 70.5, f"weight={user_data.get('weight')}"),
                (user_data.get("height") == 175.0, f"height={user_data.get('height')}"),
                (user_data.get("age") == 25, f"age={user_data.get('age')}"),
                (user_data.get("gender") == "male", f"gender={user_data.get('gender')}")
            ]
            
            all_passed = all(check[0] for check in checks)
            if all_passed:
                print_test_result("更新所有身体参数", True, 
                    f"weight=70.5, height=175.0, age=25, gender=male")
                return True
            else:
                failed = [check[1] for check in checks if not check[0]]
                print_test_result("更新所有身体参数", False, f"验证失败: {', '.join(failed)}")
                return False
        else:
            print_test_result("更新所有身体参数", False, f"响应: {data}")
            return False
    except Exception as e:
        print_test_result("更新所有身体参数", False, f"异常: {str(e)}")
        return False


def test_get_preferences_after_update():
    """测试4: 验证身体参数更新后的持久化"""
    if not TEST_USER_ID:
        print_test_result("验证身体参数持久化", False, "用户ID不存在")
        return False
    
    url = f"{BASE_URL}/api/user/preferences?userId={TEST_USER_ID}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get("code") == 200:
            user_data = data.get("data", {})
            
            # 验证数据持久化
            checks = [
                (user_data.get("weight") == 70.5, f"weight={user_data.get('weight')}"),
                (user_data.get("height") == 175.0, f"height={user_data.get('height')}"),
                (user_data.get("age") == 25, f"age={user_data.get('age')}"),
                (user_data.get("gender") == "male", f"gender={user_data.get('gender')}")
            ]
            
            all_passed = all(check[0] for check in checks)
            if all_passed:
                print_test_result("验证身体参数持久化", True, "数据持久化成功")
                return True
            else:
                failed = [check[1] for check in checks if not check[0]]
                print_test_result("验证身体参数持久化", False, f"验证失败: {', '.join(failed)}")
                return False
        else:
            print_test_result("验证身体参数持久化", False, f"响应: {data}")
            return False
    except Exception as e:
        print_test_result("验证身体参数持久化", False, f"异常: {str(e)}")
        return False


def test_update_body_params_partial():
    """测试5: 部分更新身体参数（只更新体重）"""
    if not TEST_USER_ID:
        print_test_result("部分更新身体参数", False, "用户ID不存在")
        return False
    
    url = f"{BASE_URL}/api/user/preferences"
    payload = {
        "userId": TEST_USER_ID,
        "weight": 72.0  # 只更新体重
    }
    
    try:
        response = requests.put(url, json=payload, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get("code") == 200:
            user_data = data.get("data", {})
            
            # 验证体重更新，其他字段保持不变
            checks = [
                (user_data.get("weight") == 72.0, f"weight={user_data.get('weight')} (应为72.0)"),
                (user_data.get("height") == 175.0, f"height={user_data.get('height')} (应为175.0)"),
                (user_data.get("age") == 25, f"age={user_data.get('age')} (应为25)"),
                (user_data.get("gender") == "male", f"gender={user_data.get('gender')} (应为male)")
            ]
            
            all_passed = all(check[0] for check in checks)
            if all_passed:
                print_test_result("部分更新身体参数", True, "体重更新为72.0，其他字段保持不变")
                return True
            else:
                failed = [check[1] for check in checks if not check[0]]
                print_test_result("部分更新身体参数", False, f"验证失败: {', '.join(failed)}")
                return False
        else:
            print_test_result("部分更新身体参数", False, f"响应: {data}")
            return False
    except Exception as e:
        print_test_result("部分更新身体参数", False, f"异常: {str(e)}")
        return False


def test_update_gender_options():
    """测试6: 测试性别的不同选项（male/female/other）"""
    if not TEST_USER_ID:
        print_test_result("测试性别选项", False, "用户ID不存在")
        return False
    
    url = f"{BASE_URL}/api/user/preferences"
    gender_options = ["male", "female", "other"]
    
    for gender in gender_options:
        payload = {
            "userId": TEST_USER_ID,
            "gender": gender
        }
        
        try:
            response = requests.put(url, json=payload, timeout=10)
            data = response.json()
            
            if response.status_code != 200 or data.get("code") != 200:
                print_test_result(f"测试性别选项-{gender}", False, f"响应: {data}")
                return False
            
            user_data = data.get("data", {})
            if user_data.get("gender") != gender:
                print_test_result(f"测试性别选项-{gender}", False, 
                    f"gender={user_data.get('gender')} (应为{gender})")
                return False
        except Exception as e:
            print_test_result(f"测试性别选项-{gender}", False, f"异常: {str(e)}")
            return False
    
    print_test_result("测试性别选项", True, "male/female/other 全部通过")
    return True


def test_login_with_body_params():
    """测试7: 登录后验证身体参数"""
    if not TEST_USER_ID:
        print_test_result("登录验证身体参数", False, "用户ID不存在")
        return False
    
    url = f"{BASE_URL}/api/user/login"
    payload = {
        "nickname": TEST_USER_NICKNAME,
        "password": TEST_USER_PASSWORD
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get("code") == 200:
            user_data = data.get("data", {})
            
            # 检查身体参数字段存在于登录响应中
            has_weight = "weight" in user_data
            has_height = "height" in user_data
            has_age = "age" in user_data
            has_gender = "gender" in user_data
            
            if has_weight and has_height and has_age and has_gender:
                print_test_result("登录验证身体参数", True, 
                    f"weight={user_data.get('weight')}, height={user_data.get('height')}, "
                    f"age={user_data.get('age')}, gender={user_data.get('gender')}")
                return True
            else:
                missing = []
                if not has_weight: missing.append("weight")
                if not has_height: missing.append("height")
                if not has_age: missing.append("age")
                if not has_gender: missing.append("gender")
                print_test_result("登录验证身体参数", False, f"缺少字段: {', '.join(missing)}")
                return False
        else:
            print_test_result("登录验证身体参数", False, f"响应: {data}")
            return False
    except Exception as e:
        print_test_result("登录验证身体参数", False, f"异常: {str(e)}")
        return False


def test_body_params_validation():
    """测试8: 测试身体参数的边界值验证"""
    if not TEST_USER_ID:
        print_test_result("身体参数边界验证", False, "用户ID不存在")
        return False
    
    url = f"{BASE_URL}/api/user/preferences"
    
    # 测试有效的边界值
    valid_cases = [
        {"weight": 0.1, "expected": "最小体重"},
        {"weight": 500.0, "expected": "最大体重"},
        {"height": 0.1, "expected": "最小身高"},
        {"height": 300.0, "expected": "最大身高"},
        {"age": 1, "expected": "最小年龄"},
        {"age": 150, "expected": "最大年龄"},
    ]
    
    for case in valid_cases:
        payload = {"userId": TEST_USER_ID}
        payload.update({k: v for k, v in case.items() if k != "expected"})
        
        try:
            response = requests.put(url, json=payload, timeout=10)
            if response.status_code != 200:
                # 422是验证错误，可能是边界值被拒绝
                if response.status_code == 422:
                    print_test_result(f"边界验证-{case['expected']}", False, 
                        f"边界值被拒绝: {payload}")
                    return False
        except Exception as e:
            print_test_result(f"边界验证-{case['expected']}", False, f"异常: {str(e)}")
            return False
    
    print_test_result("身体参数边界验证", True, "有效边界值全部通过")
    return True


def test_combined_update():
    """测试9: 同时更新身体参数和其他偏好"""
    if not TEST_USER_ID:
        print_test_result("组合更新测试", False, "用户ID不存在")
        return False
    
    url = f"{BASE_URL}/api/user/preferences"
    payload = {
        "userId": TEST_USER_ID,
        "healthGoal": "gain_muscle",
        "weight": 75.0,
        "height": 180.0,
        "age": 28,
        "gender": "male",
        "dailyBudget": 100
    }
    
    try:
        response = requests.put(url, json=payload, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get("code") == 200:
            user_data = data.get("data", {})
            
            checks = [
                (user_data.get("healthGoal") == "gain_muscle", 
                    f"healthGoal={user_data.get('healthGoal')}"),
                (user_data.get("weight") == 75.0, f"weight={user_data.get('weight')}"),
                (user_data.get("height") == 180.0, f"height={user_data.get('height')}"),
                (user_data.get("age") == 28, f"age={user_data.get('age')}"),
                (user_data.get("gender") == "male", f"gender={user_data.get('gender')}"),
                (user_data.get("dailyBudget") == 100, f"dailyBudget={user_data.get('dailyBudget')}")
            ]
            
            all_passed = all(check[0] for check in checks)
            if all_passed:
                print_test_result("组合更新测试", True, "身体参数和其他偏好同时更新成功")
                return True
            else:
                failed = [check[1] for check in checks if not check[0]]
                print_test_result("组合更新测试", False, f"验证失败: {', '.join(failed)}")
                return False
        else:
            print_test_result("组合更新测试", False, f"响应: {data}")
            return False
    except Exception as e:
        print_test_result("组合更新测试", False, f"异常: {str(e)}")
        return False


def check_server_health():
    """检查服务器是否运行"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Phase 4: 身体参数设置功能测试")
    print("=" * 60)
    
    # 检查服务器
    print("\n[检查后端服务]")
    if not check_server_health():
        print("  ❌ 后端服务未启动，请先启动后端服务:")
        print("     cd Backend/lifehub-backend")
        print("     uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return False
    print("  ✅ 后端服务运行正常")
    
    # 运行测试
    print("\n[运行测试用例]")
    tests = [
        test_register_user,
        test_get_preferences_initial,
        test_update_body_params_full,
        test_get_preferences_after_update,
        test_update_body_params_partial,
        test_update_gender_options,
        test_login_with_body_params,
        test_body_params_validation,
        test_combined_update,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print_test_result(test.__name__, False, f"未捕获异常: {str(e)}")
            failed += 1
    
    # 打印总结
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
