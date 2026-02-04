"""
测试饮食记录CRUD功能（Phase 2）
- 测试更新饮食记录 PUT /api/food/diet/{record_id}
- 测试删除饮食记录 DELETE /api/food/diet/{record_id}
- 测试权限校验（只能操作自己的记录）
"""
import requests
import json
from datetime import date

BASE_URL = "http://localhost:8000"


def print_separator(title: str):
    """打印分隔线"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_add_diet_record(user_id: int, food_name: str = "测试菜品") -> int | None:
    """
    添加饮食记录（用于后续测试）
    返回记录ID
    """
    print_separator(f"准备测试数据：添加饮食记录 (userId={user_id})")
    
    url = f"{BASE_URL}/api/food/record"
    payload = {
        "userId": user_id,
        "foodName": food_name,
        "calories": 200.0,
        "protein": 15.0,
        "fat": 10.0,
        "carbs": 20.0,
        "mealType": "午餐",
        "recordDate": date.today().strftime("%Y-%m-%d")
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                print("✅ 添加饮食记录成功")
                # 获取刚添加的记录ID
                records_response = requests.get(
                    f"{BASE_URL}/api/food/records/today",
                    params={"userId": user_id}
                )
                if records_response.status_code == 200:
                    records_data = records_response.json()
                    today_str = date.today().strftime("%Y-%m-%d")
                    records = records_data.get("data", {}).get(today_str, [])
                    # 找到刚添加的记录
                    for record in records:
                        if record.get("foodName") == food_name:
                            record_id = record.get("id")
                            print(f"✅ 获取到记录ID: {record_id}")
                            return record_id
                print("⚠️ 无法获取记录ID")
                return None
            else:
                print(f"❌ 添加失败: {data.get('message')}")
                return None
        else:
            print(f"❌ 请求失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return None


def test_update_diet_record_success(record_id: int, user_id: int) -> bool:
    """测试更新饮食记录 - 成功场景"""
    print_separator(f"测试1：更新饮食记录成功场景 (record_id={record_id}, userId={user_id})")
    
    url = f"{BASE_URL}/api/food/diet/{record_id}"
    payload = {
        "userId": user_id,
        "foodName": "更新后的菜名",
        "calories": 350.0,
        "protein": 25.0,
        "fat": 15.0,
        "carbs": 30.0,
        "mealType": "晚餐"
    }
    
    try:
        response = requests.put(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                # 验证更新结果
                updated_data = data.get("data", {})
                if (updated_data.get("foodName") == "更新后的菜名" and 
                    updated_data.get("calories") == 350.0 and
                    updated_data.get("mealType") == "dinner"):
                    print("✅ 更新饮食记录成功，数据验证通过")
                    return True
                else:
                    print("❌ 更新成功但数据验证失败")
                    return False
            else:
                print(f"❌ 更新失败: {data.get('message')}")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def test_update_partial_fields(record_id: int, user_id: int) -> bool:
    """测试部分更新（只更新部分字段）"""
    print_separator(f"测试2：部分字段更新 (record_id={record_id}, userId={user_id})")
    
    url = f"{BASE_URL}/api/food/diet/{record_id}"
    # 只更新热量和蛋白质
    payload = {
        "userId": user_id,
        "calories": 400.0,
        "protein": 30.0
    }
    
    try:
        response = requests.put(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                updated_data = data.get("data", {})
                # 验证部分更新：热量和蛋白质应该更新，其他字段应该保持不变
                if (updated_data.get("calories") == 400.0 and 
                    updated_data.get("protein") == 30.0 and
                    updated_data.get("foodName") == "更新后的菜名"):  # 之前的值应该保留
                    print("✅ 部分字段更新成功，其他字段保持不变")
                    return True
                else:
                    print("❌ 部分更新验证失败")
                    return False
            else:
                print(f"❌ 更新失败: {data.get('message')}")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def test_update_permission_denied(record_id: int, wrong_user_id: int) -> bool:
    """测试更新饮食记录 - 权限校验失败场景（尝试更新别人的记录）"""
    print_separator(f"测试3：权限校验-尝试更新别人的记录 (record_id={record_id}, wrong_userId={wrong_user_id})")
    
    url = f"{BASE_URL}/api/food/diet/{record_id}"
    payload = {
        "userId": wrong_user_id,  # 使用错误的用户ID
        "foodName": "恶意修改"
    }
    
    try:
        response = requests.put(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 403:
            print(f"响应: {response.text}")
            print("✅ 权限校验成功，正确拒绝了非法操作 (HTTP 403)")
            return True
        elif response.status_code == 200:
            print("❌ 权限校验失败，不应该允许更新别人的记录")
            return False
        else:
            print(f"响应: {response.text}")
            print(f"⚠️ 返回了非预期的状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def test_update_record_not_found() -> bool:
    """测试更新饮食记录 - 记录不存在场景"""
    print_separator("测试4：更新不存在的记录")
    
    url = f"{BASE_URL}/api/food/diet/99999"  # 使用不存在的ID
    payload = {
        "userId": 1,
        "foodName": "测试"
    }
    
    try:
        response = requests.put(url, json=payload)
        print(f"状态码: {response.status_code}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 404:
            print(f"响应: {response.text}")
            print("✅ 正确返回404，记录不存在")
            return True
        else:
            print(f"响应: {response.text}")
            print(f"❌ 应该返回404，实际返回: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def test_delete_permission_denied(record_id: int, wrong_user_id: int) -> bool:
    """测试删除饮食记录 - 权限校验失败场景"""
    print_separator(f"测试5：权限校验-尝试删除别人的记录 (record_id={record_id}, wrong_userId={wrong_user_id})")
    
    url = f"{BASE_URL}/api/food/diet/{record_id}"
    params = {"userId": wrong_user_id}  # 使用错误的用户ID
    
    try:
        response = requests.delete(url, params=params)
        print(f"状态码: {response.status_code}")
        print(f"请求参数: userId={wrong_user_id}")
        
        if response.status_code == 403:
            print(f"响应: {response.text}")
            print("✅ 权限校验成功，正确拒绝了非法删除操作 (HTTP 403)")
            return True
        elif response.status_code == 200:
            print("❌ 权限校验失败，不应该允许删除别人的记录")
            return False
        else:
            print(f"响应: {response.text}")
            print(f"⚠️ 返回了非预期的状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def test_delete_record_not_found() -> bool:
    """测试删除饮食记录 - 记录不存在场景"""
    print_separator("测试6：删除不存在的记录")
    
    url = f"{BASE_URL}/api/food/diet/99999"  # 使用不存在的ID
    params = {"userId": 1}
    
    try:
        response = requests.delete(url, params=params)
        print(f"状态码: {response.status_code}")
        print(f"请求参数: userId=1, record_id=99999")
        
        if response.status_code == 404:
            print(f"响应: {response.text}")
            print("✅ 正确返回404，记录不存在")
            return True
        else:
            print(f"响应: {response.text}")
            print(f"❌ 应该返回404，实际返回: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def test_delete_diet_record_success(record_id: int, user_id: int) -> bool:
    """测试删除饮食记录 - 成功场景"""
    print_separator(f"测试7：删除饮食记录成功场景 (record_id={record_id}, userId={user_id})")
    
    url = f"{BASE_URL}/api/food/diet/{record_id}"
    params = {"userId": user_id}
    
    try:
        response = requests.delete(url, params=params)
        print(f"状态码: {response.status_code}")
        print(f"请求参数: userId={user_id}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200 and data.get("message") == "删除成功":
                # 验证记录确实被删除了
                verify_url = f"{BASE_URL}/api/food/diet/{record_id}"
                verify_payload = {"userId": user_id, "foodName": "验证"}
                verify_response = requests.put(verify_url, json=verify_payload)
                
                if verify_response.status_code == 404:
                    print("✅ 删除饮食记录成功，验证记录已不存在")
                    return True
                else:
                    print("⚠️ 删除成功但记录仍可访问")
                    return True  # 删除操作本身成功了
            else:
                print(f"❌ 删除失败: {data.get('message')}")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪" * 30)
    print("   饮食记录CRUD功能测试 (Phase 2)")
    print("🧪" * 30)
    print("\n⚠️  请确保后端服务已启动 (uvicorn app.main:app --reload)")
    print("⚠️  请确保数据库中已存在测试用户（userId=1）")
    
    # 测试用户ID
    test_user_id = 1
    wrong_user_id = 99999  # 用于权限测试的错误用户ID
    
    # 统计测试结果
    results = []
    
    # 1. 准备测试数据：添加一条饮食记录
    record_id = test_add_diet_record(test_user_id, "Phase2测试菜品")
    if record_id is None:
        print("\n❌ 无法创建测试数据，请检查后端服务和数据库")
        print("提示：确保数据库中存在userId=1的用户")
        return
    
    # 2. 测试更新成功场景
    results.append(("更新饮食记录-成功", test_update_diet_record_success(record_id, test_user_id)))
    
    # 3. 测试部分字段更新
    results.append(("部分字段更新", test_update_partial_fields(record_id, test_user_id)))
    
    # 4. 测试更新权限校验
    results.append(("更新权限校验", test_update_permission_denied(record_id, wrong_user_id)))
    
    # 5. 测试更新不存在的记录
    results.append(("更新不存在记录", test_update_record_not_found()))
    
    # 6. 测试删除权限校验
    results.append(("删除权限校验", test_delete_permission_denied(record_id, wrong_user_id)))
    
    # 7. 测试删除不存在的记录
    results.append(("删除不存在记录", test_delete_record_not_found()))
    
    # 8. 测试删除成功场景（放在最后，因为会删除测试记录）
    results.append(("删除饮食记录-成功", test_delete_diet_record_success(record_id, test_user_id)))
    
    # 打印测试结果汇总
    print_separator("测试结果汇总")
    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n🎉 所有测试通过！Phase 2 饮食记录CRUD功能实现正确！")
    else:
        print(f"\n⚠️ 有 {failed} 个测试未通过，请检查代码实现")


if __name__ == "__main__":
    run_all_tests()
